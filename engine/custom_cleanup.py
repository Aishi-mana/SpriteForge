"""Selective, non-destructive cleanup of baked custom timeline frames.
Only the selected mask can change. Accepted images are separate from the rig.
"""
import base64
import io
import re
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from . import modular, refine, styles

MAX_ENCODED=24_000_000
MAX_STAMPS=128

def settings(value):
    if not isinstance(value,dict):raise ValueError("Invalid cleanup settings")
    mode=value.get("mode","joints")
    if mode not in ("joints","brush","both"):raise ValueError("Unknown cleanup mask mode")
    radius=modular.integer(value.get("radius",5),1,25,"mask radius")
    strokes=value.get("strokes",[])
    if not isinstance(strokes,list) or len(strokes)>MAX_STAMPS:raise ValueError("At most 128 mask stamps")
    clean=[]
    from .custom_skeleton import number
    for s in strokes:
        if not isinstance(s,list) or len(s)!=3:raise ValueError("Invalid mask stamp")
        clean.append([number(s[0],0,1,"mask x"),number(s[1],0,1,"mask y"),number(s[2],.01,.25,"mask radius")])
    alpha=value.get("alpha_lock",True);palette=value.get("palette_lock",True)
    if not isinstance(alpha,bool) or not isinstance(palette,bool):raise ValueError("Invalid cleanup lock")
    return dict(mode=mode,radius=radius,strokes=clean,alpha_lock=alpha,palette_lock=palette)

def mask_for(frame,points,opts):
    w,h=frame.size;alpha=np.asarray(frame)[...,3]>0
    Y,X=np.ogrid[:h,:w];mask=np.zeros((h,w),bool)
    def disc(x,y,r):return (X+.5-x)**2+(Y+.5-y)**2<=r*r
    if opts["mode"] in ("joints","both"):
        auto=np.zeros_like(mask);r=max(1,opts["radius"]*max(w,h)/100)
        for a,b in points.values():auto|=disc(*a,r);auto|=disc(*b,r)
        mask|=auto & ndi.binary_dilation(alpha,iterations=max(1,round(r/3)))
    if opts["mode"] in ("brush","both"):
        for x,y,r in opts["strokes"]:mask|=disc(x*w,y*h,r*max(w,h))
    if opts["alpha_lock"]:mask&=alpha
    if not mask.any():raise ValueError("Mask is empty; paint on the sprite or adjust joint radius")
    if mask.mean()>.55:raise ValueError("Mask covers more than 55% of frame; reduce brush or joint radius")
    return mask

def prepare(body):
    from . import custom_timeline
    frames,meta=custom_timeline.render(body.get("image"),body.get("profile"),body.get("padding",32),
                                       frame=body.get("frame"),include_bones=True)
    if len(frames)!=1:raise ValueError("Cleanup requires one frame index")
    stamp=body.get("fingerprint")
    if stamp is not None and stamp!=meta["fingerprint"]:raise ValueError("Timeline changed; render again")
    opts=settings(body.get("mask",{}))
    frame=frames[0];mask=mask_for(frame,meta["joints"][0],opts)
    return frame,mask,opts,meta

