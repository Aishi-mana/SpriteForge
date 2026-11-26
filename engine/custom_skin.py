"""Bounded multibone linear blend skinning for the custom skeleton.
Auto weights use at most four nearby bones; manual strokes can add any valid bone.
"""
import numpy as np
from PIL import Image
from . import softmesh

MAX_STAMPS=256

def grid(size,resolution):
    w,h=size
    nx,ny=min(w,resolution),min(h,resolution)
    gy,gx=np.meshgrid(np.linspace(0,h,ny+1),np.linspace(0,w,nx+1),indexing="ij")
    return np.stack((gx,gy),axis=-1)

def build_weights(profile,size,segments):
    settings=profile["skin"]
    uv=grid(size,settings["resolution"])
    ids=[b["id"] for b in profile["bones"]]
    distances=[]
    for k in ids:
        a,b=segments[k];v=b-a
        t=np.clip(((uv-a)@v)/max(float(v@v),1e-9),0,1)
        distances.append(np.linalg.norm(uv-a-t[...,None]*v,axis=-1))
    d=np.stack(distances,axis=-1)
    radius=max(.5,settings["blend"]*max(size))
    # Subtract nearest distance before exponentiation to avoid underflow.
    base=np.exp(-((d-d.min(axis=-1,keepdims=True))/radius)**2)
    if len(ids)>4:
        nearest=np.argsort(d,axis=-1,kind="stable")[...,:4]
        keep=np.zeros_like(base,dtype=bool)
        np.put_along_axis(keep,nearest,True,axis=-1)
        base[~keep]=0
    base/=base.sum(axis=-1,keepdims=True)
    weights=base.copy()
    w,h=size
    for stamp in settings["strokes"]:
        k=ids.index(stamp["bone"])
        if len(ids)==1:continue
        x,y,r,v,opacity=(stamp[n] for n in ("x","y","radius","value","strength"))
        distance=np.hypot(uv[...,0]-x*w,uv[...,1]-y*h)/max(r*max(size),.5)
        strength=np.clip(1-distance,0,1);strength=strength*strength*(3-2*strength)*opacity
        old=weights[...,k].copy()
        target=old+(v-old)*strength
        # Redistribute remaining influence in proportion to existing other weights.
        # If the selected bone had all influence, use the nearest other bone.
        other=weights.copy();other[...,k]=0
        total=other.sum(axis=-1,keepdims=True)
        fallback=base.copy();fallback[...,k]=0
        ftotal=fallback.sum(axis=-1,keepdims=True)
        # Auto weights may have underflowed to zero for other bones.
        mask=ftotal[...,0]<=1e-12
        if mask.any():
            dd=d.copy();dd[...,k]=np.inf
            idx=np.argmin(dd,axis=-1)
            fallback[mask]=np.eye(len(ids))[idx[mask]]
            ftotal=fallback.sum(axis=-1,keepdims=True)
        fallback/=np.maximum(ftotal,1e-12)
        share=np.where(total>1e-12,other/np.maximum(total,1e-12),fallback)
        weights=share*(1-target[...,None]);weights[...,k]=target
    weights/=np.maximum(weights.sum(axis=-1,keepdims=True),1e-12)
    return uv,weights,ids

def deform(image,profile,matrices,segments,padding,binding=None):
    uv,weights,ids=binding if binding is not None else build_weights(profile,image.size,segments)
    dst=np.zeros_like(uv)
    for i,k in enumerate(ids):
        M=matrices[k]
        dst+=(uv@M[:2,:2].T+M[:2,2])*weights[...,i,None]
    dst+=padding
    w,h=image.size
    return softmesh.rasterize(np.asarray(image),uv,dst,(w+2*padding,h+2*padding),not profile["pixel"])

def heatmap(profile,size,segments,bone):
    uv,weights,ids=build_weights(profile,size,segments)
    if bone not in ids:raise ValueError("Unknown weight bone")
    values=weights[...,ids.index(bone)]
    # Grid sample centers approximate the painted mesh; output bounded to source.
    im=Image.fromarray(np.rint(values*255).astype(np.uint8),"L")
    return im.resize(size,Image.Resampling.BILINEAR)
