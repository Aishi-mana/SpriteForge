"""Owned, short-lived ComfyUI server for the shared Wan 2.2 GGUF workflow."""
import json, os, secrets, socket, subprocess, tempfile, time, urllib.request, urllib.error
from pathlib import Path
from . import local_runtime, full_frame_guidance as G, world

HIGH="Wan2.2-I2V-A14B-HighNoise-Q3_K_M.gguf"
LOW="Wan2.2-I2V-A14B-LowNoise-Q3_K_M.gguf"
LH="wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors"
LL="wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors"
CLIP="umt5_xxl_fp8_e4m3fn_scaled.safetensors"
VAE="wan_2.1_vae.safetensors"
MODEL="wan22-gguf"
STATUS={"stage":"Idle"}

def model_root(root):
    if root and Path(root).is_dir():return Path(root)
    local=os.environ.get("LOCALAPPDATA")
    if local:return Path(local)/"Comfy-Desktop/ComfyUI-Shared/models"
    return None

def readiness(root):
    p=model_root(root)
    comfy,python=local_runtime.runtime()
    nodes=sorted(x.name for x in (comfy/"custom_nodes").glob("*") if x.is_dir() and "gguf" in x.name.lower())
    missing=[]
    if not p or not p.is_dir():missing.append("Shared models folder")
    for name,folders in [(HIGH,("unet","diffusion_models")),(LOW,("unet","diffusion_models")),
                         (LH,("loras",)),(LL,("loras",)),(CLIP,("text_encoders","clip")),(VAE,("vae",))]:
        if not p or not any((p/f/name).is_file() for f in folders):missing.append(name)
    if not (comfy/"main.py").is_file():missing.append("ComfyUI main.py")
    if not python.is_file():missing.append("ComfyUI Python")
    if not nodes:missing.append("ComfyUI-GGUF custom node")
    return {"name":MODEL,"backend":"wan","label":"Wan 2.2 (shared ComfyUI GGUF)","missing":missing,"ready":not missing},p,comfy,python,nodes

def settings(body):
    n=world.integer
    w=n(body.get("width",480),256,768,"video width");h=n(body.get("height",480),256,768,"video height")
    count=n(body.get("frames",33),9,97,"video frames")
    if w%16 or h%16 or (count-1)%4:raise ValueError("Wan needs dimensions divisible by 16 and 4n+1 frames")
    if w*h*count>40_000_000:raise ValueError("Video exceeds pixel budget")
    steps=n(body.get("steps",4),2,60,"steps")
    if steps%2:raise ValueError("Wan requires an even step count")
    fps=n(body.get("fps",16),8,30,"FPS")
    seed=n(body.get("seed",-1),-1,2147483647,"seed")
    guidance=G.settings(body.get("guidance"))
    return dict(width=w,height=h,frames=count,steps=steps,fps=fps,seed=seed if seed>=0 else secrets.randbelow(2147483648),
                guidance=guidance,prompt=G.prompt(body.get("prompt",""),guidance),reference=body.get("reference"))

def graph(q):
    template=json.loads((Path(__file__).parent/"workflows/wan22-i2v.json").read_text(encoding="utf-8"))
    vals={"%MODEL%":HIGH,"%MODEL_LOW%":LOW,"%LORA_HIGH%":LH,"%LORA_LOW%":LL,"%REF1%":"reference.png",
          "%PROMPT%":q["prompt"],"%NEGATIVE%":"blurry, distorted, watermark, text, static",
          "%SEED%":q["seed"],"%STEPS%":q["steps"],"%STEPS_HALF%":q["steps"]//2,"%CFG%":1.0,
          "%SAMPLER%":"euler","%SCHEDULER%":"simple","%WIDTH%":q["width"],"%HEIGHT%":q["height"],
          "%FRAMES%":q["frames"],"%PREFIX%":"spriteforge"}
    def fill(v):
        if isinstance(v,str):return vals.get(v,v)
        if isinstance(v,list):return [fill(x) for x in v]
        if isinstance(v,dict):return {k:fill(x) for k,x in v.items()}
        return v
    out=fill(template);out["vid"]["inputs"]["fps"]=q["fps"]
    out["save"]["inputs"]["format"]="mp4"
    return out

