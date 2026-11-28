"""CPU motion references from existing sprite frames, not anatomical pose inference."""
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, ImageFilter
from . import full_frame as F, world, visual_motion

def source(body):
    d=F.validate(body.get("document"))
    if not d["frames"]:raise ValueError("Import animation frames first")
    first=world.integer(body.get("first",0),0,len(d["frames"])-1,"first frame")
    last=world.integer(body.get("last",len(d["frames"])-1),first,len(d["frames"])-1,"last frame")
    return d,first,last

def inspect(body):
    d,first,last=source(body)
    rows=[];previous=None
    for i in range(first,last+1):
        a=np.asarray(world.image(d["frames"][i]).getchannel("A"))
        ys,xs=np.where(a>=128)
        center=[round(float(xs.mean()),3),round(float(ys.mean()),3)] if len(xs) else None
        box=[int(xs.min()),int(ys.min()),int(xs.max())+1,int(ys.max())+1] if len(xs) else None
        delta=[round(center[k]-previous[k],3) for k in range(2)] if center is not None and previous is not None else None
        rows.append(dict(frame=i,time_ms=round((i-first)*1000/d["fps"],3),bounds=box,centroid=center,delta=delta,ground_y=box[3]-1 if box else None,opaque=bool(np.all(a==255))))
        previous=center
    return dict(version=1,fps=d["fps"],size=[d["width"],d["height"]],pivot=d["pivot"],first=first,last=last,duration_ms=round(len(rows)*1000/d["fps"],3),frames=rows,method="alpha geometry; not skeletal pose detection")

def sample_indices(first,last,source_fps,count,fps):
    return [min(last,first+(i*source_fps)//fps) for i in range(count)]

def render(body):
    d,first,last=source(body)
    w=world.integer(body.get("width",384),256,768,"guide width")
    h=world.integer(body.get("height",384),256,768,"guide height")
    fps=world.integer(body.get("fps",12),8,30,"guide FPS")
    count=world.integer(body.get("frames",17),9,97,"guide frames")
    if w%16 or h%16 or (count-1)%4 or w*h*count>24_000_000:raise ValueError("Guide needs divisible-by-16 dimensions, 4n+1 frames and at most 24M pixels")
    kind=body.get("kind","artwork")
    if kind not in ("artwork","silhouette","edges"):raise ValueError("Invalid guide kind")
    frames=[];cache={}
    for i in sample_indices(first,last,d["fps"],count,fps):
        if i not in cache:
            im=ImageOps.pad(world.image(d["frames"][i]),(w,h),method=Image.Resampling.LANCZOS,color=(0,0,0,0))
            if kind=="silhouette":
                out=Image.merge("RGB",(im.getchannel("A"),)*3)
            else:
                out=Image.new("RGB",(w,h));out.paste(im,mask=im.getchannel("A"))
                if kind=="edges":out=out.convert("L").filter(ImageFilter.FIND_EDGES).convert("RGB")
            cache[i]=out
        frames.append(cache[i])
    return frames,fps

def generate(body):
    frames,fps=render(body)
    with tempfile.TemporaryDirectory() as tmp:
        return visual_motion.encode(frames,fps,Path(tmp)/"motion.mp4")
