"""Experimental SD1.5 AnimateDiff video-to-video for short reference-based sprite loops."""
import gc, json, secrets, tempfile, hashlib, os, shutil, re
from pathlib import Path
from . import world, full_frame_guidance as G, full_frame_video as V

PREFIX = "animatediff/"
STATUS = {"stage": "Idle"}

def _json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}

def _folders(root):
    if not root or not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and not p.is_symlink())

def _root(root):
    return Path(root).resolve() if root and Path(root).is_dir() else None

def _setup_dirs(root, create=False):
    root = _root(root)
    if root is None:
        raise ValueError("Set an existing models directory in Settings first")
    folder = root / "animatediff"
    paths = [folder, folder / "base", folder / "motion"]
    for p in paths:
        if p.is_symlink() or not p.resolve().is_relative_to(root):
            raise ValueError("AnimateDiff setup folders must stay inside the configured models directory")
        if p.exists() and not p.is_dir():
            raise ValueError("A file is blocking the AnimateDiff folder: " + str(p))
        if create:
            p.mkdir(exist_ok=True)
    return paths[1:]

def prepare_folders(root):
    _setup_dirs(root, create=True)
    return readiness(root)

def _present(path):
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False

# SHA256 of the published SD1.5 legacy Diffusers weights, verified against the
# upstream Hugging Face file pages. Never deserialize arbitrary .bin checkpoints.
LEGACY_SHA256 = {
    "unet": "c7da0e21ba7ea50637bee26e81c220844defdf01aafca02b2c42ecdadb813de4",
    "vae": "1b134cded8eb78b184aefb8805b6b572f36fa77b255c483665dda931fa0130c5",
}
WEIGHT = "diffusion_pytorch_model"

def _legacy_components(base):
    return [name for name in LEGACY_SHA256
            if not _present(base / name / (WEIGHT + ".safetensors"))
            and _present(base / name / (WEIGHT + ".bin"))]

def _verified_weights(source, expected, torch):
    # Hash the exact open file before restricted deserialization; no fallback.
    with source.open("rb") as f:
        digest = hashlib.sha256()
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ValueError("Legacy " + source.parent.name + " weights do not match the published SD1.5 file. Use the matching official file or a Safetensors model.")
        f.seek(0)
        return torch.load(f, map_location="cpu", weights_only=True)

def convert_legacy(base):
    components = _legacy_components(base)
    if not components:
        return
    import torch
    from safetensors.torch import save_file
    version = re.match(r"(\d+)\.(\d+)", str(torch.__version__))
    if not version or tuple(map(int, version.groups())) < (2, 6):
        raise RuntimeError("Verified legacy conversion requires PyTorch 2.6 or newer. Update the SpriteForge runtime or use Safetensors weights.")
    for name in components:
        folder = base / name
        source = folder / (WEIGHT + ".bin")
        target = folder / (WEIGHT + ".safetensors")
        if folder.is_symlink() or source.is_symlink() or not source.resolve().is_relative_to(base.resolve()):
            raise ValueError("Legacy model weights must be local files inside the detected model folder")
        if target.exists() or target.is_symlink():
            raise ValueError("An existing invalid Safetensors file blocks conversion: " + str(target))
        if shutil.disk_usage(folder).free < source.stat().st_size + 64 * 1024 * 1024:
            raise RuntimeError("Not enough free disk space to convert " + name + " weights; original .bin is preserved.")
        STATUS["stage"] = "Verifying and converting SD1.5 " + name + " weights (one-time)"
        weights = _verified_weights(source, LEGACY_SHA256[name], torch)
        if not isinstance(weights, dict) or not weights or any(
            not isinstance(k, str) or type(v) is not torch.Tensor or v.layout != torch.strided
            for k, v in weights.items()):
            raise ValueError("Expected a plain tensor state dictionary for " + name)
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(dir=folder, suffix=".safetensors.tmp", delete=False) as f:
                tmp = Path(f.name)
            save_file({k: v.detach().contiguous() for k, v in weights.items()}, str(tmp), metadata={"format": "pt"})
            # Publish only a complete file; never replace an existing destination.
            os.link(tmp, target)
        finally:
            if tmp is not None:
                tmp.unlink(missing_ok=True)
            del weights
            gc.collect()