def http(port,path,body=None,timeout=10):
    req=urllib.request.Request(f"http://127.0.0.1:{port}"+path,
        data=None if body is None else json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=timeout) as res:return json.load(res)
    except urllib.error.HTTPError as e:raise RuntimeError("ComfyUI rejected request: "+e.read(4000).decode(errors="replace")) from e

def run(root,body):
    from . import generate as gen, full_frame_video as V
    ready,p,comfy,python,nodes=readiness(root)
    if not ready["ready"]:raise ValueError("Wan setup missing: "+", ".join(ready["missing"]))
    q=settings(body)
    if not gen._lock.acquire(blocking=False):raise RuntimeError("GPU busy; finish the current job first")
    try:
        import torch,gc
        if not torch.cuda.is_available():raise RuntimeError("CUDA GPU required")
        gen._cache.update(key=None,pipe=None,cn_name=None);gc.collect();torch.cuda.empty_cache()
        with tempfile.TemporaryDirectory(prefix="spriteforge-wan-") as tmp:
            d=Path(tmp)
            for name in ("input","output","temp","user"):(d/name).mkdir()
            V.prepare_reference(q["reference"],q["width"],q["height"],q["guidance"]).save(d/"input/reference.png")
            # JSON is valid YAML; isolate all per-job data from both desktop apps.
            (d/"paths.yaml").write_text(json.dumps({"spriteforge":{"base_path":str(p.resolve()),
                "diffusion_models":"unet\ndiffusion_models","text_encoders":"text_encoders\nclip","loras":"loras","vae":"vae"}}),encoding="utf-8")
            with socket.socket() as sock:
                sock.bind(("127.0.0.1",0));port=sock.getsockname()[1]
            args=[str(python.resolve()),"main.py","--listen","127.0.0.1","--port",str(port),"--disable-auto-launch",
                  "--disable-all-custom-nodes","--whitelist-custom-nodes",*nodes,"--extra-model-paths-config",str(d/"paths.yaml")]
            for name in ("input","output","temp","user"):args.extend(["--"+name+"-directory",str(d/name)])
            env=dict(os.environ,HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",PYTHONUNBUFFERED="1",PYTHONIOENCODING="utf-8")
            with (d/"engine.log").open("w",encoding="utf-8") as log:
                child=subprocess.Popen(args,cwd=comfy,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                try:
                    STATUS["stage"]="Starting shared ComfyUI runtime"
                    deadline=time.monotonic()+900
                    while True:
                        if child.poll() is not None:raise RuntimeError("ComfyUI startup failed: "+(d/"engine.log").read_text(errors="replace")[-1500:])
                        try:http(port,"/system_stats",timeout=3);break
                        except (OSError,ValueError,RuntimeError):pass
                        if time.monotonic()>deadline:raise RuntimeError("ComfyUI startup timed out")
                        time.sleep(1)
                    g=graph(q)
                    info=http(port,"/object_info",timeout=60)
                    absent=sorted({v["class_type"] for v in g.values()}-set(info))
                    if absent:raise RuntimeError("ComfyUI missing workflow nodes: "+", ".join(absent))
                    pid=http(port,"/prompt",{"prompt":g,"client_id":"spriteforge"},60)["prompt_id"]
                    STATUS["stage"]="Generating Wan motion"
                    deadline=time.monotonic()+3600
                    while time.monotonic()<deadline:
                        if child.poll() is not None:raise RuntimeError("ComfyUI stopped during generation")
                        entry=http(port,"/history/"+pid).get(pid)
                        if entry:
                            status=entry.get("status",{})
                            if status.get("status_str")=="error":raise RuntimeError("Wan generation failed: "+str(status.get("messages",[]))[-1800:])
                            if status.get("completed") or status.get("status_str")=="success":
                                files=list((d/"output").rglob("*.mp4"))
                                if len(files)!=1:raise RuntimeError("Wan did not return exactly one MP4")
                                if files[0].stat().st_size>64_000_000:raise RuntimeError("Generated video exceeds 64 MB")
                                return files[0].read_bytes()
                        time.sleep(1)
                    raise RuntimeError("Wan generation timed out")
                finally:
                    STATUS["stage"]="Releasing owned ComfyUI runtime"
                    if child.poll() is None:
                        child.terminate()
                        try:child.wait(timeout=15)
                        except subprocess.TimeoutExpired:child.kill();child.wait(timeout=15)
    finally:
        STATUS["stage"]="Idle"
        gen._lock.release()
