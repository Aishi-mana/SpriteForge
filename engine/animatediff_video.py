"""Experimental SD1.5 AnimateDiff video-to-video for short reference-based sprite loops."""
import gc, json, secrets, tempfile
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

def catalog(root):
    """Only discover local Diffusers-format SD1.5 bases and compatible motion adapters."""
    folder = Path(root) / "animatediff" if root else None
    bases = []
    adapters = []
    if folder:
        for p in _folders(folder / "base"):
            index = _json(p / "model_index.json")
            unet = _json(p / "unet/config.json")
            if index.get("_class_name") in ("StableDiffusionPipeline", "StableDiffusionImg2ImgPipeline") and unet.get("cross_attention_dim") == 768:
                bases.append(p)
        for p in _folders(folder / "motion"):
            config = _json(p / "config.json")
            if config.get("_class_name") == "MotionAdapter" and config.get("block_out_channels") == [320, 640, 1280, 1280] and config.get("motion_max_seq_length", 32) >= 16 and any(p.glob("*.safetensors")):
                adapters.append(p)
    pairs = {PREFIX + b.name + "/" + a.name: (b, a) for b in bases for a in adapters}
    missing = []
    if not bases: missing.append("SD1.5 Diffusers model folder in animatediff/base")
    if not adapters: missing.append("SD1.5 Diffusers MotionAdapter folder in animatediff/motion")
    return pairs, missing

def readiness(root):
    pairs, missing = catalog(root)
    return {"ready": bool(pairs), "missing": missing,
            "models": [{"name": key, "backend": "animatediff",
                        "label": "AnimateDiff — " + b.name + " / " + a.name}
                       for key, (b, a) in pairs.items()]}

def settings(body):
    n = world.integer
    w = n(body.get("width", 512), 256, 512, "AnimateDiff width")
    h = n(body.get("height", 512), 256, 512, "AnimateDiff height")
    count = n(body.get("frames", 16), 8, 16, "AnimateDiff frames")
    if w % 64 or h % 64:
        raise ValueError("AnimateDiff dimensions must be divisible by 64")
    guidance = G.settings(body.get("guidance"))
    seed = n(body.get("seed", -1), -1, 2147483647, "video seed")
    return dict(width=w, height=h, frames=count, guidance=guidance,
                prompt=G.prompt(body.get("prompt", ""), guidance),
                negative=G.negative(guidance) + ", changing lighting, flickering colors",
                fps=n(body.get("fps", 8), 8, 30, "video FPS"),
                steps=n(body.get("steps", 12), 8, 40, "video steps"),
                seed=seed if seed >= 0 else secrets.randbelow(2147483648),
                reference=body.get("reference"), strength=0.5)

def generate(root, body, runner=None):
    pairs, _ = catalog(root)
    model = body.get("model")
    if not isinstance(model, str) or model not in pairs:
        raise ValueError("Select a detected AnimateDiff SD1.5 base and motion adapter")
    q = settings(body)
    image = V.prepare_reference(q["reference"], q["width"], q["height"], q["guidance"])
    return (runner or run)(*pairs[model], image, q)

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
        STATUS["stage"] = "Loading AnimateDiff models"
        motion = MotionAdapter.from_pretrained(str(adapter), torch_dtype=torch.float16, local_files_only=True, use_safetensors=True)
        pipe = AnimateDiffVideoToVideoPipeline.from_pretrained(
            str(base), motion_adapter=motion, torch_dtype=torch.float16, local_files_only=True, use_safetensors=True)
        pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config, beta_schedule="linear", clip_sample=False)
        pipe.enable_model_cpu_offload()
        pipe.enable_vae_slicing()
        pipe.unet.enable_forward_chunking()
        STATUS["stage"] = "Generating AnimateDiff frames"
        # A repeated still is input conditioning only; the temporal denoiser generates every output frame.
        frames = pipe(video=[image.copy() for _ in range(q["frames"])], prompt=q["prompt"],
                      negative_prompt=q["negative"], width=q["width"], height=q["height"],
                      num_inference_steps=q["steps"], strength=q["strength"], guidance_scale=5.0,
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
