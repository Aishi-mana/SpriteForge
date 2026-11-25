"""SDXL + pixel-art LoRA, optional IP-Adapter reference conditioning. Tuned for 8 GB VRAM."""
import gc
import time
import threading
from pathlib import Path
from PIL import Image

_lock = threading.Lock()
PROGRESS = None  # optional callback(done, total) set by the job queue; called after each finished image
_cache = {"key": None, "pipe": None}

NEGATIVE = "3d, realistic, photo, blurry, gradient, soft shading, shadow, text, watermark, multiple characters, cropped, frame"
BG_RGB = {"white": (255, 255, 255), "light gray": (204, 204, 204), "green": (0, 255, 0), "magenta": (255, 0, 255)}


NEGATIVE_PORTRAIT = ("3d, realistic, photo, blurry, gradient, soft shading, text, watermark, multiple characters, frame, "
                     "full body, legs, deformed face, extra eyes")


NEGATIVE_TILE = ("3d, realistic, photo, blurry, gradient, soft shading, text, watermark, frame, border, vignette, perspective, "
                 "character, person, single object, centered object, lighting gradient")
NEGATIVE_PROP = "3d, realistic, photo, blurry, gradient, soft shading, text, watermark, multiple objects, cropped, frame, character, hands"
KINDS_PROP = ("prop", "icon", "ui")


def negative_for(kind):
    """Default negative prompt per generation kind (sprite, tile, prop/icon/ui; everything else = portrait-style)."""
    if kind == "sprite":
        return NEGATIVE
    if kind == "tile":
        return NEGATIVE_TILE
    if kind in KINDS_PROP:
        return NEGATIVE_PROP
    return NEGATIVE_PORTRAIT


SAMPLERS = ("euler_a", "dpmpp_2m_karras", "euler")
SAMPLER = "euler_a"


def set_sampler(name):
    global SAMPLER
    SAMPLER = name if name in SAMPLERS else "euler_a"


def _apply_sampler(pipe):
    """Swap the scheduler (cheap, no reload). DPM++ 2M Karras converges to cleaner detail than Euler ancestral at equal steps."""
    from diffusers import EulerAncestralDiscreteScheduler, DPMSolverMultistepScheduler, EulerDiscreteScheduler
    cfg = pipe.scheduler.config
    if SAMPLER == "dpmpp_2m_karras":
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(cfg, use_karras_sigmas=True, algorithm_type="dpmsolver++")
    elif SAMPLER == "euler":
        pipe.scheduler = EulerDiscreteScheduler.from_config(cfg)
    else:
        pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(cfg)


def build_prompt(user_prompt, bg="white", kind="sprite"):
    if kind == "portrait":
        return f"pixel art, portrait, {user_prompt}, head and shoulders, face close-up, looking at viewer, plain flat solid {bg} background"
    if kind == "tile":
        return f"pixel art, seamless tileable texture, {user_prompt}, top-down view, flat even lighting, repeating pattern filling the whole image, no border"
    if kind == "prop":
        return f"pixel art, {user_prompt}, single object, game prop, centered, plain flat solid {bg} background"
    if kind == "icon":
        return f"pixel art, game item icon, {user_prompt}, single item, centered, plain flat solid {bg} background"
    if kind == "ui":
        return f"pixel art, game user interface element, {user_prompt}, flat design, centered, plain flat solid {bg} background"
    if kind == "expression":
        return f"pixel art, portrait, {user_prompt}, face close-up, expressive face"
    return f"pixel art, {user_prompt}, single character, full body, centered, plain flat solid {bg} background"


