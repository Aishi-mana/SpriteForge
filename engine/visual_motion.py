"""CPU visual motion guide authoring. No AI redraw or pose detection."""
import io, tempfile
from pathlib import Path
from PIL import Image,ImageOps
from . import world

def settings(body):
    n=world.integer
    w=n(body.get("width",480),256,768,"guide width")
    h=n(body.get("height",480),256,768,"guide height")
    count=n(body.get("frames",33),9,97,"guide frames")
    fps=n(body.get("fps",16),8,30,"guide FPS")
    if w%16 or h%16 or (count-1)%4 or w*h*count>24_000_000:raise ValueError("Invalid guide dimensions or frame count")
    keys=body.get("keys")
    if not isinstance(keys,list) or not 2<=len(keys)<=12:raise ValueError("Choose 2–12 aligned pose images")
    out=[]
    total=0
    for k in keys:
        if not isinstance(k,dict):raise ValueError("Invalid visual key pose")
        t=n(k.get("at"),0,100,"key pose percent")
        src=k.get("image")
        if not isinstance(src,str):raise ValueError("Missing key pose image")
        total+=len(src)
        if total>16_000_000:raise ValueError("Key pose images exceed 16 MB")
        if out and t<=out[-1][0]:raise ValueError("Key pose times must strictly increase")
        im=world.image(src).convert("RGBA")
        if out and im.size!=out[0][1].size:raise ValueError("All key poses must use the same aligned canvas")
        out.append((t,im))
    if out[0][0]!=0 or out[-1][0]!=100:raise ValueError("Use 0% and 100% key poses")
    mode=body.get("mode","hold")
    if mode not in ("hold","blend"):raise ValueError("Invalid guide interpolation")
    return w,h,count,fps,out,mode

def render(body):
    w,h,count,fps,keys,mode=settings(body)
    prepared=[]
    for t,im in keys:
        im=ImageOps.pad(im,(w,h),method=Image.Resampling.LANCZOS,color=(0,0,0,0))
        bg=Image.new("RGB",(w,h),(0,0,0));bg.paste(im,mask=im.getchannel("A"))
        prepared.append((t,bg))
    frames=[];j=0
    for i in range(count):
        t=100*i/(count-1)
        while j+1<len(prepared) and t>=prepared[j+1][0]:j+=1
        at,im=prepared[j]
        if mode=="blend" and j+1<len(prepared):
            end,nxt=prepared[j+1]
            im=Image.blend(im,nxt,(t-at)/(end-at))
        frames.append(im)
    return frames,fps

def encode(frames,fps,path):
    import imageio.v2 as imageio
    import numpy as np
    imageio.mimwrite(str(path),[np.asarray(im) for im in frames],fps=fps,codec="libx264",macro_block_size=1,ffmpeg_log_level="error")
    if path.stat().st_size>32_000_000:raise ValueError("Guide video exceeds 32 MB")
    return path.read_bytes()

def generate(body):
    frames,fps=render(body)
    with tempfile.TemporaryDirectory() as d:return encode(frames,fps,Path(d)/"guide.mp4")

def prepare_video(body):
    from . import wan_control as C
    q=C.settings(body)
    q["fps"]=world.integer(body.get("fps",16),8,30,"guide FPS")
    q["start_ms"]=world.integer(body.get("start_ms",0),0,600000,"start time ms")
    with tempfile.TemporaryDirectory() as d:
        folder=Path(d);C.prepare(q,folder)
        path=folder/"control.mp4"
        if path.stat().st_size>32_000_000:raise ValueError("Guide exceeds 32 MB")
        return path.read_bytes()
