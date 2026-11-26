"""Project save/load: one folder per character under <app>/projects/<name>/
   project.json (all settings + rig + skeleton), ref.png, anim.png, sprites/*.png (saved results)."""
import base64, io, json, re, shutil, time, tempfile, zipfile, stat
from threading import RLock
from pathlib import Path
from PIL import Image


class ProjectError(ValueError):
    pass


def safe_name(name):
    s = re.sub(r"[^A-Za-z0-9 _-]+", "", str(name or "")).strip()[:60]
    if not s:
        raise ProjectError("project name is empty (use letters, numbers, spaces, - and _)")
    return s


def _dir(root, name, must_exist=False):
    base = (Path(root) / "projects").resolve()
    d = (base / safe_name(name)).resolve()
    if base not in d.parents:
        raise ProjectError("invalid project name")
    if must_exist and not d.exists():
        raise ProjectError(f"project not found: {name}")
    return d


def _decode_png(data_url, max_bytes=8_000_000):
    """data URL -> sanitized PNG bytes (re-encoded through PIL, so only real images are ever written)."""
    if not isinstance(data_url, str) or "," not in data_url:
        raise ProjectError("bad image data")
    raw = base64.b64decode(data_url.split(",", 1)[1])
    if len(raw) > max_bytes:
        raise ProjectError("image too large")
    img = Image.open(io.BytesIO(raw)).convert("RGBA")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def _encode(path):
    return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()


def _slug(s):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(s))[:30] or "anim"


def _save_results(d, results):
    """Cleaned animation results (per clip): final + rig-only frames, accept flags. Decoded first, then swapped in."""
    staged = {}
    for anim, r in list((results or {}).items())[:12]:
        if not r or not r.get("frames"):
            continue
        staged[_slug(anim)] = (
            [_decode_png(u) for u in r["frames"][:32]], [_decode_png(u) for u in (r.get("raw") or [])[:32]],
            {k: r.get(k) for k in ("fps", "size", "pivot", "info", "accept", "anim")})
    rd = d / "results"
    if rd.exists():
        shutil.rmtree(rd)
    for a, (fr, raw, meta) in staged.items():
        ad = rd / a
        ad.mkdir(parents=True)
        for i, b in enumerate(fr):
            (ad / f"f_{i:02d}.png").write_bytes(b)
        for i, b in enumerate(raw):
            (ad / f"r_{i:02d}.png").write_bytes(b)
        (ad / "meta.json").write_text(json.dumps(meta))


def _load_results(d):
    out = {}
    rd = d / "results"
    if rd.exists():
        for ad in sorted(rd.iterdir()):
            try:
                meta = json.loads((ad / "meta.json").read_text())
            except Exception:
                continue
            meta["frames"] = [_encode(p) for p in sorted(ad.glob("f_*.png"))]
            meta["raw"] = [_encode(p) for p in sorted(ad.glob("r_*.png"))]
            out[meta.get("anim") or ad.name] = meta
    return out


def _save_portrait(d, pt):
    pd = d / "portrait"
    staged = None
    if pt and pt.get("base"):
        staged = (_decode_png(pt["base"]),
                  [(_slug(e.get("name")), _decode_png(e["image"])) for e in (pt.get("exprs") or [])[:24] if e.get("image")],
                  pt.get("mask"))
    if pd.exists():
        shutil.rmtree(pd)
    if staged:
        pd.mkdir(parents=True)
        (pd / "base.png").write_bytes(staged[0])
        for nm, b in staged[1]:
            (pd / f"e_{nm}.png").write_bytes(b)
        (pd / "portrait.json").write_text(json.dumps({"mask": staged[2], "order": [n for n, _ in staged[1]]}))


def _load_portrait(d):
    pd = d / "portrait"
    if not (pd / "base.png").exists():
        return None
    try:
        meta = json.loads((pd / "portrait.json").read_text())
    except Exception:
        meta = {}
    exprs = [{"name": n, "image": _encode(pd / f"e_{n}.png")} for n in meta.get("order", []) if (pd / f"e_{n}.png").exists()]
    return {"base": _encode(pd / "base.png"), "mask": meta.get("mask"), "exprs": exprs}


def _save_tileset(d, ts):
    """The tileset being built in the Tiles tab: tiles (name + image) in order."""
    td = d / "tileset"
    staged = None
    if ts and ts.get("tiles"):
        staged = [(str(e.get("name") or ""), _decode_png(e["image"]), bool(e.get("solid"))) for e in ts["tiles"][:512] if e.get("image")]
    if td.exists():
        shutil.rmtree(td)
    if staged:
        td.mkdir(parents=True)
        for i, (_, b, _s) in enumerate(staged):
            (td / f"t_{i:03d}.png").write_bytes(b)
        (td / "tileset.json").write_text(json.dumps({"names": [s[0] for s in staged], "solid": [s[2] for s in staged]}))


