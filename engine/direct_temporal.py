"""Conservative temporal repair of staged edits, gated by original motion."""
import numpy as np
from PIL import Image
from . import full_frame as F, world, modular

def load(body):
    original=F.validate(body.get("original"))
    candidate=F.validate(body.get("candidate"))
    for key in ("width","height","fps","pivot","locked_frames","direction"):
        if original[key]!=candidate[key]:raise ValueError("Candidate must retain source metadata")
    n=len(original["frames"])
    if n!=len(candidate["frames"]) or n<3:raise ValueError("Require matching sequences of at least three frames")
    first=world.integer(body.get("first",0),0,n-1,"first frame")
    last=world.integer(body.get("last",n-1),first,n-1,"last frame")
    for i in original["locked_frames"]:
        if original["frames"][i]!=candidate["frames"][i]:raise ValueError("Locked frame changed")
    return original,candidate,first,last

def options(body):
    q=body.get("options",{})
    if not isinstance(q,dict):raise ValueError("Invalid temporal options")
    return {k:world.integer(q.get(k,v),0,hi,k) for k,v,hi in (("strength",50,100),("motion_gate",12,64),("agreement",16,64),("outlier",24,128),("max_change",32,64),("alpha_strength",0,100))}

def read(uri):
    return np.asarray(world.image(uri),dtype=np.int16)

def repair_triplet(src,edit,q):
    a,b,c=src;x,y,z=edit
    # Only stable opaque source pixels: both adjacent comparisons must agree.
    stable=(a[:,:,3]>=250)&(b[:,:,3]>=250)&(c[:,:,3]>=250)
    stable &= (np.max(np.abs(a[:,:,:3]-b[:,:,:3]),axis=2)<=q["motion_gate"])
    stable &= (np.max(np.abs(c[:,:,:3]-b[:,:,:3]),axis=2)<=q["motion_gate"])
    neighbors=np.max(np.abs(x[:,:,:3]-z[:,:,:3]),axis=2)<=q["agreement"]
    goal=(x[:,:,:3].astype(np.float32)+z[:,:,:3])/2
    delta=goal-y[:,:,:3]
    rgbmask=stable&neighbors&(x[:,:,3]>=250)&(y[:,:,3]>=250)&(z[:,:,3]>=250)&(np.max(np.abs(delta),axis=2)>=q["outlier"])
    out=y.copy()
    adjustment=np.rint(np.clip(delta,-q["max_change"],q["max_change"])*q["strength"]/100).astype(np.int16)
    out[:,:,:3][rgbmask]=np.clip(y[:,:,:3][rgbmask]+adjustment[rgbmask],0,255)
    # Existing partial edge pixels only; no foreground addition or full-alpha erasure.
    alpha=y[:,:,3]
    amask=(alpha>0)&(alpha<255)&(np.abs(a[:,:,3]-b[:,:,3])<=q["motion_gate"])&(np.abs(c[:,:,3]-b[:,:,3])<=q["motion_gate"])&(np.abs(x[:,:,3]-z[:,:,3])<=q["agreement"])
    target=(x[:,:,3].astype(np.float32)+z[:,:,3])/2
    amask &= np.max(np.abs(x[:,:,:3]-z[:,:,:3]),axis=2)<=q["agreement"]
    amask &= np.abs(target-alpha)>=q["outlier"]
    diff=np.rint(np.clip(target-alpha,-q["max_change"],q["max_change"])*q["alpha_strength"]/100).astype(np.int16)
    out[:,:,3][amask]=np.clip(alpha[amask]+diff[amask],1,254)
    return out,dict(stable_pixels=int(stable.sum()),rgb_outliers=int(rgbmask.sum()),alpha_outliers=int(amask.sum()),changed_pixels=int(np.any(out!=y,axis=2).sum()))

def process(body,apply=False):
    original,candidate,first,last=load(body);q=options(body)
    frames=candidate["frames"][:];rows=[];changed=[]
    # No wraparound across loop seams, and no edits at selection boundaries.
    for i in range(first+1,last):
        if i in original["locked_frames"] or original["frames"][i]==candidate["frames"][i]:continue
        src=[read(original["frames"][j]) for j in (i-1,i,i+1)]
        edit=[read(candidate["frames"][j]) for j in (i-1,i,i+1)]
        # Do not pull the original outfit into newly edited frames.
        if any(original["frames"][j]==candidate["frames"][j] for j in (i-1,i,i+1)):continue
        out,row=repair_triplet(src,edit,q);rows.append(dict(frame=i,**row))
        if apply and row["changed_pixels"]:
            frames[i]=modular.png_uri(Image.fromarray(out.astype(np.uint8),"RGBA"));changed.append(i)
    result=dict(rows=rows,changed=changed,first=first,last=last,method="source-gated isolated temporal outliers")
    if apply:
        F.validate({**candidate,"frames":frames})
        result["replacements"]=[dict(frame=i,image=frames[i]) for i in changed]
    return result
