"""Optional CPU in-betweens with premultiplied alpha and bounded translation."""
import base64, io
import numpy as np
from PIL import Image
from . import world, full_frame as F, full_frame_consistency as C

def settings(q):
    if not isinstance(q,dict):raise ValueError("Invalid interpolation options")
    mode=q.get("mode","motion")
    if mode not in ("hold","blend","motion"):raise ValueError("Invalid interpolation mode")
    return dict(mode=mode,factor=world.integer(q.get("factor",2),2,4,"interpolation factor"),
        strength=world.integer(q.get("strength",100),0,100,"motion strength"),
        max_shift=world.integer(q.get("max_shift",32),0,128,"maximum shift"),
        preserve_duration=world.boolean(q.get("preserve_duration",True),"preserve duration"))

def blend(a,b,t):
    aa=a[:,:,3:4].astype(np.float32)/255
    ba=b[:,:,3:4].astype(np.float32)/255
    alpha=aa*(1-t)+ba*t
    premul=a[:,:,:3].astype(np.float32)*aa*(1-t)+b[:,:,:3].astype(np.float32)*ba*t
    rgb=np.divide(premul,alpha,out=np.zeros_like(premul),where=alpha>0)
    return np.rint(np.clip(np.concatenate([rgb,alpha*255],axis=2),0,255)).astype(np.uint8)

def between(a,b,t,q):
    if q["mode"]=="hold":return a if t<.5 else b
    if q["mode"]=="motion":
        sa,sb=C.stats(a),C.stats(b)
        if sa is not None and sb is not None:
            dx,dy=np.clip((sb[:2]-sa[:2])*q["strength"]/100,-q["max_shift"],q["max_shift"])
            a=C.shift(a,int(round(dx*t)),int(round(dy*t)))
            b=C.shift(b,int(round(-dx*(1-t))),int(round(-dy*(1-t))))
    return blend(a,b,t)

def interpolate(doc,options):
    d=F.validate(doc);q=settings(options);frames=d["frames"];n=len(frames)
    if n<2:raise ValueError("At least two frames are required")
    factor=q["factor"];count=n*factor if d["loop"] or q["preserve_duration"] else (n-1)*factor+1
    fps=d["fps"]*factor if q["preserve_duration"] else d["fps"]
    if fps!=d["fps"] and any(v["frames"] for v in d["directions"].values()):raise ValueError("Cannot change shared FPS for only one direction; disable preserve duration")
    if fps>60:raise ValueError("Preserving duration would exceed 60 FPS")
    if count>F.MAX_FRAMES or count*d["width"]*d["height"]>F.MAX_PIXELS:raise ValueError("Interpolated sequence exceeds frame or pixel budget")
    out=[];encoded=0
    # Keep only the current and next decoded frame; hold mode needs no arrays.
    current=None; next_array=None
    def append(s):
        nonlocal encoded
        encoded+=len(s)
        if encoded>F.MAX_ENCODED:raise ValueError("Interpolated sequence exceeds encoded budget")
        out.append(s)
    for i,s in enumerate(frames):
        append(s)
        if i==n-1 and not d["loop"]:
            if q["preserve_duration"]:
                for _ in range(factor-1):append(s)
            continue
        j=(i+1)%n
        if q["mode"]!="hold":
            current=next_array if next_array is not None else np.array(world.image(s))
            next_array=np.array(world.image(frames[j]))
        for k in range(1,factor):
            if q["mode"]=="hold":append(s if k/factor<.5 else frames[j]);continue
            result=between(current,next_array,k/factor,q)
            buf=io.BytesIO();Image.fromarray(result,"RGBA").save(buf,"PNG")
            append("data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode())
    return F.validate({**d,"combat":[{**v,"frame":v["frame"]*factor} for v in d["combat"]],"fps":fps,"frames":out,"keyframes":[k*factor for k in d["keyframes"]],"locked_frames":[k*factor for k in d["locked_frames"]]})
