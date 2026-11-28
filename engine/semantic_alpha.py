"""Offline BiRefNet alpha extraction via the installed ComfyUI core nodes."""
import json, os, socket, subprocess, time, tempfile, shutil
from pathlib import Path
from PIL import Image
from . import local_runtime, wan_video as W

MODEL="birefnet.safetensors"

def readiness(root):
    p=W.model_root(root)
    comfy,python=local_runtime.runtime()
    missing=[]
    if not p or not (p/"background_removal"/MODEL).is_file():missing.append(MODEL)
    if not (comfy/"main.py").is_file():missing.append("ComfyUI main.py")
    if not python.is_file():missing.append("ComfyUI Python")
    return {"detected":not missing,"missing":missing},p,comfy,python

def graph(filename,prefix):
    g=json.loads((Path(__file__).parent/"workflows/birefnet.json").read_text(encoding="utf-8"))
    g["img"]["inputs"]["image"]=filename
    g["bgm"]["inputs"]["bg_removal_name"]=MODEL
    g["save"]["inputs"]["filename_prefix"]=prefix
    return g

def masks(images,root):
    from . import generate as gen
    ready,p,comfy,python=readiness(root)
    if not ready["detected"]:raise RuntimeError("BiRefNet setup missing: "+", ".join(ready["missing"]))
    if not gen._lock.acquire(blocking=False):raise RuntimeError("GPU busy; finish the current job first")
    d=None
    try:
        import gc,torch
        gen._cache.update(key=None,pipe=None,cn_name=None);gc.collect()
        if torch.cuda.is_available():torch.cuda.empty_cache()
        d=Path(tempfile.mkdtemp(prefix="spriteforge-alpha-"))
        for name in ("input","output","temp","user"):(d/name).mkdir()
        (d/"paths.yaml").write_text(json.dumps({"spriteforge":{"base_path":str(p.resolve()),"background_removal":"background_removal"}}),encoding="utf-8")
        with socket.socket() as sock:
            sock.bind(("127.0.0.1",0));port=sock.getsockname()[1]
        args=[str(python.resolve()),"main.py","--listen","127.0.0.1","--port",str(port),"--disable-auto-launch","--disable-all-custom-nodes","--extra-model-paths-config",str(d/"paths.yaml")]
        for name in ("input","output","temp","user"):args.extend(["--"+name+"-directory",str(d/name)])
        env=dict(os.environ,HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",PYTHONUNBUFFERED="1",PYTHONIOENCODING="utf-8")
        with (d/"engine.log").open("w",encoding="utf-8") as log:
            child=subprocess.Popen(args,cwd=comfy,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            try:
                deadline=time.monotonic()+180
                while True:
                    if child.poll() is not None:raise RuntimeError("BiRefNet runtime exited")
                    try:W.http(port,"/system_stats",timeout=3);break
                    except (OSError,ValueError,RuntimeError):pass
                    if time.monotonic()>deadline:raise RuntimeError("BiRefNet startup timed out")
                    time.sleep(1)
                info=W.http(port,"/object_info",timeout=60)
                missing=set(v["class_type"] for v in graph("frame.png","alpha").values())-set(info)
                if missing:raise RuntimeError("BiRefNet core nodes unavailable: "+", ".join(sorted(missing)))
                out=[]
                deadline=time.monotonic()+1800
                for i,im in enumerate(images):
                    name=f"frame-{i:04d}.png";prefix=f"alpha-{i:04d}"
                    im.convert("RGB").save(d/"input"/name)
                    pid=W.http(port,"/prompt",{"prompt":graph(name,prefix),"client_id":"spriteforge-alpha"},60)["prompt_id"]
                    while True:
                        if child.poll() is not None:raise RuntimeError("BiRefNet runtime exited")
                        if time.monotonic()>deadline:raise RuntimeError("BiRefNet batch timed out")
                        entry=W.http(port,"/history/"+pid).get(pid,{})
                        status=entry.get("status",{})
                        if status.get("status_str")=="error":raise RuntimeError("BiRefNet inference failed: "+str(status.get("messages",[]))[-1200:])
                        if status.get("completed") or status.get("status_str")=="success":break
                        time.sleep(.3)
                    files=list((d/"output").glob(prefix+"_*.png"))
                    if len(files)!=1:raise RuntimeError("BiRefNet did not return one alpha PNG")
                    with Image.open(files[0]) as result:
                        if result.mode!="RGBA" or result.size!=im.size:raise RuntimeError("Invalid BiRefNet alpha output")
                        alpha=result.getchannel("A")
                        if alpha.getextrema()[1]==0:raise RuntimeError("BiRefNet returned empty mask")
                        out.append(alpha.copy())
                return out
            finally:
                try:W.stop_owned(child)
                except (OSError,subprocess.TimeoutExpired):pass
    finally:
        if d is not None:
            try:
                logs=local_runtime.ROOT/"wan-logs";logs.mkdir(exist_ok=True)
                if (d/"engine.log").is_file():shutil.copyfile(d/"engine.log",logs/"last-alpha.log")
            except OSError:pass
            shutil.rmtree(d,ignore_errors=True)
        gen._lock.release()
