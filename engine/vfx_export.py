"""VFX clip export adapters. Preserve the authored origin and normalized timing."""
from . import scenes, vfx, vfx_studio, exporter

def standalone_scene_effect(value,effect_id):
    scene,_=scenes.validate(value)
    effect=next((e for e in scene["effects"] if e["id"]==effect_id),None)
    if effect is None:raise ValueError("Choose an effect to export")
    count=effect["end"]-effect["start"]+1
    if count<2:raise ValueError("Standalone export needs at least two active frames")
    actor=next((a for a in scene["actors"] if a["id"]==effect["actor"]),None)
    mirror=effect["world_flip"] or bool(actor and actor["flip"] and effect["face_actor"])
    e={**effect,"actor":None,"face_actor":False,"world_flip":mirror,"start":0,"end":count-1,"visible":True}
    w,h,x,y=vfx.effect_canvas(e)
    e.update(x=x,y=y)
    s={"version":1,"name":e["name"],"width":w,"height":h,"count":count,
       "fps":scene["fps"],"loop":False,"actors":[],"effects":[e]}
    frames,meta=scenes.render(s,preview=False)
    return frames,{**meta,"pivot":[x,y]},effect,mirror

def effect_pack(recipe,options,root):
    r=vfx_studio.validate(recipe)
    frames,meta=vfx_studio.render(r,preview=False)
    payload={"format":"spriteforge-vfx-export","version":1,"type":"effect",
             "recipe":r,"fps":r["fps"],"loop":r["loop"],"pivot":meta["pivot"],
             "frame_count":len(frames),"active_start":r["start"],"active_end":r["end"]}
    return exporter.export_pack([{**meta,"frames":frames}],dict(options,crop=False,uniform=True,smooth=not r["pixel"],vfx_metadata=payload),meta["name"],root)

def scene_effect_pack(value,effect_id,options,root):
    frames,meta,e,mirror=standalone_scene_effect(value,effect_id)
    payload={"format":"spriteforge-vfx-export","version":1,"type":"scene_effect",
             "effect":e,"baked_mirror":mirror,"pivot":meta["pivot"],"fps":meta["fps"],
             "loop":False,"frame_count":len(frames),"source_start":e["start"],"source_end":e["end"],
             "source_arrival":vfx.flight_end(e) if e["kind"] in vfx.PROJECTILE_KINDS else None}
    return exporter.export_pack([{**meta,"frames":frames}],dict(options,crop=False,uniform=True,smooth=not e["pixel"],vfx_metadata=payload),meta["name"],root)

def scene_pack(value,options,root):
    s,_=scenes.validate(value)
    frames,meta=scenes.render(s,preview=False)
    events=[{"id":e["id"],"name":e["name"],"kind":e["kind"],"actor":e["actor"],
             "visible":e["visible"],"start":e["start"],"end":e["end"],
             "arrival":vfx.flight_end(e) if e["kind"] in vfx.PROJECTILE_KINDS else None}
            for e in s["effects"]]
    payload={"format":"spriteforge-vfx-export","version":1,"type":"scene","fps":s["fps"],
             "loop":s["loop"],"pivot":meta["pivot"],"frame_count":len(frames),"effect_cues":events}
    return exporter.export_pack([{**meta,"frames":frames}],dict(options,crop=False,uniform=True,vfx_metadata=payload),meta["name"],root)
