"""Local cross-project asset snapshots. No model files are copied or changed."""
import json
import math
import re
import shutil
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
from . import modular, modular_rig

KINDS=("character","asset","rig","image","animation","video")
MAX_VIDEO_BYTES=64_000_000
MAX_ENTRIES=300
MAX_BYTES=1_000_000_000
_LOCK=threading.RLock()

def folder(root):
    return Path(root)/"character-library"

def _entry(root,entry_id):
    if not isinstance(entry_id,str) or not re.fullmatch(r"[a-f0-9]{32}",entry_id):
        raise ValueError("Invalid library ID")
    p=folder(root)/entry_id
    if not p.is_dir() or p.is_symlink():raise FileNotFoundError("Library entry not found")
    return p

def _text(v,n,label,required=False):
    if not isinstance(v,str) or len(v)>n or (required and not v.strip()):
        raise ValueError("Invalid "+label)
    return v.strip()

def _favorite(value):
    if type(value) is not bool:raise ValueError("Invalid favorite flag")
    return value

def _metadata(data):
    if not isinstance(data,dict):raise ValueError("Invalid entry")
    kind=data.get("kind")
    if kind not in KINDS:raise ValueError("Unknown library kind")
    tags=data.get("tags",[])
    if not isinstance(tags,list) or len(tags)>12:raise ValueError("At most 12 tags")
    return dict(kind=kind,name=_text(data.get("name",""),80,"name",True),
                notes=_text(data.get("notes",""),1000,"notes"),
                collection=_text(data.get("collection",""),80,"collection"),
                favorite=_favorite(data.get("favorite",False)),
                tags=list(dict.fromkeys(_text(t,40,"tag",True) for t in tags)))

def _normalized(data,kind):
    if kind=="video":raise ValueError("Use MP4 upload to save a video")
    if kind=="image":
        from . import world
        image=data.get("image")
        if not isinstance(image,str) or len(image)>24_000_000:raise ValueError("Invalid image or image budget exceeded")
        im=world.image(image)
        return {"image":image},im,{"category":"image","width":im.width,"height":im.height}
    if kind=="animation":
        from . import full_frame, world
        doc=full_frame.validate(data.get("document"))
        clips=[doc["frames"]]+[v["frames"] for v in doc["directions"].values()]
        populated=[frames for frames in clips if frames]
        if not populated:raise ValueError("Add animation frames before saving")
        return {"document":doc},world.image(populated[0][0]),{"category":"animation","width":doc["width"],"height":doc["height"],"frames":sum(map(len,populated)),"fps":doc["fps"],"clips":len(populated)}

    if kind=="character":
        clean,images=modular.validate(data.get("recipe"))
        if not images:raise ValueError("Add a character layer before saving")
        return {"recipe":clean},modular.composite(clean,images),{"category":"character","width":clean["width"],"height":clean["height"],"layers":len(images)}
    if kind=="asset":
        recipe=data.get("recipe")
        clean,images=modular.validate(recipe)
        index=modular.integer(data.get("index"),0,len(images)-1,"layer index")
        layer=clean["layers"][index]
        return {"layer":layer,"canvas":[clean["width"],clean["height"]],"pixel":clean["pixel"]},images[index],{"category":layer["category"],"width":images[index].width,"height":images[index].height}
    clean,body,key,joints,valid,_=modular_rig.prepare(data.get("recipe"))
    if not valid:raise ValueError("Save the body rig before adding it to the library")
    profile=modular_rig.validate_profile(clean["rig"])
    return {"profile":profile,"canvas":[clean["width"],clean["height"]]},body,{"category":"rig","width":body.width,"height":body.height}

