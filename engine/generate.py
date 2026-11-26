"""SDXL + pixel-art LoRA, optional IP-Adapter reference conditioning. Tuned for 8 GB VRAM."""
import gc
import time
import threading
from pathlib import Path
from PIL import Image
from . import styles, model_families as mf

_lock = threading.Lock()
_job_context = threading.local()
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


def negative_for(kind, art_style="pixel"):
    if kind == "instruction_edit":
        return "blurry, watermark, text, duplicate character, unintended changes"
    if kind in PORTRAIT_FRAMINGS:
        return (NEGATIVE if art_style == "pixel" else styles.HD_NEGATIVE) + ", " + PORTRAIT_FRAMINGS[kind][1]
    if kind == "character_art":
        return (NEGATIVE if art_style == "pixel" else styles.HD_NEGATIVE) + ", close-up, headshot, waist-up, feet out of frame, character sheet, multiple views"
    if kind == "modular_asset":
        return "person, mannequin, face, skin, hands, body, scenery, cast shadow, text, watermark, cropped item, duplicate items, blurry"
    if kind == "sprite" and art_style != "pixel":
        return styles.HD_NEGATIVE
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
    _job_context.sampler = name if name in SAMPLERS else "euler_a"


def _progress(done,total):
    cb=getattr(_job_context,"progress",None)
    if cb:
        try:cb(done,total)
        except Exception:pass


def _check_cancelled():
    cb=getattr(_job_context,"cancelled",None)
    if cb and cb():raise RuntimeError("Generation cancelled")


def _apply_sampler(pipe):
    """Swap the scheduler (cheap, no reload). DPM++ 2M Karras converges to cleaner detail than Euler ancestral at equal steps."""
    from diffusers import EulerAncestralDiscreteScheduler, DPMSolverMultistepScheduler, EulerDiscreteScheduler
    if type(pipe.scheduler).__name__.startswith("FlowMatch"):
        return  # keep architecture-native flow schedule
    cfg = pipe.scheduler.config
    sampler=getattr(_job_context,"sampler",SAMPLER)
    if sampler == "dpmpp_2m_karras":
        pipe.scheduler = DPMSolverMultistepScheduler.from_config(cfg, use_karras_sigmas=True, algorithm_type="dpmsolver++")
    elif sampler == "euler":
        pipe.scheduler = EulerDiscreteScheduler.from_config(cfg)
    else:
        pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(cfg)


PORTRAIT_FRAMINGS = {
    "portrait_face": ("face close-up, head fully visible", "full body, waist-up, distant subject"),
    "portrait_bust": ("head, shoulders and upper chest, bust portrait", "full body, legs, extreme close-up"),
    "portrait_half": ("waist-up portrait, head and torso visible", "full body, feet, extreme close-up"),
    "portrait_full": ("full-length portrait, head to toe, feet visible, margin above and below", "headshot, waist-up, feet out of frame"),
}


