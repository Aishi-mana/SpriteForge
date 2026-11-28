"""Full-frame animation interchange, bounded atlas pages and world clips."""
import io, json, zipfile
from PIL import Image
from . import full_frame as F, world

def clips(doc):
    d=F.validate(doc)
    return {key:{**{k:d[k] for k in ("name","fps","pivot","pixel","loop")}, "frames":v["frames"],"combat":v.get("combat",[])}
            for key,v in {**d["directions"],d["direction"]:d}.items() if v["frames"]}

def world_clip(doc,budget):
    from . import scenes
    if not isinstance(doc,dict) or not isinstance(doc.get("directions"),dict):raise ValueError("Invalid full-frame playtest clip")
    directions=doc["directions"]
    from .full_frame_directions import DIRECTIONS
    if not directions or any(k not in DIRECTIONS for k in directions):raise ValueError("Invalid playtest directions")
    from . import full_frame_combat as C
    out={}
    for key,v in directions.items():
        if not isinstance(v,dict):raise ValueError("Invalid direction clip")
        frames=v.get("frames")
        if not isinstance(frames,list) or not 1<=len(frames)<=F.MAX_FRAMES:raise ValueError("Invalid playtest frame count")
        # Validate in bounded scene-sized batches, sharing the aggregate budget.
        clean=None;images=[]
        for start in range(0,len(frames),32):
            part,ims=scenes.clip({**v,"frames":frames[start:start+32]},budget)
            if clean is None:clean=part
            images.extend(ims)
        if any(im.size!=images[0].size for im in images):raise ValueError("Inconsistent clip canvas")
        clean["frames"]=frames
        clean["combat"]=C.validate(v.get("combat"),len(frames),*images[0].size)
        out[key]=clean
    active=doc.get("active")
    if active not in out:active=next(iter(out))
    return {**out[active],"directions":out,"active":active}

def export(doc,kind="atlas"):
    d=F.validate(doc);all_clips=clips(d)
    if not all_clips:raise ValueError("Add animation frames before exporting")
    if kind not in ("atlas","png","webp"):raise ValueError("Invalid export format")
    w,h=d["width"],d["height"]
    manifest={"format":"spriteforge-full-frame","version":1,"name":d["name"],"width":w,"height":h,"fps":d["fps"],"pivot":d["pivot"],"loop":d["loop"],"pixel":d["pixel"],"coordinates":"top-left canvas pixels","directions":{}}
    buf=io.BytesIO()
    def save(z,path,im,fmt="PNG",**kw):
        b=io.BytesIO();im.save(b,fmt,**kw);z.writestr(path,b.getvalue())
    with zipfile.ZipFile(buf,"w",compression=zipfile.ZIP_STORED) as z:
        for key,c in all_clips.items():
            ims=[world.image(s) for s in c["frames"]];records=[]
            if kind=="atlas":
                cols=max(1,min(4096//w,len(ims)));rows=max(1,4096//h);per=cols*rows
                for start in range(0,len(ims),per):
                    batch=ims[start:start+per];path=f"{key}/atlas_{start//per:02d}.png"
                    sheet=Image.new("RGBA",(cols*w,((len(batch)+cols-1)//cols)*h))
                    for j,im in enumerate(batch):
                        x=(j%cols)*w;y=(j//cols)*h;sheet.paste(im,(x,y))
                        records.append(dict(file=path,rect=[x,y,w,h]))
                    save(z,path,sheet)
            elif kind=="png":
                for j,im in enumerate(ims):
                    path=f"{key}/frame_{j:03d}.png";save(z,path,im);records.append(dict(file=path,rect=[0,0,w,h]))
            else:
                path=f"{key}/animation.webp";durations=[round((j+1)*1000/d["fps"])-round(j*1000/d["fps"]) for j in range(len(ims))]
                save(z,path,ims[0],"WEBP",save_all=True,append_images=ims[1:],duration=durations,loop=0 if d["loop"] else 1,lossless=True)
                records=[dict(file=path,index=j,duration_ms=ms) for j,ms in enumerate(durations)]
            manifest["directions"][key]={"frames":records,"combat":c["combat"]}
        z.writestr("animation.json",json.dumps(manifest,indent=2))
        z.writestr("IMPORT.txt","Godot: use atlas regions or PNG frames in SpriteFrames; pivot offset is negative pivot. Unity: slice atlas by rect, convert pivot to normalized bottom-left (x/width, 1-y/height). JSON is portable metadata, not native engine import files. Combat coordinates are top-left pixels. Animated WebP may coalesce identical frames; use PNG/atlas for exact per-frame indexing.")
    return buf.getvalue()
