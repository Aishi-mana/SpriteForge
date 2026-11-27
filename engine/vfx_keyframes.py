"""Relative-frame VFX tracks with bounded, deterministic interpolation."""
import re
from . import modular

LIMIT=32
EASING=("linear","smooth","hold")
FIELDS={"dx":(-512,512,0),"dy":(-512,512,0),"scale":(25,200,100),
        "rotation":(-360,360,0),"opacity":(0,100,100)}
DEFAULT={"dx":0,"dy":0,"scale":100,"rotation":0,"opacity":100,"color":"#ffffff"}

def validate(keys,duration):
    if not isinstance(keys,list) or len(keys)>LIMIT:raise ValueError("At most 32 VFX keyframes")
    out=[];seen=set()
    for k in keys:
        if not isinstance(k,dict):raise ValueError("Invalid VFX keyframe")
        frame=modular.integer(k.get("frame"),0,duration-1,"relative keyframe")
        if frame in seen:raise ValueError("Duplicate VFX keyframe")
        seen.add(frame)
        easing=k.get("easing","linear")
        color=k.get("color","#ffffff")
        if easing not in EASING:raise ValueError("Invalid keyframe interpolation")
        if not isinstance(color,str) or not re.fullmatch(r"#[0-9a-fA-F]{6}",color):raise ValueError("Invalid keyframe tint")
        out.append(dict(frame=frame,easing=easing,color=color.lower(),
                        **{n:modular.integer(k.get(n,d),lo,hi,"keyframe "+n) for n,(lo,hi,d) in FIELDS.items()}))
    return sorted(out,key=lambda k:k["frame"])

def sample(keys,frame):
    if not keys:return DEFAULT.copy()
    if frame<=keys[0]["frame"]:return {n:keys[0][n] for n in DEFAULT}
    if frame>=keys[-1]["frame"]:return {n:keys[-1][n] for n in DEFAULT}
    for a,b in zip(keys,keys[1:]):
        if a["frame"]<=frame<b["frame"]:
            t=(frame-a["frame"])/(b["frame"]-a["frame"])
            if a["easing"]=="hold":t=0
            elif a["easing"]=="smooth":t=t*t*(3-2*t)
            mix=lambda x,y:round(x+(y-x)*t)
            return {**{n:mix(a[n],b[n]) for n in FIELDS},
                    "color":"#"+"".join(f"{mix(int(a['color'][i:i+2],16),int(b['color'][i:i+2],16)):02x}" for i in (1,3,5))}
    raise ValueError("Invalid keyframe order")

def tint(color,multiplier):
    return "#"+"".join(f"{round(int(color[i:i+2],16)*int(multiplier[i:i+2],16)/255):02x}" for i in (1,3,5))
