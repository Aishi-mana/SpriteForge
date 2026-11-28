"""Portable library snapshots; never extract arbitrary archive paths."""
import hashlib
import json
import re
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from PIL import Image
from . import asset_library as L, modular, modular_rig

FORMAT="spriteforge-library"
MAX_ARCHIVE=1_100_000_000
LIMITS={"meta.json":64_000,"payload.json":26_000_000,"preview.png":256_000,"video.mp4":L.MAX_VIDEO_BYTES}
ID=re.compile(r"[0-9a-f]{32}")

def _digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
    return h.hexdigest()

def _names(meta):
    return ["meta.json","payload.json","preview.png"]+(["video.mp4"] if meta["kind"]=="video" else [])

def export(root,output,entry_id=None):
    with L._LOCK:
        rows=L.list_entries(root) if entry_id is None else [L.load(root,entry_id)["meta"]]
        manifest={"format":FORMAT,"version":1,"entries":{}}
        with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_STORED) as z:
            for meta in rows:
                key=meta["id"];p=L._entry(root,key);files={}
                for name in _names(meta):
                    f=p/name
                    if not f.is_file() or f.is_symlink() or f.stat().st_size>LIMITS[name]:raise ValueError("Invalid stored asset file")
                    files[name]={"bytes":f.stat().st_size,"sha256":_digest(f)}
                    z.write(f,key+"/"+name)
                manifest["entries"][key]=files
            z.writestr("manifest.json",json.dumps(manifest,separators=(",",":")))
    return len(rows)

def _read(z,name,path,expected):
    info=z.getinfo(name)
    if info.file_size!=expected["bytes"]:raise ValueError("Backup file size mismatch")
    h=hashlib.sha256();n=0
    with z.open(info) as src,path.open("wb") as dst:
        while chunk:=src.read(1024*1024):
            n+=len(chunk)
            if n>info.file_size:raise ValueError("Backup file exceeds declared size")
            h.update(chunk);dst.write(chunk)
    if n!=info.file_size or h.hexdigest()!=expected["sha256"]:raise ValueError("Backup checksum mismatch")

def _validate(p,key):
    m=json.loads((p/"meta.json").read_text(encoding="utf-8"));d=json.loads((p/"payload.json").read_text(encoding="utf-8"))
    clean=L._metadata(m)
    if m.get("id")!=key or not isinstance(d,dict):raise ValueError("Invalid backup asset")
    datetime.fromisoformat(m["created"])
    if "updated" in m:datetime.fromisoformat(m["updated"])
    kind=clean["kind"]
    if kind in ("image","animation","character"):
        _,_,details=L._normalized(d,kind)
    elif kind=="asset":
        w,h=d["canvas"];_,_,details=L._normalized({"recipe":{"width":w,"height":h,"pixel":d["pixel"],"layers":[d["layer"]]},"index":0},kind)
    elif kind=="rig":
        w,h=d["canvas"];modular.integer(w,16,1024,"width");modular.integer(h,16,1024,"height")
        profile=modular_rig.validate_profile(d["profile"])
        if any(x>w or y>h for x,y in profile["joints"].values()):raise ValueError("Invalid rig canvas")
        details={"category":"rig","width":w,"height":h}
    else:
        import imageio.v2 as imageio
        f=p/"video.mp4"
        with f.open("rb") as stream:
            if stream.read(8)[4:8]!=b"ftyp":raise ValueError("Invalid MP4")
        reader=imageio.get_reader(str(f),format="FFMPEG")
        try:
            import math
            info=reader.get_meta_data();w,h=info["size"];fps=float(info["fps"]);duration=float(info["duration"])
            if min(w,h)<1 or max(w,h)>2048 or not math.isfinite(fps) or not 0<fps<=120 or not math.isfinite(duration) or duration<=0:raise ValueError("Invalid MP4 metadata")
            reader.get_data(0)
        finally:reader.close()
        if d!={"format":"mp4"}:raise ValueError("Invalid video payload")
        details={"category":"video","width":w,"height":h,"fps":fps,"duration":duration,"bytes":f.stat().st_size}
    with Image.open(p/"preview.png") as im:
        if im.format!="PNG" or min(im.size)<1 or max(im.size)>128:raise ValueError("Invalid preview")
        im.load()
    clean.update(details,id=key,created=m["created"])
    if "updated" in m:clean["updated"]=m["updated"]
    parent=m.get("parent_id");relation=m.get("relation")
    if parent is not None or relation is not None:
        if not isinstance(parent,str) or not ID.fullmatch(parent) or relation not in L.RELATIONS:raise ValueError("Invalid relationship")
        clean.update(parent_id=parent,relation=relation)
    return clean

