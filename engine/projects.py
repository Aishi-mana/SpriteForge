"""Project save/load: one folder per character under <app>/projects/<name>/
   project.json (all settings + rig + skeleton), ref.png, anim.png, sprites/*.png (saved results)."""
import base64, io, json, re, shutil, time
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


def save(root, name, data):
    from . import modular
    recipe=data.get("modular")
    clean_recipe=modular.validate(recipe)[0] if recipe is not None else None
    d = _dir(root, name)
    d.mkdir(parents=True, exist_ok=True)
    images = data.get("images") or {}
    for key in ("ref", "anim", "tpl", "tplref", "tile", "terra", "terrb", "terrc", "terrd", "animstart", "animend", "characterref", "charvariant"):
        f = d / f"{key}.png"
        if images.get(key):
            f.write_bytes(_decode_png(images[key]))
        elif f.exists():
            f.unlink()
    _save_results(d, data.get("results"))
    _save_portrait(d, data.get("portrait"))
    _save_tileset(d, data.get("tileset"))
    doc = {"version": 1, "name": d.name, "saved_at": time.time(),
           "settings": data.get("settings", {}), "modular": clean_recipe, "rig": data.get("rig"), "skeleton": data.get("skeleton"),
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
    doc["images"] = {k: _encode(d / f"{k}.png") if (d / f"{k}.png").exists() else None for k in ("ref", "anim", "tpl", "tplref", "tile", "terra", "terrb", "terrc", "terrd", "animstart", "animend", "characterref", "charvariant")}
    return doc


def delete(root, name):
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