def prep_reference(sprite, bg="white", canvas=512, fill=0.8):
    """Sprite -> square, bg-coloured, crisply upscaled image the IP-Adapter's CLIP encoder can read."""
    sprite = sprite.convert("RGBA")
    scale = canvas * fill / max(sprite.size)
    if scale >= 1:
        k = int(scale)
        big = sprite.resize((sprite.width * k, sprite.height * k), Image.NEAREST)
    else:
        big = sprite.resize((max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale))), Image.LANCZOS)
    out = Image.new("RGB", (canvas, canvas), BG_RGB.get(bg, (255, 255, 255)))
    out.paste(big, ((canvas - big.width) // 2, (canvas - big.height) // 2), big)
    return out


def _controlnet(cn_dir):
    """Prefer a local SDXL OpenPose ControlNet from <models>/controlnet; else download xinsir's once (cached)."""
    import torch
    from diffusers import ControlNetModel
    if cn_dir and Path(cn_dir).exists():
        for p in sorted(Path(cn_dir).glob("*.safetensors")):
            n = p.name.lower()
            if "openpose" in n and "xl" in n:
                try:
                    return ControlNetModel.from_single_file(str(p), torch_dtype=torch.float16), p.name
                except Exception as e:
                    print(f"[controlnet] could not load local {p.name}: {e}")
    name = "xinsir/controlnet-openpose-sdxl-1.0"
    return ControlNetModel.from_pretrained(name, torch_dtype=torch.float16), name + " (Hugging Face)"


def controlnet_name():
    return _cache.get("cn_name")


def _load(ckpt, lora, lora_w, lora_dir, use_ip, use_cn=False, cn_dir=None):
    import torch
    from diffusers import StableDiffusionXLPipeline, StableDiffusionXLControlNetPipeline, EulerAncestralDiscreteScheduler
    key = (ckpt, lora, lora_w, use_ip, use_cn)
    if _cache["key"] == key:
        return _cache["pipe"]
    _cache.update(key=None, pipe=None)
    gc.collect()
    torch.cuda.empty_cache()
    if use_cn:
        cn, cn_name = _controlnet(cn_dir)
        pipe = StableDiffusionXLControlNetPipeline.from_single_file(ckpt, controlnet=cn, torch_dtype=torch.float16, use_safetensors=True)
        _cache["cn_name"] = cn_name
    else:
        pipe = StableDiffusionXLPipeline.from_single_file(ckpt, torch_dtype=torch.float16, use_safetensors=True)
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    if lora:
        pipe.load_lora_weights(str(Path(lora_dir)), weight_name=lora, adapter_name="pixel")
        pipe.set_adapters(["pixel"], [lora_w])
    if use_ip:  # first use downloads ~3 GB from Hugging Face, then it's cached and works offline
        pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter_sdxl.safetensors")
    if use_cn:
        # UNet + ControlNet together don't fit in 8 GB; stream weights layer by layer (slower, but fits)
        pipe.enable_sequential_cpu_offload()
    else:
        pipe.enable_model_cpu_offload()  # fits 8 GB, spills to system RAM
    try:  # newer diffusers moved this onto the VAE; older ones have it on the pipeline
        pipe.vae.enable_tiling()
    except AttributeError:
        pipe.enable_vae_tiling()
    _cache.update(key=key, pipe=pipe)
    return pipe


def generate(ckpt, lora, lora_w, lora_dir, prompt, negative="", steps=25, cfg=7.0, seed=-1, size=1024, bg="white",
             ip_image=None, ip_scale=0.7, n=1, control_image=None, cn_scale=0.8, cn_dir=None, kind="sprite"):
    """Returns [(PIL image, seed), ...]. ip_image = reference sprite, control_image = OpenPose skeleton render."""
    import torch
    with _lock:
        pipe = _load(ckpt, lora, lora_w, lora_dir, ip_image is not None, control_image is not None, cn_dir)
        _apply_sampler(pipe)
        kw = {}
        if control_image is not None:
            kw.update(image=control_image.convert("RGB").resize((size, size)), controlnet_conditioning_scale=cn_scale,
                      control_guidance_end=0.9)
        if ip_image is not None:
            pipe.set_ip_adapter_scale(ip_scale)
            kw["ip_adapter_image"] = ip_image
        base = seed if seed is not None and seed >= 0 else int(torch.randint(0, 2**31 - 1 - n, (1,)).item())
        neg = (negative + ", " if negative else "") + negative_for(kind)
        outs = []
        try:
            for i in range(n):
                gen = torch.Generator("cpu").manual_seed(base + i)
                img = pipe(prompt=build_prompt(prompt, bg, kind), negative_prompt=neg, num_inference_steps=steps,
                           guidance_scale=cfg, width=size, height=size, generator=gen, **kw).images[0]
                outs.append((img, base + i))
                if PROGRESS:
                    try:
                        PROGRESS(i + 1, n)
                    except Exception:
                        pass
                torch.cuda.empty_cache()
        except Exception:
            # a failed run (e.g. OOM) can leave offload hooks half-applied: drop the pipeline so the next try starts clean
            pipe = None
            _cache.update(key=None, pipe=None)
            gc.collect()
            torch.cuda.empty_cache()
            raise
        return outs


def _load_inpaint(ckpt, lora, lora_w, lora_dir, use_ip=False):
    import torch
    from diffusers import StableDiffusionXLInpaintPipeline, EulerAncestralDiscreteScheduler
    key = (ckpt, lora, lora_w, "inpaint", use_ip)
    if _cache["key"] == key:
        return _cache["pipe"]
    _cache.update(key=None, pipe=None)
    gc.collect()
    torch.cuda.empty_cache()
    pipe = StableDiffusionXLInpaintPipeline.from_single_file(ckpt, torch_dtype=torch.float16, use_safetensors=True)
    pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    if lora:
        pipe.load_lora_weights(str(Path(lora_dir)), weight_name=lora, adapter_name="pixel")
        pipe.set_adapters(["pixel"], [lora_w])
    if use_ip:  # appearance from a reference image (downloads ~3 GB once, then cached)
        pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter_sdxl.safetensors")
    pipe.enable_model_cpu_offload()
    try:
        pipe.vae.enable_tiling()
    except AttributeError:
        pipe.enable_vae_tiling()
    _cache.update(key=key, pipe=pipe)
    return pipe


def smoke_test(ckpt, lora, lora_dir):
    """Diagnostics: load SDXL (+LoRA) and render 4 steps at 512 px. Reports load time, run time and peak VRAM."""
    import torch
    with _lock:
        try:
            t0 = time.time()
            pipe = _load(ckpt, lora, 1.0, lora_dir, False, False, None)
            load_s = time.time() - t0
            _apply_sampler(pipe)
            torch.cuda.reset_peak_memory_stats()
            t1 = time.time()
            pipe(prompt=build_prompt("small knight"), negative_prompt=NEGATIVE, num_inference_steps=4, guidance_scale=6.0,
                 width=512, height=512, generator=torch.Generator("cpu").manual_seed(1))
            return {"load_s": round(load_s, 1), "run_s": round(time.time() - t1, 1),
                    "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2),
                    "total_vram_gb": round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1)}
        except Exception:
            pipe = None
            _cache.update(key=None, pipe=None)
            gc.collect()
            torch.cuda.empty_cache()
            raise


def inpaint(ckpt, lora, lora_w, lora_dir, prompt, negative, image, mask, strength=0.45, steps=22, cfg=7.0, seed=0,
            bg="magenta", kind="sprite", ip_image=None, ip_scale=0.7):
    """Repaint only the white area of `mask` (low strength = stay close to what is there). Returns a PIL RGB image."""
    import torch
    with _lock:
        pipe = _load_inpaint(ckpt, lora, lora_w, lora_dir, ip_image is not None)
        _apply_sampler(pipe)
        kw = {}
        if ip_image is not None:
            pipe.set_ip_adapter_scale(ip_scale)
            kw["ip_adapter_image"] = ip_image
        try:
            neg = (negative + ", " if negative else "") + negative_for(kind)
            gen = torch.Generator("cpu").manual_seed(int(seed))
            out = pipe(prompt=build_prompt(prompt, bg, kind), negative_prompt=neg, image=image, mask_image=mask,
                       strength=strength, num_inference_steps=steps, guidance_scale=cfg,
                       width=image.width, height=image.height, generator=gen, **kw).images[0]
            torch.cuda.empty_cache()
            return out
        except Exception:
            pipe = None
            _cache.update(key=None, pipe=None)
            gc.collect()
            torch.cuda.empty_cache()
            raise
