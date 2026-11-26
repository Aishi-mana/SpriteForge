"""Synchronized modular PNG sheets, one sheet per source layer and a shared manifest."""
import json
import math
import re
import tempfile
from pathlib import Path
from PIL import Image
from . import modular, modular_rig, rig

MAX_PIXELS=32_000_000
MAX_AXIS=16384

def export(recipe,anim,count,fps,facing,near,weapon,amp,pad,softness,name,root,columns=8,include_hidden=True,individual=False):
    clean,_=modular.validate(recipe)
    count=modular.integer(count,1,32,"frame count")
    fps=modular.integer(fps,1,60,"FPS")
    columns=min(count,modular.integer(columns,1,32,"columns"))
    pad=modular.integer(pad,0,200,"padding")
    if anim not in rig.CLIPS:raise ValueError("Unknown animation")
    if not isinstance(include_hidden,bool) or not isinstance(individual,bool):raise ValueError("Invalid export flags")
    bodies=[i for i,l in enumerate(clean["layers"]) if l["category"]=="body" and l["visible"] and l["opacity"]]
    if len(bodies)!=1:raise ValueError("Select exactly one visible body layer")
    body_idx=bodies[0]
    indices=[i for i,l in enumerate(clean["layers"]) if i!=body_idx and l["category"]!="body" and l["opacity"] and (l["visible"] or include_hidden)]
    ordered=sorted(indices+[body_idx])
    margin=pad or round(rig.CLIP_PAD.get(anim,.25)*max(clean["width"],clean["height"]))
    w,h=clean["width"]+2*margin,clean["height"]+2*margin
    sw,sh=w*columns,h*math.ceil(count/columns)
    if max(sw,sh)>MAX_AXIS or sw*sh*(len(ordered)+1)>MAX_PIXELS:
        raise ValueError("Layer sheet budget exceeded; reduce frame count, size, columns or exported layers")
    sheets={i:Image.new("RGBA",(sw,sh)) for i in ordered}
    lookup={-1:body_idx,**dict(enumerate(indices))}
    seen=set()
    regions=[{"index":i,"x":i%columns*w,"y":i//columns*h,"w":w,"h":h} for i in range(count)]
    def sink(index,fi,im):
        i=lookup[index]
        if im.size!=(w,h) or not 0<=fi<count or (i,fi) in seen:raise ValueError("Unexpected layer frame")
        seen.add((i,fi))
        rect=regions[fi]
        sheets[i].paste(im,(rect["x"],rect["y"]))
    _,meta=modular_rig.render(clean,anim,count,facing,near,weapon,amp,pad,softness=softness,
                                layer_sink=sink,include_hidden=include_hidden)
    if len(seen)!=len(ordered)*count or tuple(meta["size"])!=(w,h):raise ValueError("Incomplete synchronized layer frames")
    assembled=Image.new("RGBA",(sw,sh))
    layers=[]
    for z,i in enumerate(ordered):
        l=clean["layers"][i]
        if l["visible"]:assembled=Image.alpha_composite(assembled,sheets[i])
        layers.append({"id":f"layer_{i:02d}","source_index":i,"name":l["name"],"category":l["category"],
                       "z":z,"visible":l["visible"],"attachment":l["attachment"],"motion":l["motion"],
                       "sheet":f"layers/layer_{i:02d}.png"})
    pivot=list(meta["pivot"])
    manifest={"version":1,"format":"spriteforge_modular_animation","animation":anim,"frame_count":count,"fps":fps,
              "loop":anim not in rig.ONE_SHOT,"cell":{"w":w,"h":h},"sheet":{"w":sw,"h":sh,"columns":columns},
              "pivot_px":pivot,"pivot_normalized":[pivot[0]/w,pivot[1]/h],"origin":"top-left",
              "sampling":"nearest" if clean["pixel"] else "linear","alpha":"straight",
              "facing":facing,"near":near,"weapon":weapon,"amplitude":amp,"padding":margin,"body_softness":softness,
              "frames":regions,"layers":layers,"assembled_sheet":"assembled.png","individual_frames":individual,
              "body_layer":f"layer_{body_idx:02d}"}
    # Unique export directory avoids stale layers from previous exports.
    safe=re.sub(r"[^A-Za-z0-9_-]+","_",str(name))[:60].strip("_") or "character"
    parent=Path(root)/"exports";parent.mkdir(parents=True,exist_ok=True)
    d=Path(tempfile.mkdtemp(prefix=f"{safe}_{anim}_layers_",dir=parent))
    try:
        (d/"layers").mkdir()
        assembled.save(d/"assembled.png")
        for l,i in zip(layers,ordered):
            sheets[i].save(d/l["sheet"])
            if individual:
                folder=d/"frames"/l["id"];folder.mkdir(parents=True)
                l["frames_dir"]=f"frames/{l['id']}"
                for rect in regions:
                    x,y=rect["x"],rect["y"]
                    sheets[i].crop((x,y,x+w,y+h)).save(folder/f"{rect['index']:03d}.png")
        (d/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf-8")
        (d/"README.txt").write_text("Use the same frame index for every visible layer. Draw ascending z, at the same origin minus pivot_px. Use straight-alpha blending. Toggle alternatives by layer id/category. All cells are untrimmed; transparent cells still consume a frame. assembled.png uses default visibility. Use nearest filtering for pixel art. Export all desired clips with matching recipe/order and settings. This is baked 2D animation, not a runtime skeleton.\n",encoding="utf-8")
    except Exception:
        import shutil
        shutil.rmtree(d,ignore_errors=True)
        raise
    return {"dir":str(d),"frames":count,"layers":len(layers),"sheet":[sw,sh],"cell":[w,h],"pivot":pivot}
