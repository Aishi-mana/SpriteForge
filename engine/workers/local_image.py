"""Owned one-shot local image worker. Adapted from ManaAI-CV-2 image_job.py.
No server, custom nodes, downloads or persistent model cache.
"""
import base64,io,json,logging,os,sys,time
from pathlib import Path
sys.dont_write_bytecode=True

def status(directory,**fields):
    tmp=directory/f"progress-{os.getpid()}.tmp"
    try:
        tmp.write_text(json.dumps(fields),encoding="utf-8")
        for _ in range(10):
            try:os.replace(tmp,directory/"progress.json");return
            except PermissionError:time.sleep(.05)
    finally:tmp.unlink(missing_ok=True)

def neta(r,d):
    from PIL import Image,ImageOps
    import numpy as np
    logging.basicConfig(level=logging.INFO)
    sys.path.insert(0,r["comfy"]);sys.argv=[sys.argv[0]]
    import comfy.options
    comfy.options.enable_args_parsing()
    import torch,comfy.sd,comfy.sample,comfy.utils
    import comfy.model_management as mm
    if not torch.cuda.is_available():raise RuntimeError("CUDA unavailable in configured Comfy environment")
    print("Memory mode:",mm.vram_state,"text encoder:",mm.text_encoder_device(),flush=True)
    t0=time.monotonic();timings={}
    def mark(k):timings[k]=round(time.monotonic()-t0,2);print(k,timings[k],flush=True)
    status(d,stage="loading",step=0)
    model,clip,vae,*_=comfy.sd.load_checkpoint_guess_config(r["checkpoint"],output_vae=True,output_clip=True,embedding_directory=[])
    if clip is None or vae is None:raise RuntimeError("NetaYume needs embedded encoder and VAE")
    if r.get("lora"):
        lora=comfy.utils.load_torch_file(r["lora"],safe_load=True)
        model,clip=comfy.sd.load_lora_for_models(model,clip,lora,r["loraWeight"],r["loraWeight"]);del lora
    mark("checkpoint_loaded")
    status(d,stage="encoding",step=0)
    with torch.inference_mode():
        positive=clip.encode_from_tokens_scheduled(clip.tokenize(r["prompt"]))
        negative=clip.encode_from_tokens_scheduled(clip.tokenize(r["negative"]))
        mark("prompts_encoded")
        if r.get("reference"):
            from qwen_image import avatar_reference
            ref=avatar_reference(r["reference"])
            ref=ImageOps.pad(ref,(r["width"],r["height"]),method=Image.Resampling.LANCZOS,color="white")
            ref.save(d/"reference.jpg",quality=92)
            latent=vae.encode(torch.from_numpy(np.asarray(ref).copy()).float().div(255).unsqueeze(0))
        else:latent=torch.zeros([1,16,r["height"]//8,r["width"]//8],device="cpu")
        noise=comfy.sample.prepare_noise(latent,r["seed"])
        samples=comfy.sample.sample(model,noise,r["steps"],r["cfg"],"euler","normal",positive,negative,latent,denoise=r.get("referenceStrength",1.0),callback=lambda step,*_:status(d,stage="sampling",step=step+1,total=r["steps"]),disable_pbar=True,seed=r["seed"])
        mark("sampling_finished");status(d,stage="decoding",step=r["steps"])
        pixels=(vae.decode(samples)[0].detach().cpu().clamp(0,1)*255).to(torch.uint8).numpy()
    Image.fromarray(pixels).save(d/"image.png")
    mark("image_saved")
    (d/"generation.json").write_text(json.dumps(dict(backend="neta",sampler="euler",scheduler="normal",elapsed_seconds=timings,seed=r["seed"],reference_used=bool(r.get("reference")))),encoding="utf-8")
    status(d,stage="ready",step=r["steps"])

if __name__=="__main__":
    p=Path(sys.argv[1]).resolve();d=p.parent
    try:
        r=json.loads(p.read_text(encoding="utf-8"))
        if r["backend"]=="neta":neta(r,d)
        elif r["backend"]=="qwen":
            from qwen_image import generate_qwen
            generate_qwen(r,d,status)
        else:raise ValueError("Unsupported worker backend")
    except Exception as e:
        status(d,stage="error",error=str(e)[:1000]);raise
