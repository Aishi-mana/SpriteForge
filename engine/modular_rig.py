"""Independent modular layer animation using the base skeleton's world matrices."""
import hashlib
import math
import re
import numpy as np
from PIL import Image
from . import modular, rig

def validate_profile(profile):
    if not isinstance(profile,dict):raise ValueError("Invalid modular rig profile")
    key=profile.get("body_key","")
    if not isinstance(key,str) or not re.fullmatch("[0-9a-f]{64}",key):raise ValueError("Invalid body rig key")
    j=profile.get("joints")
    if not isinstance(j,dict) or set(j)!=set(rig.JOINTS):raise ValueError("Missing modular rig joints")
    out={}
    for name,p in j.items():
        if not isinstance(p,(tuple,list)) or len(p)!=2 or any(isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or not 0<=v<=1024 for v in p):
            raise ValueError("Invalid modular rig joint")
        out[name]=[float(v) for v in p]
    return {"body_key":key,"joints":out}

def prepare(recipe):
    clean,images=modular.validate(recipe)
    visible=[i for i,l in enumerate(clean["layers"]) if l["visible"] and l["opacity"]]
    bodies=[i for i in visible if clean["layers"][i]["category"]=="body"]
    if len(bodies)!=1:raise ValueError("Select exactly one visible body layer")
    idx=bodies[0]
    def single(i):
        return modular.composite({**clean,"layers":[clean["layers"][i]]},[images[i]])
    body=single(idx)
    if not body.getchannel("A").point(lambda v:255 if v>=128 else 0).getbbox():
        raise ValueError("Body has no opaque pixels for rigging")
    key=hashlib.sha256(f"{body.width}x{body.height}:".encode()+body.tobytes()).hexdigest()
    profile=clean.get("rig")
    valid=profile is not None and profile["body_key"]==key
    joints=profile["joints"] if valid else rig.autoplace(body)
    for xy in joints.values():
        if xy[0]>body.width or xy[1]>body.height:raise ValueError("Joint outside body canvas")
    attachments=[(single(i),clean["layers"][i]["attachment"],i<idx) for i in visible if i!=idx]
    return clean,body,key,joints,valid,attachments

def describe(recipe):
    clean,body,key,joints,valid,attachments=prepare(recipe)
    return {"body":modular.png_uri(body),"body_key":key,"joints":joints,"saved_rig":valid,"bones":list(modular.ATTACHMENTS)}

def render(recipe,anim,count=8,facing="right",near="r",weapon="r",amp=1.,pad=0,overlap=1,softness=0):
    clean,body,key,joints,valid,attachments=prepare(recipe)
    if anim not in rig.CLIPS:raise ValueError("Select a standard rig animation")
    if facing not in ("left","right") or near not in ("l","r","both") or weapon not in ("l","r"):raise ValueError("Invalid rig orientation")
    count=modular.integer(count,1,32,"frame count")
    pad=modular.integer(pad,0,200,"padding")
    if not math.isfinite(amp) or not .3<=amp<=2:raise ValueError("Invalid motion amplitude")
    # Explicit lower memory ceiling for independently retained surfaces.
    margin=pad or round(rig.CLIP_PAD.get(anim,.25)*max(body.size))
    pixels=(body.width+2*margin)*(body.height+2*margin)
    if pixels*count>32_000_000:raise ValueError("Modular clip exceeds frame memory budget; lower size, frames or padding")
    # Each auto-partitioned layer may allocate up to ten surfaces; cap aggregate supersampled work.
    parts=sum(len(rig.BONES) if bone=="auto" else 1 for _,bone,_ in attachments)
    ss=1 if rig.is_hd(body) else 2
    if pixels*ss*ss*(parts+len(rig.BONES))>32_000_000:raise ValueError("Too many visible bone layers for this canvas; hide alternatives or reduce size")
    return rig.render(body,joints,[],anim,count,facing,near,weapon,amp,pad,overlap,ss,
                      softness=softness,attachments=attachments,force_hd=not clean["pixel"])
