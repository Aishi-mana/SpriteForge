"""Standalone worker bridge, using existing local Comfy libraries without a server."""
import base64, io, json, os, subprocess, tempfile, time
from pathlib import Path
from PIL import Image, ImageOps

QWEN="Qwen-Rapid-AIO-SFW-v23.safetensors"
NETA="NetaYumev35_pretrained_all_in_one.safetensors"
ROOT=Path(__file__).resolve().parent.parent

def runtime():
    default=Path(os.environ.get("LOCALAPPDATA",""))/"Comfy-Desktop/ComfyUI-Installs/ComfyUI/ComfyUI"
    root=Path(os.environ.get("SPRITEFORGE_COMFY_ROOT",str(default)))
    python=Path(os.environ.get("SPRITEFORGE_COMFY_PYTHON",str(root/".venv/Scripts/python.exe")))
    return root,python

def qwen_files(models,checkpoint=None):
    p=Path(models)
    return {"model":Path(checkpoint) if checkpoint else p/"diffusion_models"/QWEN,
            "clip":p/"text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors",
            "vae":p/"vae/qwen_image_vae.safetensors"}

def route(path):
    p=Path(path)
    if p.name==NETA and p.is_file():return "neta"
    if p.name==QWEN and p.is_file():return "qwen"
    return None

def readiness(path):
    p=Path(path); kind=route(p)
    root,python=runtime()
    missing=[str(x) for x in (python,root/"comfy/sd.py") if not x.is_file()]
    if kind=="qwen":
        missing += [str(x) for x in qwen_files(p.parent.parent,p).values() if not x.is_file()]
        if not (root/"comfy_extras/nodes_qwen.py").is_file():missing.append("Comfy Qwen core operations")
    return kind,missing

def reference_uri(im,bg):
    from PIL import ImageColor
    im=im.convert("RGBA");im.thumbnail((1024,1024),Image.Resampling.LANCZOS)
    canvas=Image.new("RGB",im.size,ImageColor.getrgb(bg.replace(" ","")));canvas.paste(im,(0,0),im)
    b=io.BytesIO()
    for quality in (92,85,75,60):
        b.seek(0);b.truncate();canvas.save(b,"JPEG",quality=quality)
        value="data:image/jpeg;base64,"+base64.b64encode(b.getvalue()).decode()
        if len(value)<=1_000_000:return value
    raise ValueError("Reference exceeds worker input budget")

def request(ckpt,lora_dir,lora,lw,prompt,negative,steps,cfg,seed,size,reference=None,bg="white",ip_scale=.7):
    kind,missing=readiness(ckpt)
    if not kind or missing:raise ValueError("Local runtime not ready: "+", ".join(missing))
    from . import model_families as mf
    mf.check_lora(ckpt,lora_dir,lora)
    if not prompt.strip() or len(prompt)>6000 or len(negative)>6000:raise ValueError("Prompt exceeds local worker limits")
    root,python=runtime()
    side=max(128,min(1024,int(size)))//64*64
    req=dict(backend=kind,comfy=str(root.resolve()),checkpoint=str(Path(ckpt).resolve()),
             prompt=prompt,negative=negative,width=side,height=side,steps=max(1,min(50,int(steps))),
             cfg=max(1,min(15,float(cfg))),seed=int(seed)%(2**32),cpu=False)
    if lora:
        req["lora"]=str((Path(lora_dir)/lora).resolve());req["loraWeight"]=max(0.,min(2.,float(lw)))
    if kind=="qwen":
        req["qwenFiles"]={k:str(v.resolve()) for k,v in qwen_files(Path(ckpt).parent.parent,ckpt).items()}
    if reference is not None:
        req["reference"]=reference_uri(reference,bg)
        if kind=="neta":req["referenceStrength"]=max(.2,min(.8,1-float(ip_scale)))
    return python,req

def run(python,req,progress=None,cancelled=None):
    if cancelled and cancelled():raise RuntimeError("Cancelled before worker launch")
    jobroot=ROOT/"local-image-jobs";jobroot.mkdir(exist_ok=True)
    job=Path(tempfile.mkdtemp(prefix="image-",dir=jobroot))
    input_path=job/"request.json"
    input_path.write_text(json.dumps(req,ensure_ascii=False),encoding="utf-8")
    worker=Path(__file__).resolve().parent/"workers/local_image.py"
    env=dict(os.environ,HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",DIFFUSERS_OFFLINE="1",PYTHONIOENCODING="utf-8")
    with (job/"job.log").open("w",encoding="utf-8") as log:
        child=subprocess.Popen([str(python),str(worker),str(input_path)],shell=False,stdout=log,stderr=subprocess.STDOUT,env=env,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        try:
            last=None
            while child.poll() is None:
                if cancelled and cancelled():raise RuntimeError("Cancelled local image worker")
                if progress:
                    try:
                        d=json.loads((job/"progress.json").read_text(encoding="utf-8"))
                        step=int(d.get("step",0))
                        if step!=last:progress(step,req["steps"]);last=step
                    except (OSError,ValueError):pass
                time.sleep(.25)
        finally:
            if child.poll() is None:
                if os.name=="nt":
                    subprocess.run(["taskkill.exe","/PID",str(child.pid),"/T","/F"],capture_output=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                if child.poll() is None:child.terminate()
                child.wait()
    png=job/"image.png"
    if child.returncode!=0 or not png.is_file():
        try: detail=json.loads((job/"progress.json").read_text(encoding="utf-8")).get("error","")
        except (OSError,ValueError):detail=""
        raise RuntimeError(f"Local {req['backend']} worker failed (exit {child.returncode}). {detail} Log: {job/'job.log'}")
    with Image.open(png) as im:return im.convert("RGB")
