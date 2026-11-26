"""Local cross-project asset snapshots. No model files are copied or changed."""
import json
import re
import shutil
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image
from . import modular, modular_rig

KINDS=("character","asset","rig")
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

def _metadata(data):
    if not isinstance(data,dict):raise ValueError("Invalid entry")
    kind=data.get("kind")
    if kind not in KINDS:raise ValueError("Unknown library kind")
    tags=data.get("tags",[])
    if not isinstance(tags,list) or len(tags)>12:raise ValueError("At most 12 tags")
    return dict(kind=kind,name=_text(data.get("name",""),80,"name",True),
                notes=_text(data.get("notes",""),1000,"notes"),
                tags=list(dict.fromkeys(_text(t,40,"tag",True) for t in tags)))

def _normalized(data,kind):
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
                hay=" ".join([meta["name"],meta["notes"],meta["category"],*meta["tags"]]).casefold()
                if (not kind or meta["kind"]==kind) and all(t in hay for t in query.split()):rows.append(meta)
            except (OSError,ValueError,KeyError,TypeError):continue
    return sorted(rows,key=lambda m:m["created"],reverse=True)

def save(root,data):
    meta=_metadata(data)
    payload,preview,details=_normalized(data,meta["kind"])
    encoded=json.dumps(payload,ensure_ascii=False,separators=(",",":")).encode("utf-8")
    if len(encoded)>26_000_000:raise ValueError("Library entry exceeds 26 MB")
    with _LOCK:
        base=folder(root);base.mkdir(parents=True,exist_ok=True)
        existing=[p for p in base.iterdir() if p.is_dir() and not p.is_symlink() and re.fullmatch(r"[a-f0-9]{32}",p.name)]
        used=sum((p/"payload.json").stat().st_size for p in existing if (p/"payload.json").is_file())
        if len(existing)>=MAX_ENTRIES or used+len(encoded)>MAX_BYTES:raise ValueError("Local library limit reached; remove unused snapshots")
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