def list_entries(root,kind="",query=""):
    if kind and kind not in KINDS:raise ValueError("Unknown library kind")
    query=_text(query,200,"search").casefold()
    rows=[]
    with _LOCK:
        base=folder(root)
        if not base.exists():return []
        for p in base.iterdir():
            if not p.is_dir() or p.is_symlink() or not re.fullmatch(r"[a-f0-9]{32}",p.name):continue
            try:
                meta=json.loads((p/"meta.json").read_text(encoding="utf-8"))
                if meta.get("id")!=p.name or meta.get("kind") not in KINDS:continue
                meta.setdefault("collection","");meta.setdefault("favorite",False)
                hay=" ".join([meta["name"],meta["notes"],meta["category"],meta["collection"],*meta["tags"]]).casefold()
                if (not kind or meta["kind"]==kind) and all(t in hay for t in query.split()):rows.append(meta)
            except (OSError,ValueError,KeyError,TypeError):continue
    return sorted(rows,key=lambda m:m["created"],reverse=True)

def _capacity(base,size):
    existing=[p for p in base.iterdir() if p.is_dir() and not p.is_symlink() and re.fullmatch(r"[a-f0-9]{32}",p.name)]
    used=sum((p/name).stat().st_size for p in existing for name in ("payload.json","video.mp4") if (p/name).is_file())
    if len(existing)>=MAX_ENTRIES or used+size>MAX_BYTES:raise ValueError("Local library limit reached; remove unused snapshots")

def save_video(root,raw,data):
    if not isinstance(raw,bytes) or not raw or len(raw)>MAX_VIDEO_BYTES or raw[4:8]!=b"ftyp":
        raise ValueError("Choose an MP4 under 64 MB")
    meta=_metadata({**data,"kind":"video"})
    import imageio.v2 as imageio
    with tempfile.TemporaryDirectory() as work:
        source=Path(work)/"source.mp4";source.write_bytes(raw)
        try:
            reader=imageio.get_reader(str(source),format="FFMPEG")
            try:
                info=reader.get_meta_data();w,h=info["size"];fps=float(info["fps"]);duration=float(info.get("duration",0))
                if min(w,h)<1 or max(w,h)>2048 or not math.isfinite(fps) or not 0<fps<=120 or not math.isfinite(duration) or duration<=0:
                    raise ValueError("Invalid video dimensions, FPS or duration")
                preview=Image.fromarray(reader.get_data(0)).convert("RGB")
            finally:reader.close()
        except (OSError,RuntimeError,IndexError,KeyError,TypeError) as exc:
            raise ValueError("Unable to decode MP4") from exc
        payload=json.dumps({"format":"mp4"},separators=(",",":")).encode()
        with _LOCK:
            base=folder(root);base.mkdir(parents=True,exist_ok=True);_capacity(base,len(raw)+len(payload))
            entry_id=uuid.uuid4().hex
            meta.update(id=entry_id,created=datetime.now(timezone.utc).isoformat(),category="video",width=w,height=h,fps=fps,duration=duration,bytes=len(raw))
            tmp=Path(tempfile.mkdtemp(prefix=".pending-",dir=base))
            try:
                shutil.copyfile(source,tmp/"video.mp4")
                (tmp/"payload.json").write_bytes(payload)
                (tmp/"meta.json").write_text(json.dumps(meta,ensure_ascii=False),encoding="utf-8")
                preview.thumbnail((128,128),Image.Resampling.LANCZOS);preview.save(tmp/"preview.png")
                tmp.rename(base/entry_id)
            finally:
                if tmp.exists():shutil.rmtree(tmp,ignore_errors=True)
    return meta

def video_path(root,entry_id):
    p=_entry(root,entry_id)/"video.mp4"
    if not p.is_file() or p.is_symlink():raise FileNotFoundError("Video asset not found")
    return p