def _base_issues(p):
    index = _json(p / "model_index.json")
    unet = _json(p / "unet/config.json")
    issues = []
    if not index:
        issues.append("Missing or invalid model_index.json")
    elif index.get("_class_name") not in ("StableDiffusionPipeline", "StableDiffusionImg2ImgPipeline"):
        issues.append("Not a Stable Diffusion 1.5 image pipeline")
    if unet.get("cross_attention_dim") != 768:
        issues.append("Missing or incompatible SD1.5 UNet config")
    required = ["vae/config.json", "text_encoder/config.json",
                "text_encoder/model.safetensors", "tokenizer/vocab.json",
                "tokenizer/merges.txt", "tokenizer/tokenizer_config.json", "scheduler/scheduler_config.json"]
    issues.extend("Missing " + name for name in required if not _present(p / name))
    for name in LEGACY_SHA256:
        if not _present(p / name / (WEIGHT + ".safetensors")) and not _present(p / name / (WEIGHT + ".bin")):
            issues.append("Missing " + name + "/" + WEIGHT + ".safetensors or official SD1.5 .bin")
    return issues

def _motion_issues(p):
    config = _json(p / "config.json")
    length = config.get("motion_max_seq_length", 32)
    issues = []
    if (config.get("_class_name") != "MotionAdapter" or
        config.get("block_out_channels") != [320, 640, 1280, 1280] or
        not isinstance(length, int) or length < 16):
        issues.append("Missing or incompatible SD1.5 MotionAdapter config.json")
    if not _present(p / "diffusion_pytorch_model.safetensors"):
        issues.append("Missing diffusion_pytorch_model.safetensors")
    return issues

def _inspect(root):
    missing = []
    details = {"base": [], "motion": [], "paths": {}, "raw_files": [], "can_prepare": False}
    try:
        base_dir, motion_dir = _setup_dirs(root)
        details["paths"] = {"base": str(base_dir), "motion": str(motion_dir)}
        details["can_prepare"] = True
    except (ValueError, OSError) as exc:
        return {}, [str(exc)], details
    good = {}
    for key, directory, check in (("base", base_dir, _base_issues), ("motion", motion_dir, _motion_issues)):
        good[key] = []
        for p in _folders(directory):
            if not p.resolve().is_relative_to(directory.resolve()):
                continue
            issues = check(p)
            details[key].append({"name": p.name, "ready": not issues, "issues": issues,
                                 "legacy": _legacy_components(p) if key == "base" else []})
            if not issues:
                good[key].append(p)
        if directory.is_dir():
            details["raw_files"].extend(str(p.name) for p in sorted(directory.iterdir())
                if p.is_file() and p.suffix.lower() in (".ckpt", ".safetensors", ".gguf", ".pt"))
    if not good["base"]: missing.append("Complete SD1.5 Diffusers image model in animatediff/base")
    if not good["motion"]: missing.append("Complete SD1.5 Diffusers MotionAdapter in animatediff/motion")
    pairs = {PREFIX + b.name + "/" + a.name: (b, a) for b in good["base"] for a in good["motion"]}
    return pairs, missing, details

def catalog(root):
    pairs, missing, _ = _inspect(root)
    return pairs, missing

def readiness(root):
    pairs, missing, details = _inspect(root)
    return {"ready": bool(pairs), "missing": missing, **details,
            "models": [{"name": key, "backend": "animatediff",
                        "label": "AnimateDiff — " + b.name + " / " + a.name,
                        "legacy": _legacy_components(b)}
                       for key, (b, a) in pairs.items()]}

PROFILES = {"preserve": (0.35, 4.0), "balanced": (0.50, 5.0), "motion": (0.65, 6.0)}

def motion_prompts(text, guidance):
    # Typed instructions take precedence over preset-specific restrictions.
    # In particular, idle's default no-blink/no-gesture guidance must not override a requested action.
    text = world.label(text, "motion description", 2000, True)
    effective = dict(guidance)
    if text:
        effective["preset"] = "custom"
    positive = G.prompt(text, effective)
    negative = G.negative(effective)
    if guidance["identity"]:
        positive += " Keep the original palette, shading, lighting direction and costume details consistent across frames."
        negative += ", identity drift, costume changes, inconsistent palette, changing lighting, flickering colors"
    return positive, negative

