"""Conservative temporal diagnostics and optional full-frame cleanup."""
import base64, io
import numpy as np
from PIL import Image
from . import full_frame as F, world, full_frame_guidance as G

def settings(q):
    if not isinstance(q,dict):raise ValueError("Invalid consistency options")
    n=world.integer
    bg=q.get("background","none")
    if bg not in ("none","green","magenta","blue"):raise ValueError("Invalid spill color")
    return dict(color=n(q.get("color",0),0,100,"color strength"),position=n(q.get("position",0),0,100,"position strength"),
        edge=n(q.get("edge",0),0,100,"edge strength"),spill=n(q.get("spill",0),0,100,"spill strength"),background=bg,
        max_shift=n(q.get("max_shift",4),0,16,"maximum shift"))

def stats(a):
    mask=a[:,:,3]>=128
    ys,xs=np.where(mask)
    if not len(xs):return None
    return np.array([(xs.min()+xs.max())/2,ys.max(),xs.max()-xs.min()+1,ys.max()-ys.min()+1,*np.median(a[:,:,:3][mask],axis=0)],dtype=float)

def inspect(doc):
    d=F.validate(doc)
    arrays=[np.array(world.image(s)) for s in d["frames"]]
    metrics=[stats(a) for a in arrays]
    rows=[]
    for i,s in enumerate(metrics):
        neighbors=[v for v in metrics[max(0,i-1):i+2] if v is not None]
        if s is None:
            rows.append(dict(frame=i+1,empty=True,position=0,scale=0,color=0,flag=True));continue
        target=np.median(neighbors,axis=0)
        pos=float(np.linalg.norm(s[:2]-target[:2]))
        scale=float(np.max(np.abs(s[2:4]-target[2:4])/np.maximum(target[2:4],1)))
        color=float(np.max(np.abs(s[4:]-target[4:])))
        rows.append(dict(frame=i+1,empty=False,position=round(pos,2),scale=round(scale,3),color=round(color,2),flag=pos>4 or scale>.15 or color>18))
    return rows

def shift(a,dx,dy):
    h,w=a.shape[:2];out=np.zeros_like(a)
    x0=max(0,-dx);x1=min(w,w-dx);y0=max(0,-dy);y1=min(h,h-dy)
    if x1>x0 and y1>y0:out[y0+dy:y1+dy,x0+dx:x1+dx]=a[y0:y1,x0:x1]
    return out

def correct(doc,options):
    d=F.validate(doc);q=settings(options)
    arrays=[np.array(world.image(s)) for s in d["frames"]]
    metrics=[stats(a) for a in arrays]
    out=[]
    for i,a in enumerate(arrays):
        if metrics[i] is None:
            out.append(d["frames"][i]);continue
        s=metrics[i];neighbors=[v for v in metrics[max(0,i-1):i+2] if v is not None];target=np.median(neighbors,axis=0)
        b=a.copy()
        if q["color"]:
            delta=np.clip(target[4:]-s[4:],-24,24)*q["color"]/100
            mask=b[:,:,3]>0;b[:,:,:3][mask]=np.clip(b[:,:,:3][mask].astype(float)+delta,0,255).astype(np.uint8)
        if q["edge"] and 0<i<len(arrays)-1:
            alpha=b[:,:,3];prev=arrays[i-1][:,:,3];nxt=arrays[i+1][:,:,3]
            # Only soften partially transparent existing edge pixels when neighbors agree.
            mask=(alpha>0)&(alpha<255)&(np.abs(prev.astype(float)-nxt.astype(float))<=32)
            goal=np.median(np.stack([prev,alpha,nxt]),axis=0)
            alpha[mask]=np.rint(alpha[mask]+(goal[mask]-alpha[mask])*q["edge"]/100).astype(np.uint8)
        if q["spill"] and q["background"]!="none":
            rgb=b[:,:,:3].astype(float);alpha=b[:,:,3];mask=(alpha>0)&(alpha<255)
            channels={"green":[1],"blue":[2],"magenta":[0,2]}[q["background"]]
            other=[c for c in range(3) if c not in channels]
            limit=np.max(rgb[:,:,other],axis=2)
            for c in channels:rgb[:,:,c][mask]-=np.maximum(0,rgb[:,:,c][mask]-limit[mask])*q["spill"]/100
            b[:,:,:3]=np.rint(rgb).astype(np.uint8)
        if q["position"]:
            dx,dy=np.rint(np.clip((target[:2]-s[:2])*q["position"]/100,-q["max_shift"],q["max_shift"])).astype(int)
            # Never shift a visible pixel off the canvas.
            ys,xs=np.where(b[:,:,3]>0);h,w=b.shape[:2]
            if len(xs) and xs.min()+dx>=0 and xs.max()+dx<w and ys.min()+dy>=0 and ys.max()+dy<h:b=shift(b,dx,dy)
        if np.array_equal(a,b):out.append(d["frames"][i]);continue
        buf=io.BytesIO();Image.fromarray(b,"RGBA").save(buf,"PNG")
        out.append("data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode())
    return F.validate({**d,"frames":out})
