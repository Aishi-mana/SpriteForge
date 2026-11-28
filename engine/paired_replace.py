"""Replace only a chosen paired actor's raster sequence."""
from . import scenes, full_frame as F

def prepare(body):
    scene,decoded=scenes.validate(body.get("scene"))
    key=body.get("actor")
    if key not in ("actor_A","actor_B") or {a["id"] for a in scene["actors"]}!={"actor_A","actor_B"}:
        raise ValueError("Choose one actor in a two-character pair")
    a=next(a for a in scene["actors"] if a["id"]==key)
    c=a["clip"];w,h=decoded[key][0].size
    # Full-frame documents require a pivot inside the canvas, unlike scene clips.
    doc=F.validate(dict(version=1,name=c["name"],width=w,height=h,pivot=[min(w-1,c["pivot"][0]),min(h-1,c["pivot"][1])],fps=c["fps"],loop=c["loop"],pixel=c["pixel"],frames=c["frames"]))
    return doc

def replace(body):
    scene,decoded=scenes.validate(body.get("scene"))
    key=body.get("actor")
    if key not in ("actor_A","actor_B") or {a["id"] for a in scene["actors"]}!={"actor_A","actor_B"}:
        raise ValueError("Choose one actor in a two-character pair")
    a=next(a for a in scene["actors"] if a["id"]==key)
    frames=body.get("frames")
    if not isinstance(frames,list) or len(frames)!=len(a["clip"]["frames"]):
        raise ValueError("Replacement must have original source frame count")
    clip,images=scenes.clip({**a["clip"],"frames":frames})
    if images[0].size!=decoded[key][0].size:raise ValueError("Replacement must have original canvas dimensions")
    if any(not im.getchannel("A").getbbox() for im in images):raise ValueError("Replacement contains an empty frame")
    a["clip"]=clip
    return scenes.validate(scene)[0]
