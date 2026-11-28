"""Optional local Diffusers LTX image-to-video backend; no downloads on generation."""
import json, io, threading, tempfile, gc, secrets
from pathlib import Path
from PIL import Image, ImageOps
from . import world, full_frame_guidance as G

CLASSES={"LTXImageToVideoPipeline":"ltx"}
def discover(root):
    if not root:return []
    folder=Path(root)/"video_models"
    out=[]
    if not folder.is_dir():return out
    for p in sorted(folder.iterdir()):
        try:
            if not p.is_dir() or p.is_symlink():continue
            cls=json.loads((p/"model_index.json").read_text(encoding="utf-8")).get("_class_name")
            if cls in CLASSES:out.append({"name":p.name,"backend":CLASSES[cls]})
        except (OSError,ValueError,AttributeError):continue
    return out

def settings(body):
    if not isinstance(body,dict):raise ValueError("Invalid video request")
    n=world.integer
    w=n(body.get("width",512),256,768,"video width");h=n(body.get("height",512),256,768,"video height")
    count=n(body.get("frames",49),9,97,"video frame count")
    if w%32 or h%32 or (count-1)%8:raise ValueError("LTX requires dimensions divisible by 32 and frame count 8k+1")
    if w*h*count>40_000_000:raise ValueError("Video exceeds pixel budget")
    guidance=G.settings(body.get("guidance"))
    return dict(guidance=guidance,model=world.label(body.get("model"),"video model",180),prompt=G.prompt(body.get("prompt",""),guidance),
        width=w,height=h,frames=count,fps=n(body.get("fps",12),8,30,"video FPS"),steps=n(body.get("steps",30),1,60,"video steps"),
        seed=n(body.get("seed",-1),-1,2147483647,"video seed"),reference=body.get("reference"))

def prepare_reference(uri,w,h,guidance=None):
    im=world.image(uri)
    q=G.settings(guidance)
    margin=q["margin"]/100
    im.thumbnail((max(1,int(w*(1-2*margin))),max(1,int(h*(1-2*margin)))),Image.Resampling.LANCZOS)
    canvas=Image.new("RGB",(w,h),G.BACKGROUNDS[q["background"]][0])
    canvas.paste(im,((w-im.width)//2,(h-im.height)//2),im.getchannel("A"))
    return canvas

def generate(root,body,runner=None):
    q=settings(body)
    if q["model"] not in {m["name"] for m in discover(root)}:raise ValueError("Select a discovered local LTX video model")
    im=prepare_reference(q["reference"],q["width"],q["height"],q["guidance"])
    if q["seed"]<0:q["seed"]=secrets.randbelow(2147483648)
    return (runner or run_ltx)(Path(root)/"video_models"/q["model"],im,q)

def run_ltx(path,image,q):
    from . import generate as gen
    if not gen._lock.acquire(blocking=False):raise RuntimeError("GPU is busy; finish the current generation first")
    pipe=None
    try:
        import torch
        from diffusers import LTXImageToVideoPipeline
        from diffusers.utils import export_to_video
        if not torch.cuda.is_available():raise RuntimeError("CUDA GPU required for local LTX generation")
        gen._cache.update(key=None,pipe=None,cn_name=None)
        gc.collect();torch.cuda.empty_cache()
        pipe=LTXImageToVideoPipeline.from_pretrained(str(path),torch_dtype=torch.bfloat16,local_files_only=True)
        pipe.enable_model_cpu_offload()
        frames=pipe(image=image,prompt=q["prompt"],width=q["width"],height=q["height"],num_frames=q["frames"],
            num_inference_steps=q["steps"],generator=torch.Generator(device="cpu").manual_seed(q["seed"]),output_type="pil").frames[0]
        with tempfile.TemporaryDirectory() as tmp:
            target=str(Path(tmp)/"motion.mp4")
            export_to_video(frames,target,fps=q["fps"])
            return Path(target).read_bytes()
    except ImportError as exc:raise RuntimeError("Install a compatible Diffusers LTX runtime, Accelerate and imageio-ffmpeg") from exc
    finally:
        del pipe
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():torch.cuda.empty_cache()
        finally:gen._lock.release()
