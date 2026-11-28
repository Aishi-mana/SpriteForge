"""Wan 2.2 Fun 5B spatial control, using native ComfyUI nodes."""
import base64,binascii,io
from pathlib import Path
from PIL import Image,ImageOps
from . import world

MODEL="wan22-fun5b"
WEIGHTS=["Wan2.2-Fun-5B-Control-Q4_K_M.gguf","Wan2.2-Fun-5B-Control-Q3_K_M.gguf","wan2.2_fun_control_5B_bf16.safetensors"]
VAES=["wan2.2_vae.safetensors","Wan2.2_VAE.safetensors"]

def files(root):
    def find(names,folders):
        return next((n for n in names if root and any((root/f/n).is_file() for f in folders)),None)
    return find(WEIGHTS,("unet","diffusion_models")),find(VAES,("vae",))

def settings(body):
    n=world.integer
    w=n(body.get("width",480),256,768,"video width")
    h=n(body.get("height",480),256,768,"video height")
    count=n(body.get("frames",33),9,97,"video frames")
    if w%16 or h%16 or (count-1)%4 or w*h*count>24_000_000:raise ValueError("Control needs dimensions divisible by 16, 4n+1 frames and at most 24M pixels")
    mode=body.get("control_kind","prepared")
    if mode not in ("prepared","canny"):raise ValueError("Invalid spatial control type")
    video=body.get("control_video")
    if not isinstance(video,str) or not video.startswith("data:video/mp4;base64,") or len(video)>44_000_000:raise ValueError("Choose a prepared control MP4, at most 32 MB")
    try:raw=base64.b64decode(video.split(",",1)[1],validate=True)
    except (ValueError,binascii.Error):raise ValueError("Invalid control MP4")
    if len(raw)>32_000_000 or len(raw)<12 or raw[4:8]!=b"ftyp":raise ValueError("Invalid or oversized control MP4")
    return dict(width=w,height=h,frames=count,steps=n(body.get("steps",20),10,60,"control steps"),control_kind=mode,control_bytes=raw)

def prepare(q,folder):
    """Decode a bounded prefix, sample exact requested count at target FPS, no stretching in time."""
    import imageio.v2 as imageio
    import numpy as np
    source=folder/"source.mp4"
    source.write_bytes(q["control_bytes"])
    reader=imageio.get_reader(str(source))
    try:
        meta=reader.get_meta_data()
        fps=float(meta.get("fps",0))
        size=meta.get("size",(0,0))
        if not 1<=fps<=120 or len(size)!=2 or min(size)<1 or max(size)>2048:raise ValueError("Control video needs 1–120 FPS and dimensions at most 2048")
        indices=[int(i*fps/q["fps"]+.5) for i in range(q["frames"])]
        frames=[]
        last=-1
        for i in indices:
            if i!=last:
                try:im=Image.fromarray(reader.get_data(i)).convert("RGB")
                except (IndexError,RuntimeError,ValueError):raise ValueError("Control video is shorter than requested animation")
                frame=np.asarray(ImageOps.pad(im,(q["width"],q["height"]),method=Image.Resampling.BILINEAR,color=(0,0,0)))
                last=i
            frames.append(frame)
    finally:reader.close()
    imageio.mimwrite(str(folder/"control.mp4"),frames,fps=q["fps"],codec="libx264",macro_block_size=1,ffmpeg_log_level="error")

def graph(q,clip):
    weight=q["control_weight"]
    def node(cls,**inputs):return {"class_type":cls,"inputs":inputs}
    g={
      "model":node("UnetLoaderGGUF",unet_name=weight) if weight.endswith(".gguf") else node("UNETLoader",unet_name=weight,weight_dtype="default"),
      "clip":node("CLIPLoader",clip_name=clip,type="wan",device="default"),
      "vae":node("VAELoader",vae_name=q["control_vae"]),
      "ref":node("LoadImage",image="reference.png"),
      "video":node("LoadVideo",file="control.mp4"),
      "components":node("GetVideoComponents",video=["video",0]),
      "shift":node("ModelSamplingSD3",model=["model",0],shift=8.0),
      "pos":node("CLIPTextEncode",clip=["clip",0],text=q["prompt"]),
      "neg":node("CLIPTextEncode",clip=["clip",0],text="blurry, distorted, inconsistent character, watermark, text"),
      "control":node("Wan22FunControlToVideo",positive=["pos",0],negative=["neg",0],vae=["vae",0],width=q["width"],height=q["height"],length=q["frames"],batch_size=1,ref_image=["ref",0],control_video=["components",0]),
      "sample":node("KSampler",model=["shift",0],seed=q["seed"],steps=q["steps"],cfg=5.0,sampler_name="uni_pc",scheduler="simple",positive=["control",0],negative=["control",1],latent_image=["control",2],denoise=1.0),
      "decode":node("VAEDecode",samples=["sample",0],vae=["vae",0]),
      "vid":node("CreateVideo",images=["decode",0],fps=q["fps"]),
      "save":node("SaveVideo",video=["vid",0],filename_prefix="spriteforge",format="mp4",codec="auto")
    }
    if q["control_kind"]=="canny":
        g["edges"]=node("Canny",image=["components",0],low_threshold=.1,high_threshold=.6)
        g["control"]["inputs"]["control_video"]=["edges",0]
    return g