def cleanup(frame,mask,opts,inpaint_fn,ckpt,lora,lora_w,lora_dir,prompt,negative,strength,steps,cfg,seed,size,pixel,art_style):
    """Letterbox to an SDXL canvas, then restore only masked pixels.
    Alpha is exact by default; optional chroma-key silhouette repair is guarded.
    """
    w,h=frame.size;arr=np.asarray(frame).copy();visible=arr[...,3]>0
    samples=arr[visible][:,:3][::max(1,int(visible.sum())//4096)].astype(np.int32)
    if not len(samples):raise ValueError("Cannot clean a transparent frame")
    bgname=max(refine.CANDIDATE_BG,key=lambda n:np.min(((samples-np.array(refine.CANDIDATE_BG[n]))**2).sum(-1)))
    bg=refine.CANDIDATE_BG[bgname]
    scale=size/max(w,h);rw,rh=max(1,round(w*scale)),max(1,round(h*scale))
    ox,oy=(size-rw)//2,(size-rh)//2
    sampling=Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS
    big=frame.resize((rw,rh),sampling)
    img=Image.new("RGB",(size,size),bg);img.paste(big.convert("RGB"),(ox,oy),big.getchannel("A"))
    mk=Image.new("L",(size,size));mk.paste(Image.fromarray(mask.astype(np.uint8)*255,"L").resize((rw,rh),Image.Resampling.NEAREST),(ox,oy))
    if not mk.getbbox():raise ValueError("Mask vanished at inference resolution; increase size or brush radius")
    rendered=inpaint_fn(ckpt,lora,lora_w,lora_dir,prompt,negative,img,mk,strength,steps,cfg,seed,bg,art_style=art_style)
    if rendered.size!=(size,size):raise ValueError("Inpaint returned unexpected dimensions")
    rgb=np.asarray(rendered.convert("RGB").crop((ox,oy,ox+rw,oy+rh)).resize((w,h),sampling)).copy()
    info={"seed":seed,"masked_pixels":int(mask.sum()),"alpha_locked":opts["alpha_lock"],"palette_applied":False,"rejected":False}
    if opts["palette_lock"] and pixel:
        # Exact palette lock only for genuinely limited-color source frames.
        cols=np.unique(arr[visible][:,:3],axis=0)
        if 0<len(cols)<=96:
            rgb[mask]=cols[refine._nearest_palette(rgb[mask].reshape(-1,1,3),cols,chunk=4096).reshape(-1)]
            info["palette_applied"]=True
        else:info["warning"]="Source exceeds 96 colors; exact palette lock skipped"
    if opts["alpha_lock"]:
        arr[mask,:3]=rgb[mask]
    else:
        # Use the unquantized RGB for chroma keying, not the snapped palette.
        raw=np.asarray(rendered.convert("RGB").crop((ox,oy,ox+rw,oy+rh)).resize((w,h),sampling))
        new_alpha=np.where(np.max(np.abs(raw.astype(np.int16)-np.array(bg)),axis=-1)>55,255,0).astype(np.uint8)
        before=int((visible&mask).sum());after=int(((new_alpha>0)&mask).sum())
        if after<.6*before or after>1.4*before+12:
            info.update(rejected=True,warning="Silhouette change exceeds guard; original retained")
            return frame.copy(),info
        arr[mask,:3]=rgb[mask];arr[mask,3]=new_alpha[mask]
        arr[mask&(arr[...,3]==0),:3]=0
    return Image.fromarray(arr,"RGBA"),info

def decode_frame(uri):
    if not isinstance(uri,str) or not uri.startswith("data:image/png;base64,") or len(uri)>13_000_000:
        raise ValueError("Invalid accepted cleanup PNG")
    try:
        raw=base64.b64decode(uri.split(",",1)[1],validate=True)
        with Image.open(io.BytesIO(raw)) as im:
            if im.format!="PNG" or min(im.size)<1 or max(im.size)>1536:raise ValueError("Invalid cleanup frame dimensions")
            return im.convert("RGBA")
    except (OSError,ValueError) as e:raise ValueError("Cannot read accepted cleanup frame") from e

def validate_saved(value):
    if value is None:return None
    if not isinstance(value,dict) or not isinstance(value.get("fingerprint"),str) or not re.fullmatch(r"[0-9a-f]{64}",value["fingerprint"]):
        raise ValueError("Invalid cleanup fingerprint")
    frames=value.get("frames")
    if not isinstance(frames,dict) or len(frames)>32:raise ValueError("Invalid accepted cleanup frames")
    total=0;clean={}
    for k,v in frames.items():
        if not isinstance(k,str) or not re.fullmatch(r"(0|[1-9][0-9]?)",k) or int(k)>31 or not isinstance(v,str):
            raise ValueError("Invalid cleanup frame index")
        total+=len(v)
        if total>MAX_ENCODED:raise ValueError("Accepted cleanup images exceed 24 MB")
        decode_frame(v)
        clean[k]=v
    return {"fingerprint":value["fingerprint"],"frames":clean} if clean else None

def apply(frames,meta,value):
    saved=validate_saved(value)
    if not saved:return frames
    if saved["fingerprint"]!=meta["fingerprint"]:raise ValueError("Accepted cleanup belongs to a different timeline; export originals or render matching rig")
    out=list(frames)
    for k,v in saved["frames"].items():
        idx=int(k)
        if idx>=len(out):raise ValueError("Accepted cleanup frame outside clip")
        im=decode_frame(v)
        if im.size!=out[idx].size:raise ValueError("Accepted cleanup canvas mismatch")
        out[idx]=im
    return out