def save(root,data):
    meta=_metadata(data)
    payload,preview,details=_normalized(data,meta["kind"])
    encoded=json.dumps(payload,ensure_ascii=False,separators=(",",":")).encode("utf-8")
    if len(encoded)>26_000_000:raise ValueError("Library entry exceeds 26 MB")
    with _LOCK:
        base=folder(root);base.mkdir(parents=True,exist_ok=True)
        _capacity(base,len(encoded))
        entry_id=uuid.uuid4().hex
        meta.update(details,id=entry_id,created=datetime.now(timezone.utc).isoformat())
        tmp=Path(tempfile.mkdtemp(prefix=".pending-",dir=base))
        try:
            (tmp/"payload.json").write_bytes(encoded)
            (tmp/"meta.json").write_text(json.dumps(meta,ensure_ascii=False),encoding="utf-8")
            thumb=preview.copy();thumb.thumbnail((128,128),Image.Resampling.LANCZOS)
            thumb.save(tmp/"preview.png")
            tmp.rename(base/entry_id)
        finally:
            if tmp.exists():shutil.rmtree(tmp,ignore_errors=True)
    return meta

def load(root,entry_id):
    with _LOCK:
        p=_entry(root,entry_id)
        return {"meta":json.loads((p/"meta.json").read_text(encoding="utf-8")),
                "payload":json.loads((p/"payload.json").read_text(encoding="utf-8"))}

def update_metadata(root,entry_id,patch):
    """Update only organization fields; never rewrite payload or preview."""
    allowed={"name","notes","tags","collection","favorite"}
    if not isinstance(patch,dict) or not patch or set(patch)-allowed:
        raise ValueError("Invalid metadata fields")
    with _LOCK:
        p=_entry(root,entry_id)
        target=p/"meta.json"
        meta=json.loads(target.read_text(encoding="utf-8"))
        clean=_metadata({**meta,**patch})
        meta.update(clean)
        meta["updated"]=datetime.now(timezone.utc).isoformat()
        with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=p,prefix=".meta-",delete=False) as out:
            tmp=Path(out.name)
            try:json.dump(meta,out,ensure_ascii=False)
            except Exception:
                out.close();tmp.unlink(missing_ok=True);raise
        try:tmp.replace(target)
        finally:tmp.unlink(missing_ok=True)
        return meta

def preview_path(root,entry_id):
    return _entry(root,entry_id)/"preview.png"

def delete(root,entry_id):
    with _LOCK:
        shutil.rmtree(_entry(root,entry_id))
    return {"deleted":True}

def apply(root,entry_id,recipe,keep_placement=False):
    """Create a validated copy. Rig presets require the exact existing body."""
    entry=load(root,entry_id);kind=entry["meta"]["kind"];data=entry["payload"]
    if kind=="character":return modular.validate(data["recipe"])[0]
    if kind not in ("asset","rig"):raise ValueError("Use the appropriate studio to open this asset")
    clean,_=modular.validate(recipe)
    if kind=="rig":
        _,_,key,_,_,_=modular_rig.prepare(clean)
        if data["profile"]["body_key"]!=key:raise ValueError("Rig preset belongs to a different body or canvas")
        clean["rig"]=modular_rig.validate_profile(data["profile"])
        return clean
    if len(clean["layers"])>=modular.MAX_LAYERS:raise ValueError("Remove a layer before importing another")
    layer=dict(data["layer"])
    if not clean["layers"]:
        clean["width"],clean["height"]=data["canvas"];clean["pixel"]=data["pixel"]
    same_canvas=data["canvas"]==[clean["width"],clean["height"]]
    if not keep_placement or not same_canvas:
        im=modular.decode(layer["image"])
        layer.update(x=(clean["width"]-im.width)//2,y=(clean["height"]-im.height)//2,scale=100,flip=False)
    # Canvas-space brush coordinates and body masks need review on a new base.
    if layer["motion"]["mode"]=="weighted":
        layer["motion"]=modular.motion_settings()
    layer.pop("occlusion",None)
    layer["visible"]=True
    if layer["category"]=="body":
        for l in clean["layers"]:
            if l["category"]=="body":l["visible"]=False
        clean.pop("rig",None)
    order=modular.CATEGORIES
    i=next((i for i,l in enumerate(clean["layers"]) if order.index(l["category"])>order.index(layer["category"])),len(clean["layers"]))
    clean["layers"].insert(i,layer)
    return modular.validate(clean)[0]