def _load_tileset(d):
    td = d / "tileset"
    try:
        meta = json.loads((td / "tileset.json").read_text())
        names = meta["names"]
    except Exception:
        return None
    solid = meta.get("solid") or []
    tiles = [{"name": n, "image": _encode(td / f"t_{i:03d}.png"), "solid": bool(i < len(solid) and solid[i])}
             for i, n in enumerate(names) if (td / f"t_{i:03d}.png").exists()]
    return {"tiles": tiles} if tiles else None


def list_projects(root):
    base = Path(root) / "projects"
    out = []
    if base.exists():
        for d in base.iterdir():
            f = d / "project.json"
            if f.exists():
                try:
                    out.append({"name": d.name, "saved_at": json.loads(f.read_text()).get("saved_at", 0)})
                except Exception:
                    out.append({"name": d.name, "saved_at": 0})
    return sorted(out, key=lambda p: -p["saved_at"])


def validate_clips(value, profile):
    from . import custom_skeleton
    if value is None:return []
    if not isinstance(value,list) or len(value)>24:raise ValueError("At most 24 saved clips")
    if value and not profile:raise ValueError("Saved clips require a skeleton")
    out=[];names=set()
    for clip in value:
        if not isinstance(clip,dict):raise ValueError("Invalid saved clip")
        name=clip.get("name")
        if not isinstance(name,str) or not name.strip() or len(name)>60 or name in names:raise ValueError("Invalid or duplicate saved clip name")
        names.add(name)
        candidate=custom_skeleton.validate({**profile,"timeline":clip.get("timeline"),"ik":clip.get("ik",[])})
        if "timeline" not in candidate:raise ValueError("Saved clip requires a timeline")
        out.append({"name":name,"timeline":candidate["timeline"],"ik":candidate.get("ik",[])})
    return out


def save(root, name, data):
    with _PROJECT_LOCK:
        return _save(root, name, data)


def _save(root, name, data):
    from . import modular, custom_skeleton, custom_cleanup, scenes
    scene=data.get('scene')
    clean_scene=scenes.validate(scene)[0] if scene is not None else None
    clean_cleanup=custom_cleanup.validate_saved(data.get('custom_cleanup'))
    profile=data.get("custom_skeleton")
    clean_profile=custom_skeleton.validate(profile) if profile is not None else None
    clean_clips=validate_clips(data.get("custom_clips"),clean_profile)
    recipe=data.get("modular")
    clean_recipe=modular.validate(recipe)[0] if recipe is not None else None
    d = _dir(root, name)
    images = data.get("images") or {}
    keys=("ref", "anim", "tpl", "tplref", "tile", "terra", "terrb", "terrc", "terrd", "animstart", "animend", "characterref", "charvariant", "customrig", "characterart")
    # Reject malformed input before replacing any image from an existing project.
    staged={key:_decode_png(images[key]) for key in keys if images.get(key)}
    d.mkdir(parents=True, exist_ok=True)
    for key in keys:
        f = d / f"{key}.png"
        if key in staged:
            tmp=f.with_suffix(".png.tmp");tmp.write_bytes(staged[key]);tmp.replace(f)
        elif f.exists():
            f.unlink()
    _save_results(d, data.get("results"))
    _save_portrait(d, data.get("portrait"))
    _save_tileset(d, data.get("tileset"))
    doc = {"version": 1, "name": d.name, "saved_at": time.time(),
           "settings": data.get("settings", {}), "modular": clean_recipe, "custom_skeleton": clean_profile, "custom_clips": clean_clips, "custom_cleanup": clean_cleanup, "scene": clean_scene, "rig": data.get("rig"), "skeleton": data.get("skeleton"),
           "anim_params": data.get("anim_params", {}), "tab": data.get("tab", 1), "palette": data.get("palette"), "template": data.get("template"), "directions": data.get("directions"),
           "has_ref": (d / "ref.png").exists(), "has_anim": (d / "anim.png").exists()}
    tmp = d / "project.json.tmp"
    tmp.write_text(json.dumps(doc, indent=1))
    tmp.replace(d / "project.json")  # atomic: a crash mid-save can't corrupt the previous save
    return {"name": d.name, "saved_at": doc["saved_at"]}


def load(root, name):
    d = _dir(root, name, True)
    f = d / "project.json"
    if not f.exists():
        raise ProjectError(f"project not found: {name}")
    doc = json.loads(f.read_text())
    doc["results"] = _load_results(d)
    doc["portrait"] = _load_portrait(d)
    doc["tileset"] = _load_tileset(d)
    doc["images"] = {k: _encode(d / f"{k}.png") if (d / f"{k}.png").exists() else None for k in ("ref", "anim", "tpl", "tplref", "tile", "terra", "terrb", "terrc", "terrd", "animstart", "animend", "characterref", "charvariant", "customrig", "characterart")}
    return doc


def delete(root, name):
    with _PROJECT_LOCK:
        shutil.rmtree(_dir(root, name, True))


def add_sprite(root, name, data_url):
    d = _dir(root, name)
    (d / "sprites").mkdir(parents=True, exist_ok=True)
    sid = time.strftime("%Y%m%d_%H%M%S") + f"_{int(time.time() * 1000) % 1000:03d}"
    (d / "sprites" / f"{sid}.png").write_bytes(_decode_png(data_url))
    return sid


