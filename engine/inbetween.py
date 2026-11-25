"""Endpoint-locked sprite transitions."""
import numpy as np
from PIL import Image
from . import pixelize as px, styles

def validate(start,end,count):
    if start.size != end.size:
        raise ValueError("Start and end images must have identical canvas dimensions")
    if not 2 <= count <= 32 or max(start.size)>1024 or start.width*start.height*count>32_000_000:
        raise ValueError("Use 2-32 frames, max 1024 px per side and 32 million total pixels")

def blend(start,end,t):
    a,b=[np.asarray(im.convert("RGBA"),dtype=np.float32)/255 for im in (start,end)]
    alpha=(1-t)*a[...,3:4]+t*b[...,3:4]
    rgb=((1-t)*a[...,:3]*a[...,3:4]+t*b[...,:3]*b[...,3:4])/np.maximum(alpha,1e-8)
    return Image.fromarray(np.clip(np.rint(np.concatenate((rgb,alpha),axis=2)*255),0,255).astype(np.uint8),"RGBA")

def frames(start,end,count,redraw=None):
    start,end=start.convert("RGBA"),end.convert("RGBA")
    validate(start,end,count)
    out=[start.copy()]
    for i in range(1,count-1):
        t=i/(count-1)
        guide=blend(start,end,t)
        im=redraw(guide,t,i) if redraw else guide
        if im.size!=start.size:
            raise ValueError("In-between renderer changed canvas dimensions")
        out.append(im.convert("RGBA"))
    return out+[end.copy()]

def ai_frame(guide,start,end,t,redraw,art_style,bg_tol=40):
    pixel=art_style=="pixel"
    w,h=guide.size
    side=768
    scale=side/max(w,h)
    rw,rh=max(1,round(w*scale)),max(1,round(h*scale))
    x,y=(side-rw)//2,(side-rh)//2
    resample=Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS
    def composite(im):
        canvas=Image.new("RGB",(side,side),"magenta")
        im=im.resize((rw,rh),resample)
        canvas.paste(im,(x,y),im)
        return canvas
    raw=redraw(composite(guide),Image.new("L",(side,side),255),composite(start if t<.5 else end))
    crop=raw.crop((x,y,x+rw,y+rh))
    if pixel:
        im=px.remove_bg(crop,bg_tol).resize((w,h),Image.Resampling.NEAREST)
        palette=px.palette_from_sprite(start)
        return px.quantize(im,32,palette if palette is not None else "none")
    im,_=styles.finish(crop,max(w,h),True,bg_tol)
    return im.resize((w,h),Image.Resampling.LANCZOS) if im.size!=(w,h) else im
