"""Conservative architecture detection and local generation capabilities."""
import json
from pathlib import Path
from . import diag

FOLDERS={"StableDiffusionXLPipeline":"sdxl","StableDiffusionPipeline":"sd15",
         "Lumina2Pipeline":"lumina2","FluxPipeline":"flux","StableDiffusion3Pipeline":"sd3",
         "QwenImagePipeline":"qwen"}
FLOW={"lumina2","flux","sd3","qwen"}
NAMES={"sdxl":"SDXL","sd15":"SD 1.5","lumina2":"Lumina 2 / NetaYume","flux":"FLUX.1",
       "sd3":"SD3 / SD3.5","qwen":"Qwen-Image","unknown":"Unknown","dit":"Other DiT","other":"Other","broken":"Broken"}

def header(path):
    with open(path,"rb") as fp:
        n=int.from_bytes(fp.read(8),"little")
        if not 0<n<=400_000_000: raise ValueError("Bad header")
        return json.loads(fp.read(n))

def identify(path,lora=False):
    p=Path(path)
    if p.is_dir():
        try:
            name=json.loads((p/"model_index.json").read_text(encoding="utf-8"))["_class_name"]
            return FOLDERS.get(name,"other")
        except Exception: return "broken"
    d=diag.inspect_file(p,lora)
    if d["status"]!="ok": return "broken"
    if p.name=="NetaYumev35_pretrained_all_in_one.safetensors" and not lora:return "lumina2"
    from .local_runtime import QWEN_CHECKPOINTS
    if p.name in QWEN_CHECKPOINTS and not lora:return "qwen"
    h=header(p)
    meta=h.pop("__metadata__",{}) or {}
    ks=" ".join(h.keys()).lower()
    tags=" ".join(str(meta.get(k,"")) for k in ("modelspec.architecture","ss_base_model_version","ss_base_model","base_model","architecture")).lower()
    if "lumina" in tags or "netayume" in tags or "noise_refiner" in ks or "context_refiner" in ks or "cap_embedder" in ks: return "lumina2"
    if "flux" in tags or "double_blocks" in ks and "single_blocks" in ks or "single_transformer_blocks" in ks: return "flux"
    if "stable-diffusion-v3" in tags or "sd3" in tags or "joint_blocks" in ks: return "sd3"
    if "qwen" in tags or "img_mod" in ks and "txt_mod" in ks: return "qwen"
    if "sdxl" in tags or "stable-diffusion-xl" in tags: return "sdxl"
    if "sd1.5" in tags or "sd_v1" in tags or "stable-diffusion-v1" in tags: return "sd15"
    if lora and p.name=="modern-anime.safetensors" and d["kind"] in ("other","unknown"):return "qwen"  # documented installed Qwen adapter
    return d["kind"]

def describe(path):
    p=Path(path); family=identify(p)
    from . import local_runtime as lr
    route,missing=lr.readiness(p)
    if route and family!="broken":
        return {"family":family,"label":NAMES[family],"supported":not missing,"reference":not missing,"controlnet":False,"inpaint":False,"backend":route,"flow":True,"detail":("Local standalone runtime; image reference supported" if not missing else "Missing: "+", ".join(missing))}
    native=family in {"sdxl","sd15","unknown"} or (p.is_dir() and family in FLOW)
    # Comfy single-file Lumina transformer support requires explicitly installed local base pipeline.
    lumina_base=p.parent/"Lumina2-base"
    lumina_single=family=="lumina2" and p.is_file() and lumina_base.is_dir() and identify(lumina_base)=="lumina2"
    supported=native or lumina_single
    detail=("Text-to-image, reference and inpaint" if family=="sdxl" else
            "Legacy SDXL fallback; unverified architecture" if family=="unknown" else
            "Text-to-image only; use SDXL for reference / inpaint" if supported else
            "Install a complete local Diffusers pipeline folder" if family in FLOW else "Unsupported or broken architecture")
    if family=="lumina2" and p.is_file() and not supported:
        detail="Use a complete NetaYume Diffusers folder, or install Lumina2-base for compatible transformer single-file loading"
    return {"family":family,"label":NAMES.get(family,family),"supported":supported,
            "reference":family in {"sdxl","unknown"} and supported,"detail":detail,"flow":family in FLOW}

def compatibility(model,lora):
    if lora=="broken" or model=="broken": return "incompatible"
    if lora==model and model in {"sdxl","sd15"}|FLOW: return "match"
    if lora=="unknown" or model=="unknown": return "unknown"
    if lora=="other" and model in FLOW: return "unknown"
    return "incompatible"

def check_lora(ckpt,dir,name):
    if not name: return
    if Path(name).name!=name: raise ValueError("Invalid LoRA filename")
    p=Path(dir)/name
    if not p.is_file(): raise ValueError("LoRA file not found")
    family=identify(ckpt); lk=identify(p,True)
    if compatibility(family,lk)=="incompatible":
        raise ValueError(f"LoRA architecture {lk} is incompatible with {family}")
