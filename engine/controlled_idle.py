"""Small torso-only warp of a transparent reference; no AI redraw."""
import base64,io,math
import numpy as np
from scipy.ndimage import map_coordinates
from PIL import Image
from . import full_frame as F,world

def generate(doc,options):
    d=F.validate(doc)
    if d["locked_frames"]:raise ValueError("Unlock frames before replacement")
    if not d["reference"]:raise ValueError("Choose transparent character reference")
    if not isinstance(options,dict):raise ValueError("Invalid idle options")
    n=world.integer
    count=n(options.get("frames",32),8,97,"idle frames")
    fps=n(options.get("fps",16),8,30,"idle FPS")
    amplitude=n(options.get("amplitude",3),0,8,"breathing pixels")
    im=world.image(d["reference"]).convert("RGBA")
    if im.getchannel("A").getextrema()[0]==255:raise ValueError("Controlled idle requires a transparent reference")
    if not im.getchannel("A").getbbox():raise ValueError("Reference is empty")
    original=im
    ref_pixels=im.width*im.height
    shared=any(v["frames"] for v in d["directions"].values())
    # Old callers retain native resolution; the UI supplies an explicit maximum.
    side=n(options.get("max_side",max(im.size)),32,2048,"idle maximum size")
    auto=world.boolean(options.get("auto_fit",False),"automatic idle fit")
    remaining=F.MAX_ENCODED-len(d["reference"])
    pixels=(F.MAX_PIXELS-ref_pixels)//count
    if pixels<1 or remaining<1:raise ValueError("Original reference leaves no room for animation frames; choose a smaller reference.")
    if shared:
        if fps!=d["fps"]:raise ValueError("Use the existing directional FPS.")
        target=(d["width"],d["height"])
    else:
        scale=min(1,side/max(im.size),math.sqrt(pixels/ref_pixels))
        target=tuple(max(1,int(v*scale)) for v in im.size)
    for attempt in range(8):
        if target==original.size:im=original
        else:
            im=original.copy()
            im.thumbnail(target,Image.Resampling.NEAREST if d["pixel"] else Image.Resampling.LANCZOS)
            if shared and im.size!=target:
                canvas=Image.new("RGBA",target)
                canvas.paste(im,((target[0]-im.width)//2,target[1]-im.height))
                im=canvas
        w,h=im.size
        if w*h>pixels:raise ValueError("This canvas cannot hold the requested frame count. Reduce frames or use a smaller canvas.")
        out=render(im,count,amplitude,remaining)
        if out is not None:
            bbox=im.getchannel("A").getbbox()
            if not bbox:raise ValueError("Reference became empty after resizing.")
            return F.validate({**d,"width":w,"height":h,"pivot":d["pivot"] if shared else [w//2,bbox[3]-1],"fps":fps,"loop":True,"frames":out,"keyframes":[],"locked_frames":[],"combat":[]})
        if not auto or shared:break
        next_target=tuple(max(1,int(v*.8)) for v in target)
        if next_target==target:break
        target=next_target
    raise ValueError("The requested frames exceed the 24 MB stored-artwork limit. Enable automatic fit, reduce output size, or reduce frame count. Original artwork is unchanged.")

def render(im,count,amplitude,remaining):
    w,h=im.size
    x0,y0,x1,y1=im.getchannel("A").getbbox()
    y,x=np.mgrid[:h,:w].astype(np.float32)
    v=(y-y0)/max(1,y1-y0);u=(x-(x0+x1-1)/2)/max(1,(x1-x0)/2)
    # Default chibi torso band; zero displacement in upper head and lower feet.
    band=np.sin(np.pi*np.clip((v-.43)/.32,0,1))**2
    band[(v<=.43)|(v>=.75)]=0
    weight=band*np.maximum(0,1-u*u)**2
    a=np.asarray(im,dtype=np.float32)/255
    prem=a.copy();prem[:,:,:3]*=prem[:,:,3:4]
    out=[]
    used=0
    cache={}
    for i in range(count):
        phase_index=min(i,count-i) if amplitude else 0
        if phase_index in cache:
            value=cache[phase_index]
            used+=len(value)
            if used>remaining:return None
            out.append(value)
            continue
        phase=(1-math.cos(2*math.pi*phase_index/count))/2
        if not amplitude or not i:
            frame=im
        else:
            coords=[y+amplitude*phase*weight,x]
            warped=np.stack([map_coordinates(prem[:,:,c],coords,order=1,mode="constant",cval=0) for c in range(4)],axis=2)
            alpha=warped[:,:,3:4]
            rgb=np.divide(warped[:,:,:3],alpha,out=np.zeros_like(warped[:,:,:3]),where=alpha>1e-6)
            rgba=np.rint(np.clip(np.concatenate([rgb,alpha],axis=2),0,1)*255).astype(np.uint8)
            rgba[weight==0]=np.asarray(im)[weight==0]
            frame=Image.fromarray(rgba,"RGBA")
        b=io.BytesIO();frame.save(b,"PNG",compress_level=6)
        value="data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()
        used+=len(value)
        if used>remaining:return None
        cache[phase_index]=value
        out.append(value)
    return out