def restore(root,source):
    """Validate all entries in staging, then publish copies; never overwrite."""
    base=L.folder(root);base.mkdir(parents=True,exist_ok=True)
    try:
        with L._LOCK,tempfile.TemporaryDirectory(prefix=".restore-",dir=base) as work,zipfile.ZipFile(source) as z:
            infos=z.infolist();names=[i.filename for i in infos]
            if len(names)>1+4*L.MAX_ENTRIES or len(set(names))!=len(names) or "manifest.json" not in names:raise ValueError("Invalid backup members")
            if z.getinfo("manifest.json").file_size>256_000 or sum(i.file_size for i in infos)>MAX_ARCHIVE:raise ValueError("Backup exceeds size limit")
            manifest=json.loads(z.read("manifest.json"))
            if manifest.get("format")!=FORMAT or manifest.get("version")!=1:raise ValueError("Unsupported backup format")
            entries=manifest["entries"]
            if not isinstance(entries,dict) or len(entries)>L.MAX_ENTRIES:raise ValueError("Invalid backup entry count")
            expected={"manifest.json"};size=0
            for key,files in entries.items():
                if not ID.fullmatch(key) or not isinstance(files,dict) or set(files) not in ({"meta.json","payload.json","preview.png"},set(LIMITS)):raise ValueError("Invalid backup entry")
                for name,info in files.items():
                    if type(info["bytes"]) is not int or not 0<info["bytes"]<=LIMITS[name] or not re.fullmatch(r"[0-9a-f]{64}",info["sha256"]):raise ValueError("Invalid backup file manifest")
                    expected.add(key+"/"+name)
                    if name in ("payload.json","video.mp4"):size+=info["bytes"]
            if expected!=set(names):raise ValueError("Unexpected or missing backup members")
            existing=[p for p in base.iterdir() if p.is_dir() and ID.fullmatch(p.name)]
            used=sum((p/n).stat().st_size for p in existing for n in ("payload.json","video.mp4") if (p/n).is_file())
            if len(existing)+len(entries)>L.MAX_ENTRIES or used+size>L.MAX_BYTES:raise ValueError("Restore exceeds library capacity")
            stage=Path(work);metas={}
            for key,files in entries.items():
                p=stage/key;p.mkdir()
                for name,info in files.items():_read(z,key+"/"+name,p/name,info)
                m=_validate(p,key)
                if set(files)!=set(_names(m)):raise ValueError("Asset files do not match type")
                metas[key]=m
            # All source IDs are remapped on collision; external links are detached
            # rather than accidentally pointing to an unrelated local asset.
            mapping={key:uuid.uuid4().hex if (base/key).exists() else key for key in metas}
            detached=0
            for key,m in metas.items():
                seen={key};cursor=m.get("parent_id")
                while cursor in metas:
                    if cursor in seen:raise ValueError("Backup relationship cycle")
                    seen.add(cursor);cursor=metas[cursor].get("parent_id")
                parent=m.get("parent_id")
                if parent in metas:
                    kinds=(metas[parent]["kind"],m["kind"])
                    if m["relation"]=="revision" and kinds[0]!=kinds[1]:raise ValueError("Invalid revision types")
                    if m["relation"]=="extracted_from" and kinds!=("video","animation"):raise ValueError("Invalid extraction types")
            for key,m in metas.items():
                parent=m.get("parent_id")
                if parent in mapping:m["parent_id"]=mapping[parent]
                elif parent:
                    m.pop("parent_id");m.pop("relation");detached+=1
                m["id"]=mapping[key]
                (stage/key/"meta.json").write_text(json.dumps(m,ensure_ascii=False),encoding="utf-8")
            published=[]
            try:
                for key,new in mapping.items():
                    target=base/new
                    if target.exists():raise ValueError("Restore ID collision")
                    (stage/key).rename(target);published.append(target)
            except Exception:
                for target in published:shutil.rmtree(target)
                raise
            return {"imported":len(mapping),"remapped":sum(k!=v for k,v in mapping.items()),"detached":detached}
    except (zipfile.BadZipFile,KeyError,TypeError,AttributeError,IndexError,OSError,RuntimeError) as exc:
        raise ValueError("Invalid or unreadable library backup: "+str(exc)) from exc
