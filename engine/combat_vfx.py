"""Bake combat cues into ordinary editable scene effects; no simulation state."""
from . import scenes, vfx, modular

MODES=("follow","launch","target","projectile_target")

def cue(value,request):
    scene,_=scenes.validate(value)
    if not isinstance(request,dict):raise ValueError("Invalid combat cue")
    by={a["id"]:a for a in scene["actors"]}
    source=by.get(request.get("source")) if isinstance(request.get("source"),str) else None
    if source is None:raise ValueError("Choose a source actor")
    selected=next((e for e in scene["effects"] if e["id"]==request.get("effect")),None)
    if selected is None:raise ValueError("Choose an effect")
    mode=request.get("mode","follow")
    if mode not in MODES:raise ValueError("Invalid combat attachment")
    n=modular.integer
    clip_frame=n(request.get("clip_frame",0),0,len(source["clip"]["frames"])-1,"attack clip frame")
    earliest=n(request.get("earliest",0),0,scene["count"]-1,"earliest scene frame")
    delay=n(request.get("delay",0),0,63,"cue delay")
    trigger=next((i for i in range(earliest,scene["count"]) if source["opacity"] and
                  scenes.frame_index(source,i,scene["fps"])==clip_frame),None)
    if trigger is None:raise ValueError("Source clip frame is not visible/reachable in the scene")
    start=trigger+delay
    duration=selected["end"]-selected["start"]+1
    end=start+duration-1
    if end>=scene["count"]:raise ValueError("Extend scene duration to fit this combat cue")
    if scenes.frame_index(source,start,scene["fps"]) is None:raise ValueError("Source actor is not visible at cue start")
    x=n(request.get("x",0),-512,512,"anchor X")
    y=n(request.get("y",0),-512,512,"anchor Y")
    tx=n(request.get("target_x",0),-512,512,"target X")
    ty=n(request.get("target_y",0),-512,512,"target Y")
    def anchor(actor,frame,dx,dy):
        if not actor["opacity"] or scenes.frame_index(actor,frame,scene["fps"]) is None:
            raise ValueError("Combat anchor actor is not visible at event frame")
        ax,ay=scenes.position(actor,frame)
        return ax+round(dx*actor["scale"]/100)*(-1 if actor["flip"] else 1),ay+round(dy*actor["scale"]/100)
    e={**selected,"start":start,"end":end,"actor":None,"face_actor":False,"world_flip":False}
    if mode=="follow":
        # Actor-facing offsets are stored in world pixels; compositor mirrors the full local effect.
        e.update(actor=source["id"],face_actor=True,x=round(x*source["scale"]/100),y=round(y*source["scale"]/100))
    elif mode=="target":
        target=by.get(request.get("target")) if isinstance(request.get("target"),str) else None
        if target is None:raise ValueError("Choose a target actor")
        e.update(x=anchor(target,start,tx,ty)[0],y=anchor(target,start,tx,ty)[1])
    else:
        e["x"],e["y"]=anchor(source,start,x,y)
        if mode=="projectile_target":
            if e["kind"] not in vfx.PROJECTILE_KINDS:raise ValueError("Targeted flight needs a projectile effect")
            if vfx.flight_end(e)<=start:raise ValueError("Targeted flight needs at least two flight frames")
            target=by.get(request.get("target")) if isinstance(request.get("target"),str) else None
            if target is None:raise ValueError("Choose a target actor")
            arrive=vfx.flight_end(e)
            ax,ay=anchor(target,arrive,tx,ty)
            k=vfx.keyframe(e,arrive)
            e.update(travel_x=ax-e["x"]-k["dx"],travel_y=ay-e["y"]-k["dy"])
        else:
            e["world_flip"]=source["flip"]
    scene["effects"]=[e if x["id"]==e["id"] else x for x in scene["effects"]]
    return {"scene":scenes.validate(scene)[0],"trigger":trigger,"start":start,"end":end,
            "arrival":vfx.flight_end(e) if e["kind"] in vfx.PROJECTILE_KINDS else None}

def behavior_clip(value,effect_id):
    """Render an actor-local effect, preserving the actual origin of its path canvas."""
    scene,_=scenes.validate(value)
    e=next((e for e in scene["effects"] if e["id"]==effect_id),None)
    if e is None:raise ValueError("Choose a scene effect")
    count=e["end"]-e["start"]+1
    if count<2:raise ValueError("Behavior preview needs at least two effect frames")
    e={**e,"world_flip":False}
    w,h,x,y=vfx.effect_canvas(e)
    recipe={"version":1,"name":e["name"],"width":w,"height":h,"count":count,"fps":scene["fps"],"loop":False,"actors":[],
            "effects":[{**e,"actor":None,"face_actor":False,"start":0,"end":count-1,"x":x,"y":y,"visible":True}]}
    frames,meta=scenes.render(recipe)
    return frames,{**meta,"pivot":[x,y],"pixel":e["pixel"]}