def settings(body):
    n = world.integer
    w = n(body.get("width", 512), 256, 512, "AnimateDiff width")
    h = n(body.get("height", 512), 256, 512, "AnimateDiff height")
    count = n(body.get("frames", 16), 8, 16, "AnimateDiff frames")
    if w % 64 or h % 64:
        raise ValueError("AnimateDiff dimensions must be divisible by 64")
    guidance = G.settings(body.get("guidance"))
    seed = n(body.get("seed", -1), -1, 2147483647, "video seed")
    profile = body.get("ad_profile", "balanced")
    if not isinstance(profile, str) or profile not in PROFILES:
        raise ValueError("Choose a valid AnimateDiff motion profile")
    strength, cfg = PROFILES[profile]
    positive, negative = motion_prompts(body.get("prompt", ""), guidance)
    return dict(width=w, height=h, frames=count, guidance=guidance,
                prompt=positive, negative=negative, profile=profile, cfg=cfg,
                fps=n(body.get("fps", 8), 8, 30, "video FPS"),
                steps=n(body.get("steps", 12), 8, 40, "video steps"),
                seed=seed if seed >= 0 else secrets.randbelow(2147483648),
                reference=body.get("reference"), strength=strength)

def generate(root, body, runner=None):
    pairs, _ = catalog(root)
    model = body.get("model")
    if not isinstance(model, str) or model not in pairs:
        raise ValueError("Select a detected AnimateDiff SD1.5 base and motion adapter")
    q = settings(body)
    image = V.prepare_reference(q["reference"], q["width"], q["height"], q["guidance"])
    return (runner or run)(*pairs[model], image, q)

def configure_memory(pipe):
    """Diffusers exposes VAE slicing on the component in newer releases."""
    pipe.enable_model_cpu_offload()
    slice_vae = getattr(pipe.vae, "enable_slicing", None)
    legacy_slice = getattr(pipe, "enable_vae_slicing", None)
    if callable(slice_vae):
        slice_vae()
    elif callable(legacy_slice):
        legacy_slice()
    chunk = getattr(pipe.unet, "enable_forward_chunking", None)
    if callable(chunk):
        chunk()
    # Video encode/decode remains explicitly chunked in the pipeline call.

def run(base, adapter, image, q):
    from . import generate as gen
    if not gen._lock.acquire(blocking=False):
        raise RuntimeError("GPU busy; finish the current generation first")
    pipe = motion = None
    try:
        import torch
        from diffusers import AnimateDiffVideoToVideoPipeline, MotionAdapter, DDIMScheduler
        from diffusers.utils import export_to_video
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU required for AnimateDiff")
        gen._cache.update(key=None, pipe=None, cn_name=None)
        gc.collect()
        torch.cuda.empty_cache()
        convert_legacy(base)
        STATUS["stage"] = "Loading AnimateDiff models"
        motion = MotionAdapter.from_pretrained(str(adapter), torch_dtype=torch.float16, local_files_only=True, use_safetensors=True)
        pipe = AnimateDiffVideoToVideoPipeline.from_pretrained(
            str(base), motion_adapter=motion, torch_dtype=torch.float16, local_files_only=True, use_safetensors=True)
        pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config, beta_schedule="linear", clip_sample=False)
        configure_memory(pipe)
        STATUS["stage"] = "Generating AnimateDiff frames (" + q["profile"] + ", seed " + str(q["seed"]) + ")"
        # A repeated still is input conditioning only; the temporal denoiser generates every output frame.
        frames = pipe(video=[image.copy() for _ in range(q["frames"])], prompt=q["prompt"],
                      negative_prompt=q["negative"], width=q["width"], height=q["height"],
                      num_inference_steps=q["steps"], strength=q["strength"], guidance_scale=q["cfg"],
                      generator=torch.Generator(device="cpu").manual_seed(q["seed"]),
                      output_type="pil", decode_chunk_size=2).frames[0]
        if len(frames) != q["frames"]:
            raise RuntimeError("AnimateDiff returned an unexpected frame count")
        STATUS["stage"] = "Encoding animation preview"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "motion.mp4"
            export_to_video(frames, str(target), fps=q["fps"])
            if target.stat().st_size > 64_000_000:
                raise RuntimeError("Generated video exceeds 64 MB")
            return target.read_bytes()
    except ImportError as exc:
        raise RuntimeError("AnimateDiff requires compatible Diffusers, Accelerate and imageio-ffmpeg in SpriteForge's Python environment") from exc
    finally:
        try:
            del pipe, motion
            gc.collect()
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        finally:
            STATUS["stage"] = "Idle"
            gen._lock.release()