def build_prompt(user_prompt, bg="white", kind="sprite", art_style="pixel"):
    if kind == "instruction_edit":
        return user_prompt
    if kind in PORTRAIT_FRAMINGS:
        return f"{styles.PRESETS[art_style]}, character portrait, {user_prompt}, {PORTRAIT_FRAMINGS[kind][0]}, single character, centered, plain flat solid {bg} background"
    if kind == "character_art":
        return f"{styles.PRESETS[art_style]}, full-length character concept illustration, {user_prompt}, single character, entire body head to toe visible, feet visible, centered with space above and below, plain flat solid {bg} background"
    if kind == "modular_asset":
        return f"{styles.PRESETS[art_style]}, {user_prompt}, isolated game customization asset, plain flat solid {bg} background"
    if kind == "sprite" and art_style != "pixel":
        return f"{styles.PRESETS[art_style]}, {user_prompt}, single character, full body, centered, plain flat solid {bg} background"
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
    family=mf.identify(ckpt)
    mf.check_lora(ckpt,lora_dir,lora)
    if family not in ("sdxl","unknown") and (use_ip or use_cn):
        raise ValueError("Reference IP-Adapter and ControlNet currently require SDXL")
    key = (ckpt, lora, lora_w, use_ip, use_cn)
    if _cache["key"] == key:
        return _cache["pipe"]
    _cache.update(key=None, pipe=None)
    gc.collect()
    torch.cuda.empty_cache()
    if family=="sd15":
        from diffusers import StableDiffusionPipeline
        pipe=(StableDiffusionPipeline.from_pretrained(ckpt,torch_dtype=torch.float16,local_files_only=True) if Path(ckpt).is_dir() else StableDiffusionPipeline.from_single_file(ckpt,torch_dtype=torch.float16,use_safetensors=True))
    elif family in mf.FLOW:
        import diffusers
        cls=getattr(diffusers, next(k for k,v in mf.FOLDERS.items() if v==family))
        if Path(ckpt).is_dir():
            pipe=cls.from_pretrained(ckpt,torch_dtype=torch.bfloat16,local_files_only=True)
        elif family=="lumina2":
            base=Path(ckpt).parent/"Lumina2-base"
            transformer=diffusers.Lumina2Transformer2DModel.from_single_file(ckpt,config=str(base/"transformer"),torch_dtype=torch.bfloat16,local_files_only=True)
            pipe=cls.from_pretrained(str(base),transformer=transformer,torch_dtype=torch.bfloat16,local_files_only=True)
        else: raise ValueError("This model needs a complete Diffusers pipeline folder")
    elif use_cn:
        cn, cn_name = _controlnet(cn_dir)
        pipe = (StableDiffusionXLControlNetPipeline.from_pretrained(ckpt,controlnet=cn,torch_dtype=torch.float16,local_files_only=True) if Path(ckpt).is_dir() else StableDiffusionXLControlNetPipeline.from_single_file(ckpt, controlnet=cn, torch_dtype=torch.float16, use_safetensors=True))
        _cache["cn_name"] = cn_name
    else:
        pipe = StableDiffusionXLPipeline.from_pretrained(ckpt,torch_dtype=torch.float16,local_files_only=True) if Path(ckpt).is_dir() else StableDiffusionXLPipeline.from_single_file(ckpt, torch_dtype=torch.float16, use_safetensors=True)
    if family not in mf.FLOW:
        pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)
    if lora:
        pipe.load_lora_weights(str(Path(lora_dir)), weight_name=lora, adapter_name="pixel")
        pipe.set_adapters(["pixel"], [lora_w])
    if use_ip:  # first use downloads ~3 GB from Hugging Face, then it's cached and works offline
        pipe.load_ip_adapter("h94/IP-Adapter", subfolder="sdxl_models", weight_name="ip-adapter_sdxl.safetensors")
    if use_cn or family in mf.FLOW:
        # UNet + ControlNet together don't fit in 8 GB; stream weights layer by layer (slower, but fits)
        pipe.enable_sequential_cpu_offload()
    else:
        pipe.enable_model_cpu_offload()  # fits 8 GB, spills to system RAM
    try:  # newer diffusers moved this onto the VAE; older ones have it on the pipeline
        pipe.vae.enable_tiling()
    except AttributeError:
        if hasattr(pipe,"enable_vae_tiling"): pipe.enable_vae_tiling()
    _cache.update(key=key, pipe=pipe)
    return pipe


