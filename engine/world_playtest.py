"""Prepare a bounded immutable playtest snapshot; browser handles real-time movement."""
from PIL import Image
from . import world, world_masks, scenes, modular

STATES=("idle","walk","run","attack","cast")

def prepare(value,clips,options=None):
    d,images=world.validate(value)
    if not isinstance(clips,dict) or "idle" not in clips or any(k not in STATES for k in clips):
        raise ValueError("Assign an idle sprite or animation and optional movement/action clips")
    if options is None:options={}
    if not isinstance(options,dict):raise ValueError("Invalid playtest options")
    allow_stale=world.boolean(options.get("allow_stale",False),"allow stale masks")
    radius=world.integer(options.get("radius",4),0,32,"player footprint radius")
    # Reuse the scene clip validator and shared aggregate source budgets.
    budget=[0,0];clean={}
    for state,c in clips.items():
        clean[state]=scenes.clip(c,budget)[0]
    if not any(l["role"] not in world.MASKS and l["visible"] and l["opacity"] for l in d["layers"]):
        raise ValueError("Add visible environment artwork before playtesting")
    masks,has_walk=world_masks.effective(d)
    status=world_masks.inspect(d)
    if status["stale"] and not allow_stale:raise ValueError("Generated masks are stale; rebuild or explicitly allow stale masks")
    if not clear(masks,has_walk,d["spawn"],radius):raise ValueError("Spawn or player footprint is blocked/outside walkable area; adjust spawn, radius or masks")
    layers=[]
    for i,l in enumerate(d["layers"]):
        if l["role"] in world.MASKS or not l["visible"] or not l["opacity"]:continue
        layers.append(dict(id=l["id"],mode=l["depth"]["mode"],y=world_masks.anchor(l)[1],index=i))
    return dict(width=d["width"],height=d["height"],spawn=d["spawn"],has_walkable=has_walk,
                collision=modular.png_uri(masks["collision"].convert("RGBA")),
                walkable=modular.png_uri(masks["walkable"].convert("RGBA")),
                occlusion=modular.png_uri(masks["occlusion"].convert("RGBA")),
                layers=layers,status=status,radius=radius,clips=clean)

def clear(masks,has_walk,point,radius=0):
    """Same round-footprint occupancy as the browser; out-of-bounds always blocked."""
    x,y=point;w,h=masks["collision"].size
    for dy in range(-radius,radius+1):
        for dx in range(-radius,radius+1):
            if dx*dx+dy*dy>radius*radius:continue
            px,py=x+dx,y+dy
            if not 0<=px<w or not 0<=py<h:return False
            if masks["collision"].getpixel((px,py)) or has_walk and not masks["walkable"].getpixel((px,py)):return False
    return True

def saved_clips(doc):
    """Extract saved standard animation results without loading a GPU model."""
    result={};budget=[0,0]
    pixel=doc.get("settings",{}).get("artstyle","pixel")=="pixel"
    for state in STATES:
        r=doc.get("results",{}).get(state)
        if not r or not r.get("frames"):continue
        frames=r["frames"];raw=r.get("raw") or [];accept=r.get("accept") or []
        chosen=[raw[i] if i<len(accept) and not accept[i] and i<len(raw) else uri for i,uri in enumerate(frames)]
        pivot=r.get("pivot")
        if not isinstance(pivot,(list,tuple)) or len(pivot)!=2:continue
        c=dict(name=state,frames=chosen,fps=r.get("fps",10),pivot=[round(v) for v in pivot],pixel=pixel,loop=state in ("idle","walk","run"))
        result[state]=scenes.clip(c,budget)[0]
    if "idle" not in result:
        uri=doc.get("images",{}).get("charactersprite") or doc.get("images",{}).get("anim")
        if uri:
            im=world.image(uri);box=im.getchannel("A").getbbox()
            if box:result["idle"]=scenes.clip(dict(name="Sprite",frames=[uri],fps=1,loop=True,pixel=pixel,pivot=[(box[0]+box[2])//2,box[3]]),budget)[0]
    if not result:raise ValueError("Saved project has no usable sprite or standard animation clips")
    return result
