"""Frame-indexed custom skeleton rotation tracks and bounded clip rendering."""
import math
from . import modular

MAX_KEYS=512
CURVES=("linear","ease","step")

def validate(clip,ids):
    if not isinstance(clip,dict):raise ValueError("Invalid custom timeline")
    name=clip.get("name","custom")
    if not isinstance(name,str) or not name.strip() or len(name)>60:raise ValueError("Invalid clip name")
    count=modular.integer(clip.get("count",8),2,32,"clip frame count")
    fps=modular.integer(clip.get("fps",10),1,60,"clip FPS")
    loop=clip.get("loop",True)
    if not isinstance(loop,bool):raise ValueError("Invalid loop setting")
    tracks=clip.get("tracks",{})
    if not isinstance(tracks,dict) or any(k not in ids for k in tracks):raise ValueError("Timeline track references missing bone")
    clean={};total=0
    for bone,keys in tracks.items():
        if not isinstance(keys,list) or len(keys)>count:raise ValueError("Invalid keyframe list")
        seen=set();rows=[]
        for k in keys:
            if not isinstance(k,dict):raise ValueError("Invalid keyframe")
            frame=modular.integer(k.get("frame"),0,count-1,"keyframe index")
            angle=k.get("angle")
            curve=k.get("curve","linear")
            if frame in seen:raise ValueError("Duplicate keyframe")
            if isinstance(angle,bool) or not isinstance(angle,(float,int)) or not math.isfinite(angle) or not -180<=angle<=180:
                raise ValueError("Invalid keyframe rotation")
            if curve not in CURVES:raise ValueError("Invalid keyframe interpolation")
            seen.add(frame);rows.append(dict(frame=frame,angle=float(angle),curve=curve))
        total+=len(rows)
        if rows:clean[bone]=sorted(rows,key=lambda k:k["frame"])
    if total>MAX_KEYS:raise ValueError("Timeline exceeds 512 keyframes")
    return dict(name=name.strip(),count=count,fps=fps,loop=loop,tracks=clean)

def sample(keys,frame,default):
    """Hold outside the keyed interval. Outgoing curve belongs to the left key."""
    if not keys:return default
    if frame<=keys[0]["frame"]:return keys[0]["angle"]
    if frame>=keys[-1]["frame"]:return keys[-1]["angle"]
    for a,b in zip(keys,keys[1:]):
        if frame==b["frame"]:return b["angle"]
        if a["frame"]<=frame<b["frame"]:
            t=(frame-a["frame"])/(b["frame"]-a["frame"])
            if a["curve"]=="step":t=0
            elif a["curve"]=="ease":t=t*t*(3-2*t)
            return a["angle"]+(b["angle"]-a["angle"])*t
    return default

def pose(profile,frame):
    clip=profile["timeline"]
    return {**profile,"bones":[{**b,"angle":sample(clip["tracks"].get(b["id"],[]),frame,b["angle"])} for b in profile["bones"]]}

def render(image,profile,padding=32,preview=True,frame=None):
    from . import custom_skeleton as cs,custom_skin
    profile=cs.validate(profile)
    if "timeline" not in profile:raise ValueError("Create a custom animation timeline first")
    clip=profile["timeline"]
    if not clip["tracks"]:raise ValueError("Add at least one bone keyframe")
    im=modular.decode(image)
    pad=modular.integer(padding,0,256,"padding")
    indices=list(range(clip["count"])) if frame is None else [modular.integer(frame,0,clip["count"]-1,"preview frame")]
    w,h=im.size;pixels=(w+2*pad)*(h+2*pad)
    if pixels*len(indices)>(12_000_000 if preview else 32_000_000):
        raise ValueError("Clip exceeds frame budget; reduce source size, padding or frame count")
    weighted=profile.get("skin",{}).get("mode")=="weighted"
    if pixels*len(profile["bones"])>48_000_000 or (not weighted and pixels*len(profile["bones"])*len(indices)>240_000_000):
        raise ValueError("Clip exceeds CPU work budget; reduce size, bone count or frames")
    binding=None
    if weighted:
        _,segments=cs.transforms(profile,im.size)
        binding=custom_skin.build_weights(profile,im.size,segments)
    frames=[]
    for i in indices:
        rendered,_=cs.render(im,pose(profile,i),pad,binding=binding)
        frames.append(rendered)
    # Fixed rest root-head pivot, independent of each frame's pose.
    pivot=(round(profile["root_head"][0]*w)+pad,round(profile["root_head"][1]*h)+pad)
    return frames,{"name":clip["name"],"fps":clip["fps"],"loop":clip["loop"],"size":list(frames[0].size),"pivot":list(pivot),"indices":indices}