def generate(ckpt, lora, lora_w, lora_dir, prompt, negative="", steps=25, cfg=7.0, seed=-1, size=1024, bg="white",
             ip_image=None, ip_scale=0.7, n=1, control_image=None, cn_scale=0.8, cn_dir=None, kind="sprite", art_style="pixel"):
    """Returns [(PIL image, seed), ...]. ip_image = reference sprite, control_image = OpenPose skeleton render."""
    import torch
    with _lock:
        from . import local_runtime as lr
        _check_cancelled()
        if lr.route(ckpt):
            if control_image is not None:raise ValueError("Local model does not support SDXL ControlNet")
            _cache.update(key=None,pipe=None);gc.collect();torch.cuda.empty_cache()
            base=seed if seed is not None and seed>=0 else int(torch.randint(0,2**31-1,(1,)).item())
            out=[]
            for i in range(n):
                _check_cancelled()
                py,req=lr.request(ckpt,lora_dir,lora,lora_w,build_prompt(prompt,bg,kind,art_style),(negative+", " if negative else "")+negative_for(kind,art_style),steps,cfg,base+i,size,ip_image,bg,ip_scale)
                out.append((lr.run(py,req,cancelled=getattr(_job_context,"cancelled",None)),req["seed"]))
                _progress(i+1,n)
            return out
        pipe = _load(ckpt, lora, lora_w, lora_dir, ip_image is not None, control_image is not None, cn_dir)
        _apply_sampler(pipe)
        family=mf.identify(ckpt)
        if family=="sd15": size=min(size,768)
        kw = {}
        if control_image is not None:
            kw.update(image=control_image.convert("RGB").resize((size, size)), controlnet_conditioning_scale=cn_scale,
                      control_guidance_end=0.9)
        if ip_image is not None:
            pipe.set_ip_adapter_scale(ip_scale)
            kw["ip_adapter_image"] = ip_image
        base = seed if seed is not None and seed >= 0 else int(torch.randint(0, 2**31 - 1 - n, (1,)).item())
        neg = (negative + ", " if negative else "") + negative_for(kind, art_style)
        outs = []
        try:
            for i in range(n):
                _check_cancelled()
                gen = torch.Generator("cpu").manual_seed(base + i)
                import inspect
                allowed=inspect.signature(pipe.__call__).parameters
                opts=dict(prompt=build_prompt(prompt,bg,kind,art_style),negative_prompt=neg,num_inference_steps=steps,guidance_scale=cfg,width=size,height=size,generator=gen,**kw)
                if family=="qwen" and "true_cfg_scale" in allowed: opts["true_cfg_scale"]=cfg
                if family in mf.FLOW: opts={k:v for k,v in opts.items() if k in allowed}
                img=pipe(**opts).images[0]
                outs.append((img, base + i))
                _progress(i+1,n)
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
    if mf.identify(ckpt) not in ("sdxl","unknown"):
        raise ValueError("Inpainting currently requires SDXL")
    mf.check_lora(ckpt,lora_dir,lora)
    key = (ckpt, lora, lora_w, "inpaint", use_ip)
    if _cache["key"] == key:
        return _cache["pipe"]
    _cache.update(key=None, pipe=None)
    gc.collect()
    torch.cuda.empty_cache()
    pipe = StableDiffusionXLInpaintPipeline.from_pretrained(ckpt,torch_dtype=torch.float16,local_files_only=True) if Path(ckpt).is_dir() else StableDiffusionXLInpaintPipeline.from_single_file(ckpt, torch_dtype=torch.float16, use_safetensors=True)
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
            bg="magenta", kind="sprite", ip_image=None, ip_scale=0.7, art_style="pixel"):
    """Repaint only the white area of `mask` (low strength = stay close to what is there). Returns a PIL RGB image."""
    import torch
    with _lock:
        _check_cancelled()
        pipe = _load_inpaint(ckpt, lora, lora_w, lora_dir, ip_image is not None)
        _apply_sampler(pipe)
        kw = {}
        if ip_image is not None:
            pipe.set_ip_adapter_scale(ip_scale)
            kw["ip_adapter_image"] = ip_image
        try:
            neg = (negative + ", " if negative else "") + negative_for(kind, art_style)
            gen = torch.Generator("cpu").manual_seed(int(seed))
            out = pipe(prompt=build_prompt(prompt, bg, kind, art_style), negative_prompt=neg, image=image, mask_image=mask,
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


def resource_status(torch_module=None):
    """Read process allocator and device-wide memory without loading a model."""
    from importlib.metadata import version, PackageNotFoundError
    versions = {}
    for name in ("torch", "diffusers", "accelerate", "transformers", "safetensors"):
        try:
            versions[name] = version(name)
        except PackageNotFoundError:
            versions[name] = None
    key = _cache.get("key")
    result = {"busy": _lock.locked(), "cached": _cache.get("pipe") is not None,
              "checkpoint": Path(key[0]).name if key else None,
              "dependencies": versions, "cuda": False, "memory": None}
    try:
        if torch_module is None:
            import torch as torch_module
        cuda = torch_module.cuda
        if cuda.is_available():
            free, total = cuda.mem_get_info(0)
            result.update(cuda=True, device=cuda.get_device_name(0),
                          memory={"free": int(free), "total": int(total),
                                  "allocated": int(cuda.memory_allocated(0)),
                                  "reserved": int(cuda.memory_reserved(0))})
    except Exception as exc:
        result["warning"] = type(exc).__name__ + ": " + str(exc)
    result["recommended_size"] = 640 if not result["memory"] or result["memory"]["total"] <= 8 * 2**30 else 768
    return result


def release_resources(unload=False, torch_module=None):
    """Do not mutate cached pipelines while generation or inpainting owns the lock."""
    if not _lock.acquire(blocking=False):
        raise RuntimeError("AI generation is busy; retry after the current operation finishes")
    try:
        if unload:
            _cache.update(key=None, pipe=None, cn_name=None)
        gc.collect()
        try:
            if torch_module is None:
                import torch as torch_module
            if torch_module.cuda.is_available():
                torch_module.cuda.empty_cache()
        except ImportError:
            pass
    finally:
        _lock.release()
    return resource_status(torch_module)