def list_sprites(root, name, limit=200):
    d = _dir(root, name) / "sprites"
    if not d.exists():
        return []
    files = sorted(d.glob("*.png"), reverse=True)[:limit]
    return [{"id": p.stem, "data": _encode(p)} for p in files]


def delete_sprite(root, name, sid):
    f = _dir(root, name, True) / "sprites" / (re.sub(r"[^0-9_]", "", sid) + ".png")
    if f.exists():
        f.unlink()


# Phase 57: portable, bounded project archives. Never extract arbitrary ZIP paths.
_PROJECT_LOCK = RLock()
_BUNDLE_LIMIT = 128 * 1024 * 1024
_BUNDLE_FILES = 2048
_BUNDLE_PART = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_. -]{0,79}")

def _allowed_member(name):
    parts = name.split("/")
    if any(not _BUNDLE_PART.fullmatch(p) or p.endswith((".", " ")) for p in parts):
        return False
    if len(parts) == 1:
        return name == "project.json" or bool(re.fullmatch(r"[A-Za-z0-9_]+\.png", name))
    if len(parts) == 2 and parts[0] in ("sprites", "portrait", "tileset"):
        return bool(re.fullmatch(r"[A-Za-z0-9_-]+\.(png|json)", parts[1]))
    if len(parts) == 3 and parts[0] == "results":
        return bool(re.fullmatch(r"[A-Za-z0-9_-]+", parts[1]) and re.fullmatch(r"[A-Za-z0-9_-]+\.(png|json)", parts[2]))
    return False

def _bundle(root, name):
    src = _dir(root, name, True)
    if not (src / "project.json").is_file():
        raise ProjectError("Save the project first")
    buf = io.BytesIO()
    total = count = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=3) as z:
        for p in sorted(src.rglob("*")):
            if p.is_symlink():
                raise ProjectError("Project contains a symbolic link")
            if not p.is_file():
                continue
            rel = p.relative_to(src).as_posix()
            if not _allowed_member(rel):
                continue
            total += p.stat().st_size
            count += 1
            if total > _BUNDLE_LIMIT or count > _BUNDLE_FILES:
                raise ProjectError("Project exceeds portable bundle limit")
            z.write(p, rel)
    if len(buf.getbuffer()) > _BUNDLE_LIMIT:
        raise ProjectError("Bundle exceeds size limit")
    return buf.getvalue()

def bundle(root, name):
    with _PROJECT_LOCK:
        return _bundle(root, name)

def _restore(root, name, raw):
    dest = _dir(root, name)
    if dest.exists():
        raise ProjectError("Destination already exists; choose a new name")
    if not isinstance(raw, bytes) or len(raw) > _BUNDLE_LIMIT:
        raise ProjectError("Bundle exceeds size limit")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="sf-import-", dir=dest.parent.parent) as stage:
        temp = Path(stage) / "project"
        temp.mkdir()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            entries = z.infolist()
            if len(entries) > _BUNDLE_FILES or sum(i.file_size for i in entries) > _BUNDLE_LIMIT:
                raise ProjectError("Bundle exceeds extraction limit")
            seen = set()
            for i in entries:
                key = i.filename.casefold()
                if not _allowed_member(i.filename) or key in seen or i.is_dir() or stat.S_ISLNK(i.external_attr >> 16):
                    raise ProjectError("Unsupported or duplicate bundle member")
                seen.add(key)
                data = z.read(i)
                p = temp / i.filename
                p.parent.mkdir(parents=True, exist_ok=True)
                if p.suffix == ".png":
                    with Image.open(io.BytesIO(data)) as im:
                        if im.format != "PNG" or im.width * im.height > 16_000_000:
                            raise ProjectError("Invalid bundle image")
                        im.verify()
                else:
                    json.loads(data)
                p.write_bytes(data)
        doc = json.loads((temp / "project.json").read_bytes())
        if not isinstance(doc, dict) or doc.get("version") != 1:
            raise ProjectError("Unsupported project version")
        from . import custom_skeleton, custom_cleanup, modular, scenes
        profile = custom_skeleton.validate(doc["custom_skeleton"]) if doc.get("custom_skeleton") is not None else None
        validate_clips(doc.get("custom_clips"), profile)
        if doc.get("scene") is not None: scenes.validate(doc["scene"])
        if doc.get("modular") is not None: modular.validate(doc["modular"])
        custom_cleanup.validate_saved(doc.get("custom_cleanup"))
        doc["name"] = dest.name
        doc["saved_at"] = time.time()
        (temp / "project.json").write_text(json.dumps(doc), encoding="utf-8")
        if dest.exists():
            raise ProjectError("Destination already exists")
        temp.rename(dest)
    return {"name": dest.name}

def restore_bundle(root, name, raw):
    with _PROJECT_LOCK:
        return _restore(root, name, raw)

def duplicate(root, source, destination):
    with _PROJECT_LOCK:
        return _restore(root, destination, _bundle(root, source))
