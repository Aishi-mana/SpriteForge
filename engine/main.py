import base64, io, json, re
from typing import List, Optional
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image
import numpy as np

import hashlib
from fastapi import Body
import atexit
from . import generate as gen, pixelize as px, rig, refine as refiner, projects, exporter, llm, portrait, diag, palettes, templates, directions, jobs, tiles, terrain

ROOT = Path(__file__).resolve().parent.parent
CFG_PATH = ROOT / "config.json"
DEFAULT = {"models_dir": "", "port": 8765}
app = FastAPI(title="SpriteForge")
palettes.load_into_px(ROOT)  # your saved palettes become usable by name everywhere a palette can be chosen


@app.exception_handler(StarletteHTTPException)
async def _http_error(request, exc):
    diag.record_error(request.url.path, exc.status_code, exc.detail)  # shown in the diagnostics report
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


def cfg():
    """Tolerant config reader: BOM, Windows backslashes, or a broken file never take the app down."""
    try:
        txt = CFG_PATH.read_text(encoding="utf-8-sig")
    except Exception:
        return dict(DEFAULT)
    for attempt in (txt, txt.replace("\\", "/")):
        try:
            return {**DEFAULT, **json.loads(attempt)}
        except Exception:
            pass
    return dict(DEFAULT)


def cfg_dir():
    return cfg()["models_dir"] or "."


def b64(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def scan(sub):
    d = Path(cfg()["models_dir"]) / sub
    if not cfg()["models_dir"]: return []
    names=[p.name for p in d.glob("*.safetensors") if p.is_file()]
    if sub=="checkpoints":
        names += [p.name for p in d.iterdir() if p.is_dir() and (p/"model_index.json").is_file()] if d.is_dir() else []
        from .local_runtime import QWEN_CHECKPOINTS
        for name in QWEN_CHECKPOINTS:
            q=d.parent/"diffusion_models"/name
            if q.is_file() and q.name not in names:names.append(q.name)
    return sorted(names)


@app.get("/api/state")
def state():
    try:
        import torch
        gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    except Exception:
        gpu = None
    md = cfg()["models_dir"]
    kinds = {"checkpoints": {}, "loras": {}}
    for sub in kinds:  # tag files that cannot work with the SDXL pipelines (Flux, SD1.5, video...) or are broken
        for name in scan(sub):
            path = _checkpoint_path(Path(md),name) if sub=="checkpoints" else Path(md)/sub/name
            if path.is_dir():
                kinds[sub][name]=mf.identify(path)
                continue
            r = diag.inspect_file(path, sub == "loras")
            kinds[sub][name] = r["kind"] if r["status"] == "ok" else "broken"
    models={name:mf.describe(_checkpoint_path(Path(md),name)) for name in scan("checkpoints")}
    lora_families={name:mf.identify(Path(md)/"loras"/name,True) for name in scan("loras")}
    return {"model_info":models,"lora_families":lora_families,"ckpt_kinds": kinds["checkpoints"], "lora_kinds": kinds["loras"], "models_dir": md, "models_dir_ok": bool(md) and Path(md).exists(), "checkpoints": scan("checkpoints"),
            "loras": scan("loras"), "palettes": list(px.PALETTES), "gpu": gpu}


class Cfg(BaseModel):
    models_dir: str


@app.post("/api/config")
def set_cfg(c: Cfg):
    data = cfg()
    data["models_dir"] = c.models_dir.strip().strip('"').replace("\\", "/")
    CFG_PATH.write_text(json.dumps(data, indent=2))
    return state()


def _checkpoint_path(md,name):
    p=md/"checkpoints"/name
    from .local_runtime import QWEN_CHECKPOINTS
    if not p.exists() and name in QWEN_CHECKPOINTS:p=md/"diffusion_models"/name
    return p


def _paths(checkpoint):
    md = Path(cfg()["models_dir"])
    if not checkpoint or Path(checkpoint).name != checkpoint:
        raise HTTPException(400,"Select a valid checkpoint")
    ckpt = _checkpoint_path(md,checkpoint)
    if not ckpt.exists():
        raise HTTPException(400, f"checkpoint not found: {ckpt}")
    info=mf.describe(ckpt)
    if not info["supported"]: raise HTTPException(400,info["detail"])
    return str(ckpt), str(md / "loras")


def _outline(v):
    return v if v in ("dark", "selective") else "none"


@app.post("/api/pixelize")
def pixelize_ep(file: UploadFile = File(...), mode: str = Form("auto"), size: int = Form(64), colors: int = Form(16),
                palette: str = Form("none"), remove_bg: bool = Form(True), bg_tol: int = Form(40),
                remove_shadow: bool = Form(True), crisp: bool = Form(True), clean: bool = Form(True),
                outline: str = Form("none")):
    sprite, info = px.pixelize(Image.open(file.file), mode, size, colors, palette, remove_bg, bg_tol,
                               remove_shadow=remove_shadow, crisp=crisp, clean=clean, outline=_outline(outline))
    return {"results": [{"sprite": b64(sprite), "info": info}]}


from . import styles, inbetween, model_families as mf, character, modular, modular_assets, modular_rig, layer_export, asset_library, custom_skeleton, custom_timeline, custom_ik, custom_cleanup


def _art_style(value):
    if value not in styles.PRESETS:
        raise HTTPException(400, f"Unknown art style: {value}")
    return value


class GenParams(BaseModel):
    art_style: str = "pixel"
    hd_size: int = 768
    gen_size: int = 1024
    prompt: str
    negative: str = ""
    checkpoint: str
    lora: str = ""
    lora_weight: float = 1.0
    steps: int = 25
    cfg: float = 7.0
    seed: int = -1
    bg: str = "white"
    n: int = 1
    mode: str = "fixed"
    size: int = 64
    colors: int = 16
    palette: str = "none"
    remove_bg: bool = True
    bg_tol: int = 40
    remove_shadow: bool = True
    crisp: bool = True
    clean: bool = True
    outline: str = "none"
    sampler: str = "euler_a"
    kind: str = "sprite"      # sprite | tile | prop | icon | ui  (tile = seamless tile on a fixed square canvas)
    seamless: bool = True     # tiles only


def _run(p_ckpt, lora_dir, lora, lw, prompt, neg, steps, cfg_, seed, bg, n, ip_image, ip_scale, post,
         control_image=None, cn_scale=0.8, cn_dir=None, gen_size=1024, kind="sprite", art_style="pixel"):
    try:
        # Bound retained raw images before generation, regardless of UI settings.
        if not 1<=n<=6 or not 128<=gen_size<=1024 or n*gen_size*gen_size>6_400_000:
            raise ValueError("Generation batch exceeds image budget")
        outs = gen.generate(p_ckpt, lora, lw, lora_dir, prompt, neg, steps, cfg_, seed, gen_size, bg, ip_image, ip_scale, n,
                            control_image, cn_scale, cn_dir, kind, art_style=art_style) if art_style != "pixel" else gen.generate(
                                p_ckpt, lora, lw, lora_dir, prompt, neg, steps, cfg_, seed, gen_size, bg, ip_image, ip_scale, n,
                                control_image, cn_scale, cn_dir, kind)
    except ValueError as e:
        raise HTTPException(400,str(e))
    except Exception as e:
        hint = " - out of GPU memory: lower 'Generation size', set Variations to 1, close other GPU apps" if "out of memory" in str(e).lower() else ""
        raise HTTPException(500, f"{type(e).__name__}: {e}{hint}")
    results = []
    for raw, s in outs:
        try:sprite, info = post(raw)
        except ValueError as e:raise HTTPException(400,str(e))
        info["seed"] = s
        info["art_style"] = art_style
        if control_image is not None:
            info["controlnet"] = gen.controlnet_name()
        results.append({"raw": b64(raw.resize((384, 384))), "sprite": b64(sprite), "info": info})
    return {"results": results}


def _do_generate(p):
    ckpt, lora_dir = _paths(p.checkpoint)
    gen.set_sampler(p.sampler)
    kind = p.kind if p.kind in ("sprite", "tile", "prop", "icon", "ui") else "sprite"
    art_style = _art_style(p.art_style) if kind == "sprite" else "pixel"
    if art_style != "pixel":
        post = lambda raw: styles.finish(raw, p.hd_size, p.remove_bg, p.bg_tol)
    elif kind == "tile":
        size = max(8, min(int(p.size), 128))
        post = lambda raw: tiles.tile_post(raw, size, p.colors, p.palette, p.seamless)
    else:
        post = lambda raw: px.pixelize(raw, p.mode, p.size, p.colors, p.palette, p.remove_bg, p.bg_tol,
                                       remove_shadow=p.remove_shadow, crisp=p.crisp, clean=p.clean, outline=_outline(p.outline))
    from . import local_runtime as lr
    return _run(ckpt, lora_dir, p.lora, p.lora_weight, p.prompt, p.negative, p.steps, p.cfg, p.seed, p.bg,
                max(1, min(p.n, 6)), None, 0, post, kind=kind, art_style=art_style,
                gen_size=max(512, min(p.gen_size, 1024)) // 64 * 64 if art_style != "pixel" or lr.route(ckpt) else 1024)


@app.post("/api/generate")
def generate_ep(p: GenParams):
    return _do_generate(p)


@app.post("/api/reference")
def reference_ep(ref: UploadFile = File(...), pose_img: Optional[UploadFile] = File(None), pose: str = Form(""),
                 character: str = Form(""), negative: str = Form(""), checkpoint: str = Form(...), lora: str = Form(""),
                 lora_weight: float = Form(1.0), steps: int = Form(25), cfg: float = Form(7.0), seed: int = Form(-1),
                 bg: str = Form("white"), ip_scale: float = Form(0.7), n: int = Form(1), colors: int = Form(16),
                 lock_palette: bool = Form(True), match_size: bool = Form(True), bg_tol: int = Form(40),
                 cn_scale: float = Form(0.8), canvas: int = Form(128), remove_shadow: bool = Form(True),
                 gen_size: int = Form(768), crisp: bool = Form(True), clean: bool = Form(True),
                 outline: str = Form("none"), sampler: str = Form("euler_a"),
                 art_style: str = Form("pixel"), hd_size: int = Form(768)):
    return _do_reference(Image.open(ref.file), Image.open(pose_img.file).convert("RGB") if pose_img is not None else None,
                         dict(pose=pose, character=character, negative=negative, checkpoint=checkpoint, lora=lora, lora_weight=lora_weight,
                              steps=steps, cfg=cfg, seed=seed, bg=bg, ip_scale=ip_scale, n=n, colors=colors, lock_palette=lock_palette,
                              match_size=match_size, bg_tol=bg_tol, cn_scale=cn_scale, canvas=canvas, remove_shadow=remove_shadow,
                              gen_size=gen_size, crisp=crisp, clean=clean, outline=outline, sampler=sampler,
                              art_style=art_style, hd_size=hd_size))


REF_DEFAULTS = dict(pose="", character="", negative="", checkpoint="", lora="", lora_weight=1.0, steps=25, cfg=7.0, seed=-1, bg="white",
                    ip_scale=0.7, n=1, colors=16, lock_palette=True, match_size=True, bg_tol=40, cn_scale=0.8, canvas=128,
                    remove_shadow=True, gen_size=768, crisp=True, clean=True, outline="none", sampler="euler_a", art_style="pixel", hd_size=768)


def _coerce_ref(f):
    """Queued jobs carry plain JSON: make every field the type the pipeline expects (numbers sent as text, 'true'/'false' strings)."""
    out = {}
    for k, d in REF_DEFAULTS.items():
        v = f.get(k, d)
        try:
            if isinstance(d, bool):
                v = v if isinstance(v, bool) else str(v).strip().lower() in ("1", "true", "yes", "on")
            elif isinstance(d, (int, float)):
                v = type(d)(float(v))
            else:
                v = str(v)
        except (TypeError, ValueError):
            raise HTTPException(400, f"bad value for '{k}': {v!r}")
        out[k] = v
    return out


def _do_reference(ref_img, control, f):
    """Reference-pose generation: ref_img = reference sprite (PIL), control = OpenPose render (PIL RGB) or None, f = field dict."""
    f = _coerce_ref(f)
    (pose, character, negative, checkpoint, lora, lora_weight, steps, cfg, seed, bg, ip_scale, n, colors, lock_palette, match_size,
     bg_tol, cn_scale, canvas, remove_shadow, gen_size, crisp, clean, outline, sampler, art_style, hd_size) = [f[k] for k in REF_DEFAULTS]
    art_style = _art_style(art_style)
    ckpt, lora_dir = _paths(checkpoint)
    gen.set_sampler(sampler)
    q = dict(remove_shadow=remove_shadow, crisp=crisp, clean=clean, outline=_outline(outline))
    ref_sprite = px.crop_to_content(px.remove_bg(ref_img, bg_tol))
    pal = px.palette_from_sprite(ref_sprite) if lock_palette and art_style == "pixel" else None  # None if ref isn't a real low-colour sprite
    from . import local_runtime as lr
    if lr.route(ckpt) and control is not None:
        raise HTTPException(400,"This local model supports image references but not SDXL skeleton ControlNet; turn off Use skeleton pose")
    ip_img = ref_sprite if lr.route(ckpt) else gen.prep_reference(ref_sprite, bg)
    prompt = ", ".join(s for s in (character.strip(), pose.strip()) if s)
    pal_arg = pal if pal is not None else "none"
    if art_style != "pixel":
        post = lambda raw: styles.finish(raw, hd_size, True, bg_tol)
    elif control is not None:  # skeleton mode: fixed canvas, fixed scale, every frame lines up
        post = lambda raw: px.pixelize(raw, "canvas", canvas, colors, pal_arg, True, bg_tol, **q)
    else:
        size = max(ref_sprite.size) if match_size and max(ref_sprite.size) <= 160 else 64
        post = lambda raw: px.pixelize(raw, "fixed", size, colors, pal_arg, True, bg_tol, **q)
    return _run(ckpt, lora_dir, lora, lora_weight, prompt, negative, steps, cfg, seed, bg, max(1, min(n, 6)),
                ip_img, ip_scale, post, control, cn_scale, str(Path(cfg_dir()) / "controlnet"),
                max(512, min(gen_size, 1024)) // 64 * 64, art_style=art_style)


# ---------------- rig animation ----------------
def _sprite(f):
    return Image.open(f.file).convert("RGBA")


def _joints(s):
    j = json.loads(s)
    missing = [n for n in rig.JOINTS if n not in j]
    if missing:
        raise HTTPException(400, f"missing joints: {missing}")
    return {n: [float(j[n][0]), float(j[n][1])] for n in rig.JOINTS}


@app.post("/api/rig/autoplace")
def rig_autoplace(sprite: UploadFile = File(...)):
    img = _sprite(sprite)
    try:
        return {"joints": rig.autoplace(img), "size": img.size, "bones": rig.BONE_NAMES}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/rig/parts")
def rig_parts(sprite: UploadFile = File(...), joints: str = Form(...), overrides: str = Form("[]")):
    lab = rig.assign_parts(_sprite(sprite), _joints(joints), json.loads(overrides))
    return {"overlay": b64(rig.overlay_image(lab))}


def _secondary(v):
    """Secondary-motion settings from the UI (dict or JSON text) -> a safe dict, or None when off."""
    try:
        s = json.loads(v) if isinstance(v, str) and v.strip() else (v if isinstance(v, dict) else None)
    except Exception:
        raise HTTPException(400, "bad secondary motion settings")
    if not s or not s.get("enabled", True):
        return None
    clip = lambda x, lo, hi, d: max(lo, min(float(x if x is not None else d), hi))
    parts = {}
    for name in ("cape", "hair", "tail"):
        p = (s.get("parts") or {}).get(name) or {}
        parts[name] = {"segments": int(clip(p.get("segments"), 1, 6, rig.SEC_DEFAULTS[name]["segments"])), "front": bool(p.get("front", False))}
    return {"enabled": True, "flutter": clip(s.get("flutter"), 0, 2, 1), "stiffness": clip(s.get("stiffness"), .4, 2, 1),
            "damping": clip(s.get("damping"), .1, .9, .35), "parts": parts}


_RCACHE = {}


@app.post("/api/rig/animate")
def rig_animate(sprite: UploadFile = File(...), joints: str = Form(...), overrides: str = Form("[]"),
                anim: str = Form("walk"), frames: int = Form(8), fps: int = Form(10), facing: str = Form("right"),
                near: str = Form("r"), weapon: str = Form("r"), amp: float = Form(1.0), pad: int = Form(0),
                overlap: int = Form(1), ss: int = Form(4), export: bool = Form(False), name: str = Form("sprite"),
                refine: bool = Form(False), checkpoint: str = Form(""), lora: str = Form(""),
                lora_weight: float = Form(1.0), character: str = Form(""), negative: str = Form(""),
                strength: float = Form(0.45), steps: int = Form(22), cfg: float = Form(7.0), seed: int = Form(-1),
                radius: float = Form(0), sampler: str = Form("euler_a"), secondary: str = Form(""), keyframes: str = Form("[]"), softness: float = Form(0.0)):
    if anim not in rig.CLIPS and anim != "custom":
        raise HTTPException(400, f"unknown animation: {anim}")
    frames, fps = max(1, min(frames, 32)), max(1, min(fps, 60))
    sp, jn, ov = _sprite(sprite), _joints(joints), json.loads(overrides)
    if rig.is_hd(sp) and refine:
        raise HTTPException(400, "AI joint cleanup is pixel-only; disable it for HD animation")
    try:
        keys = json.loads(keyframes) if anim == "custom" else None
        if anim == "custom": rig.custom_keys(keys)
    except (ValueError, TypeError) as e:
        raise HTTPException(400, str(e))
    sec = _secondary(secondary)
    args = (anim, frames, facing, near, weapon, amp, max(0, min(pad, 200)), max(0, min(overlap, 3)), max(1, min(ss, 6)))
    params = [args, checkpoint, lora, lora_weight, character, negative, strength, steps, cfg, seed, radius, jn, ov, sampler, sec, keys, softness]
    key = hashlib.sha1(sp.tobytes() + json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()
    info = {}
    if refine and key in _RCACHE:  # e.g. same settings again: don't pay for the AI pass twice
        e = _RCACHE[key]
        raw, imgs, meta, info = e["raw"], e["imgs"], e["meta"], e["info"]
    else:
        try:
            raw, meta = rig.render(sp, jn, ov, *args, secondary=sec, keyframes=keys, softness=softness)
        except ValueError as e:
            raise HTTPException(400, str(e))
        imgs = raw
        if refine:
            ckpt, lora_dir = _paths(checkpoint)
            gen.set_sampler(sampler)
            if meta["size"][0] > 256 or meta["size"][1] > 256:
                raise HTTPException(400, "frames are larger than 256 px: AI cleanup needs a smaller sprite or less padding")
            try:
                imgs, info = refiner.refine(raw, meta, sp, ckpt, lora, lora_weight, lora_dir, character, negative,
                                            max(0.1, min(strength, 0.9)), max(8, min(steps, 50)), cfg, seed, radius)
            except HTTPException:
                raise
            except Exception as e:
                hint = " - out of GPU memory: close other GPU apps and retry" if "out of memory" in str(e).lower() else ""
                raise HTTPException(500, f"{type(e).__name__}: {e}{hint}")
            _RCACHE[key] = {"raw": raw, "imgs": imgs, "meta": meta, "info": info,
                            "cfg": {"sprite": sp, "ckpt": ckpt, "lora": lora, "lora_w": lora_weight, "lora_dir": lora_dir,
                                    "character": character, "negative": negative, "steps": max(8, min(steps, 50)),
                                    "cfg": cfg, "radius": radius}}
            while len(_RCACHE) > 3:
                _RCACHE.pop(next(iter(_RCACHE)))
    out = {"frames": [b64(f) for f in imgs], "fps": fps, "size": meta["size"], "pivot": meta["pivot"]}
    if refine:
        out["raw_frames"] = [b64(f) for f in raw]
        out["refine"] = info
        out["key"] = key
        out["accept"] = [i not in set(info.get("reverted_idx", [])) for i in range(len(imgs))]
    if export:
        try:
            out["saved_to"] = rig.export(imgs, meta, fps, anim, name, ROOT)
        except ValueError as e:
            raise HTTPException(400, str(e))
    return out


class RedoBody(BaseModel):
    key: str
    frames: List[int]
    seed: int = -1
    strength: float = 0.45


@app.post("/api/rig/redo")
def rig_redo(b: RedoBody):
    e = _RCACHE.get(b.key)
    if not e:
        raise HTTPException(400, "cleanup result expired (server restarted?): press Preview again")
    idx = sorted({i for i in b.frames if 0 <= i < len(e["imgs"])})
    if not idx:
        raise HTTPException(400, "no frames selected")
    try:
        imgs, info = refiner.redo_frames(e, idx, b.seed, max(0.1, min(b.strength, 0.9)))
    except Exception as ex:
        hint = " - out of GPU memory: close other GPU apps and retry" if "out of memory" in str(ex).lower() else ""
        raise HTTPException(500, f"{type(ex).__name__}: {ex}{hint}")
    return {"frames": [b64(f) for f in imgs], "redone": idx, "refine": info,
            "accept": [i not in set(info["reverted_idx"]) for i in range(len(imgs))]}


class ReferenceFrames(BaseModel):
    start: str
    end: str
    count: int = 8
    fps: int = 10
    method: str = "ai"
    prompt: str = ""
    negative: str = ""
    checkpoint: str = ""
    lora: str = ""
    lora_weight: float = 1.0
    art_style: str = "pixel"
    steps: int = 25
    cfg: float = 7.0
    strength: float = .65
    seed: int = -1
    sampler: str = "euler_a"


@app.post("/api/rig/reference_frames")
def rig_reference_frames(b: ReferenceFrames):
    try:
        start,end=_dec_img(b.start),_dec_img(b.end)
        inbetween.validate(start,end,b.count)
    except Exception as e:
        raise HTTPException(400,str(e))
    if b.method not in ("ai","blend"):
        raise HTTPException(400,"Unknown in-between method")
    style=_art_style(b.art_style)
    seed=b.seed if b.seed>=0 else int(np.random.randint(0,2**31-1))
    redraw=None
    if b.method=="ai" and b.count>2:
        ckpt,lora_dir=_paths(b.checkpoint)
        if mf.identify(ckpt) not in ("sdxl","unknown"):
            raise HTTPException(400,"AI endpoint in-betweens currently require SDXL inpainting; crossfade is model independent")
        gen.set_sampler(b.sampler)
        def redraw(guide,t,i):
            def run(image,mask,ref):
                prompt=f"{b.prompt}, intermediate animation pose, {round(t*100)} percent through motion, consistent character and costume, single coherent pose, no ghosting"
                return gen.inpaint(ckpt,b.lora,b.lora_weight,lora_dir,prompt,b.negative,image,mask,
                                   strength=max(.15,min(.85,b.strength)),steps=max(12,min(50,b.steps)),cfg=b.cfg,
                                   seed=seed,bg="magenta",ip_image=ref,ip_scale=.7,art_style=style)
            return inbetween.ai_frame(guide,start,end,t,run,style)
    try:
        imgs=inbetween.frames(start,end,b.count,redraw)
    except Exception as e:
        raise HTTPException(500,f"{type(e).__name__}: {e}")
    return {"frames":[b64(im) for im in imgs],"fps":max(1,min(60,b.fps)),"size":list(start.size),
            "pivot":[start.width/2,start.height-1],"info":{"method":b.method,"seed":seed,"endpoints_locked":True}}


class ReferenceExport(BaseModel):
    frames: List[str]
    fps: int = 10
    name: str = "sprite"
    options: dict = {}


@app.post("/api/rig/reference_export")
def rig_reference_export(b: ReferenceExport):
    try:
        if not 2<=len(b.frames)<=32:
            raise ValueError("Need 2-32 frames")
        imgs=[_dec_img(u) for u in b.frames]
        inbetween.validate(imgs[0],imgs[-1],len(imgs))
        if any(im.size!=imgs[0].size for im in imgs):
            raise ValueError("Frames must share canvas dimensions")
        w,h=imgs[0].size
        opts=dict(b.options,crop=False,uniform=True,frames=True,smooth=rig.is_hd(imgs[0]))
        return exporter.export_pack([{"name":"reference","fps":max(1,min(60,b.fps)),"loop":False,
                                     "frames":imgs,"pivot":(w/2,h-1)}],opts,b.name,ROOT)
    except ValueError as e:
        raise HTTPException(400,str(e))
    except Exception as e:
        raise HTTPException(500,f"{type(e).__name__}: {e}")


class ExportBody(BaseModel):
    frames: List[str]
    fps: int = 10
    anim: str = "anim"
    name: str = "sprite"
    pivot: List[float] = [0, 0]


@app.post("/api/rig/export_frames")
def rig_export_frames(b: ExportBody):
    """Export exactly the frames the user chose (e.g. AI where it helped, rig-only where it didn't)."""
    if not 1 <= len(b.frames) <= 64:
        raise HTTPException(400, "need 1-64 frames")
    try:
        imgs = [Image.open(io.BytesIO(base64.b64decode(u.split(",", 1)[1]))).convert("RGBA") for u in b.frames]
    except Exception:
        raise HTTPException(400, "bad frame data")
    if len({im.size for im in imgs}) != 1 or max(imgs[0].size) > 512:
        raise HTTPException(400, "frames must share one size (max 512 px)")
    fps = max(1, min(b.fps, 60))
    return {"saved_to": rig.export(imgs, {"pivot": (b.pivot + [0, 0])[:2]}, fps, b.anim, b.name, ROOT)}


class PackAnim(BaseModel):
    anim: str
    softness: float = 0
    keyframes: Optional[List[dict]] = None
    count: int = 8
    fps: int = 10
    facing: str = "right"
    near: str = "r"
    weapon: str = "r"
    amp: float = 1.0
    pad: int = 0
    overlap: int = 1
    frames: Optional[List[str]] = None   # ready-made frames (e.g. AI-cleaned, with your accept/reject applied)
    pivot: Optional[List[float]] = None


class PackBody(BaseModel):
    secondary: Optional[dict] = None
    sprite: str
    joints: dict
    overrides: list = []
    name: str = "sprite"
    options: dict = {}
    anims: List[PackAnim]


def _dec_img(u):
    return Image.open(io.BytesIO(base64.b64decode(u.split(",", 1)[1]))).convert("RGBA")


@app.post("/api/rig/export_pack")
def rig_export_pack(b: PackBody):
    """One sprite sheet + atlas (+ Godot / Unity files) for one or many clips, sharing a feet pivot."""
    if not 1 <= len(b.anims) <= len(rig.CLIPS) + 1:
        raise HTTPException(400, "pick 1-%d animations" % len(rig.CLIPS))
    try:
        sp, jn = _dec_img(b.sprite), _joints(json.dumps(b.joints))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "bad sprite data")
    entries, seen = [], set()
    pixel_budget = 0
    for a in b.anims:
        if (a.anim not in rig.CLIPS and a.anim != "custom") or a.anim in seen:
            raise HTTPException(400, f"unknown or duplicate animation: {a.anim}")
        seen.add(a.anim)
        fps = max(1, min(a.fps, 60))
        frames = pivot = None
        if a.frames and a.pivot and len(a.pivot) >= 2:
            try:
                frames = [_dec_img(u) for u in a.frames[:64]]
            except Exception:
                raise HTTPException(400, f"bad frame data for {a.anim}")
            if len({f.size for f in frames}) != 1 or max(frames[0].size) > 1024:
                raise HTTPException(400, f"frames of {a.anim} must share one size (max 1024 px)")
            pivot = (a.pivot[0], a.pivot[1])
        else:
            count = max(1, min(a.count, 32))
            pad = max(0, min(a.pad, 200)) or round(rig.CLIP_PAD.get(a.anim, .25) * max(sp.size))
            if rig.is_hd(sp) and pixel_budget + (sp.width + 2 * pad) * (sp.height + 2 * pad) * count > 48_000_000:
                raise HTTPException(400, 'HD pack exceeds pixel budget; export fewer clips or frames')
            try:
                frames, meta = rig.render(sp, jn, b.overrides, a.anim, count, a.facing, a.near, a.weapon,
                                          a.amp, max(0, min(a.pad, 200)), max(0, min(a.overlap, 3)), 4, secondary=_secondary(b.secondary), keyframes=a.keyframes, softness=a.softness)
            except ValueError as e:
                raise HTTPException(400, str(e))
            pivot = tuple(meta["pivot"])
        pixel_budget += sum(im.width * im.height for im in frames)
        if rig.is_hd(sp) and pixel_budget > 48_000_000:
            raise HTTPException(400, "HD pack exceeds pixel budget; export fewer clips or frames")
        entries.append({"name": a.anim, "fps": fps, "loop": a.anim not in rig.ONE_SHOT, "frames": frames, "pivot": pivot})
    if sum(len(e["frames"]) for e in entries) > 400:
        raise HTTPException(400, "too many frames (max 400)")
    try:
        options = dict(b.options, smooth=rig.is_hd(sp))
        return exporter.export_pack(entries, options, b.name, ROOT)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")


# ---------------- palette tools ----------------
def _pal(fn, *a, **k):
    try:
        return fn(*a, **k)
    except palettes.PaletteError as e:
        raise HTTPException(400, str(e))


def _pimg(f):
    try:
        im = Image.open(f.file).convert("RGBA")
    except Exception:
        raise HTTPException(400, "could not read the image")
    if max(im.size) > 1024:
        raise HTTPException(400, "image is larger than 1024 px")
    return im


def _plist(s):
    try:
        return [palettes.from_hex(c) if isinstance(c, str) else c for c in json.loads(s)]
    except Exception:
        raise HTTPException(400, "bad colour list")


@app.get("/api/palettes")
def pal_list():
    out = [{"name": n, "builtin": True, "colors": [palettes.to_hex(c) for c in px.PALETTES[n]]} for n in px.BUILTIN_PALETTES]
    return {"palettes": out + [dict(p, builtin=False) for p in palettes.list_user(ROOT)]}


@app.post("/api/palettes/parse")
def pal_parse(file: UploadFile = File(...)):
    return _pal(palettes.parse_any, file.filename, file.file.read(5_000_000))


class PalSave(BaseModel):
    name: str
    colors: List[str]


@app.post("/api/palettes/save")
def pal_save(b: PalSave):
    return {"name": _pal(palettes.save_user, ROOT, b.name, b.colors)}


@app.delete("/api/palettes/{name}")
def pal_delete(name: str):
    _pal(palettes.delete_user, ROOT, name)
    return {"ok": True}


@app.post("/api/palettes/export")
def pal_export(b: PalSave):
    return _pal(palettes.export_files, ROOT, b.name, b.colors)


class PalSort(BaseModel):
    colors: List[str]
    key: str = "lightness"


@app.post("/api/palettes/sort")
def pal_sort(b: PalSort):
    return {"colors": _pal(palettes.sort_colors, b.colors, b.key if b.key in ("lightness", "hue") else "lightness")}


class PalRamp(BaseModel):
    color: str
    n: int = 5


@app.post("/api/palettes/ramp")
def pal_ramp(b: PalRamp):
    return {"colors": _pal(lambda: palettes.ramp(palettes.from_hex(b.color), b.n))}


@app.post("/api/palettes/extract")
def pal_extract(file: UploadFile = File(...), n: int = Form(0)):
    return palettes.extract(_pimg(file), max(0, min(n, 256)))


@app.post("/api/palettes/remap")
def pal_remap(file: UploadFile = File(...), palette: str = Form(...), dither: str = Form("none"), strength: float = Form(0.6)):
    cols = _plist(palette)
    if not 1 <= len(cols) <= 256:
        raise HTTPException(400, "the working palette needs 1-256 colours")
    img = _pimg(file)
    out, note = palettes.remap(img, cols, dither if dither in ("none", "bayer2", "bayer4", "floyd") else "none", strength)
    return {"image": b64(out), "size": list(out.size), "note": note}


@app.post("/api/palettes/merge")
def pal_merge(file: UploadFile = File(...), delta: float = Form(0.05)):
    out, pal = palettes.merge_similar(_pimg(file), max(0.005, min(delta, 0.3)))
    return {"image": b64(out), "size": list(out.size), "palette": pal}


@app.post("/api/palettes/variants")
def pal_variants(file: UploadFile = File(...), shifts: str = Form(...), protect: str = Form("[]"), chroma: float = Form(1.0),
                 keep_dark: bool = Form(True)):
    try:
        sh = [float(s) for s in json.loads(shifts)][:12]
    except Exception:
        raise HTTPException(400, "bad shift list")
    img = _pimg(file)
    res = palettes.variants(img, sh, _plist(protect), max(0.0, min(chroma, 2.0)), keep_dark)
    return {"variants": [{"shift": v["shift"], "image": b64(v["image"]), "size": list(v["image"].size), "palette": v["palette"]} for v in res]}


# ---------------- sprite templates ----------------
@app.get("/api/template/dummy")
def template_dummy(height: int = 64, style: str = "normal", view: str = "front"):
    img, joints, ov = templates.make_dummy(height, style if style in templates.STYLES else "normal", view if view in ("front", "side") else "front")
    return {"sprite": b64(img), "joints": joints, "overrides": ov, "size": list(img.size)}


@app.post("/api/template/generate")
def template_generate(template: UploadFile = File(...), ref: Optional[UploadFile] = File(None), prompt: str = Form(""),
                      negative: str = Form(""), checkpoint: str = Form(...), lora: str = Form(""), lora_weight: float = Form(1.0),
                      steps: int = Form(25), cfg: float = Form(7.0), seed: int = Form(-1), n: int = Form(2),
                      freedom: int = Form(2), strength: float = Form(0.85), ip_scale: float = Form(0.8), colors: int = Form(20),
                      palette_src: str = Form("reference"), clean: bool = Form(True), sampler: str = Form("euler_a"),
                      bg_tol: int = Form(40)):
    ckpt, lora_dir = _paths(checkpoint)
    gen.set_sampler(sampler)
    try:
        tpl = Image.open(template.file).convert("RGBA")
        refimg = Image.open(ref.file) if ref is not None else None
        if refimg is not None:
            refimg.load()
    except Exception:
        raise HTTPException(400, "could not read the template or reference image")
    try:
        res = templates.generate_from_template(tpl, refimg, prompt, negative, ckpt, lora, lora_weight, lora_dir,
                                               max(.3, min(strength, 1.0)), max(8, min(steps, 50)), cfg, seed, max(1, min(n, 4)),
                                               freedom, max(0.0, min(ip_scale, 1.0)), max(4, min(colors, 64)),
                                               palette_src if palette_src in ("reference", "result") else "reference", clean,
                                               bg_tol=bg_tol)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        hint = " - out of GPU memory: close other GPU apps and retry" if "out of memory" in str(e).lower() else ""
        raise HTTPException(500, f"{type(e).__name__}: {e}{hint}")
    return {"results": [{"raw": b64(r["raw"].resize((384, 384))), "sprite": b64(r["sprite"]), "info": r["info"]} for r in res]}


# ---------------- 4 / 8 direction characters ----------------
def _dirs_valid(dirs):
    dirs = list(dict.fromkeys(dirs or []))
    if not dirs or any(d not in directions.DIRS8 for d in dirs):
        raise HTTPException(400, "pick directions from: " + ", ".join(directions.DIRS8))
    return dirs


def _dir_slots(slots, dirs):
    try:
        need = directions.needed(dirs)
    except directions.DirectionError as e:
        raise HTTPException(400, str(e))
    out = {}
    for u in need:  # west / south-west / north-west reuse the east / south-east / north-east views
        s = (slots or {}).get(u)
        if not s or not s.get("sprite"):
            raise HTTPException(400, f"the {u} view has no sprite yet")
        try:
            img = _dec_img(s["sprite"])
        except Exception:
            raise HTTPException(400, f"bad image for the {u} view")
        if max(img.size) > 256:
            raise HTTPException(400, f"the {u} view is larger than 256 px")
        jn = _joints(json.dumps(s["joints"])) if s.get("joints") else rig.autoplace(img)  # no rig yet: guess one
        out[u] = {"sprite": img, "joints": jn, "ovr": s.get("overrides") or []}
    return out


def _dir_clip(c):
    if c.anim not in rig.CLIPS:
        raise HTTPException(400, f"unknown animation: {c.anim}")
    return {"anim": c.anim, "count": max(1, min(c.count, 32)), "fps": max(1, min(c.fps, 60)), "amp": max(.3, min(c.amp, 2.0)),
            "softness": max(0, min(c.softness, 100)), "pad": max(0, min(c.pad, 200)), "overlap": max(0, min(c.overlap, 3)), "weapon": c.weapon if c.weapon in ("l", "r") else "r"}


class DirClip(BaseModel):
    anim: str
    softness: float = 0
    count: int = 8
    fps: int = 10
    amp: float = 1.0
    pad: int = 0
    overlap: int = 1
    weapon: str = "r"


class DirRender(BaseModel):
    slots: dict
    clip: DirClip
    dirs: List[str]
    secondary: Optional[dict] = None


@app.post("/api/dirs/render")
def dirs_render(b: DirRender):
    """Preview: one clip for every direction (west / south-west / north-west are mirrors of their east views)."""
    dirs = _dirs_valid(b.dirs)
    slots, clip = _dir_slots(b.slots, dirs), _dir_clip(b.clip)
    try:
        res = directions.render_directions(slots, [clip], dirs, _secondary(b.secondary))
    except directions.DirectionError as e:
        raise HTTPException(400, str(e))
    return {"fps": clip["fps"], "dirs": {d: {"frames": [b64(f) for f in res[(clip["anim"], d)][0]],
                                             "size": list(res[(clip["anim"], d)][1]["size"])} for d in dirs}}


class DirBody(BaseModel):
    slots: dict
    clips: List[DirClip]
    dirs: List[str]
    order: str = "cw8"
    name: str = "character"
    options: dict = {}
    secondary: Optional[dict] = None


@app.post("/api/dirs/export")
def dirs_export(b: DirBody):
    dirs = _dirs_valid(b.dirs)
    if not 1 <= len(b.clips) <= len(rig.CLIPS):
        raise HTTPException(400, "pick 1-%d animations" % len(rig.CLIPS))
    slots, clips = _dir_slots(b.slots, dirs), [_dir_clip(c) for c in b.clips]
    if len({c["anim"] for c in clips}) != len(clips):
        raise HTTPException(400, "duplicate animations")
    try:
        return directions.export_directions(slots, clips, dirs, b.order if b.order in directions.ORDERS else "cw8", b.options,
                                            b.name, _secondary(b.secondary), ROOT)
    except directions.DirectionError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")


@app.post("/api/dirs/generate")
def dirs_generate(ref: Optional[UploadFile] = File(None), dirs: str = Form(...), height: int = Form(64), style: str = Form("normal"),
                  prompt: str = Form(""), negative: str = Form(""), checkpoint: str = Form(...), lora: str = Form(""),
                  lora_weight: float = Form(1.0), steps: int = Form(25), cfg: float = Form(7.0), seed: int = Form(-1),
                  strength: float = Form(0.85), ip_scale: float = Form(0.8), freedom: int = Form(2), colors: int = Form(20),
                  palette_src: str = Form("reference"), clean: bool = Form(True), sampler: str = Form("euler_a"), bg_tol: int = Form(40)):
    """Generate the needed views from view-specific dummies with ONE reference, seed and palette, so they match each other."""
    ckpt, lora_dir = _paths(checkpoint)
    gen.set_sampler(sampler)
    try:
        need = directions.needed(json.loads(dirs))
        refimg = Image.open(ref.file) if ref is not None else None
        if refimg is not None:
            refimg.load()
    except directions.DirectionError as e:
        raise HTTPException(400, str(e))
    except Exception:
        raise HTTPException(400, "bad directions list or reference image")
    if not need:
        raise HTTPException(400, "pick at least one direction")
    import numpy as np
    base = seed if seed >= 0 else int(np.random.randint(0, 2**31 - 1))
    results, err, shared = [], None, None
    for d in need:
        img, joints, ov = templates.make_dummy(height, style if style in templates.STYLES else "normal", directions.DUMMY_VIEW[d])
        try:
            r = templates.generate_from_template(img, refimg, ", ".join(x for x in (prompt.strip(), directions.HINT[d]) if x), negative, ckpt,
                                                 lora, lora_weight, lora_dir, max(.3, min(strength, 1.0)), max(8, min(steps, 50)), cfg,
                                                 base, 1, freedom, max(0.0, min(ip_scale, 1.0)), max(4, min(colors, 64)),
                                                 palette_src if palette_src in ("reference", "result") else "reference", clean,
                                                 bg_tol=bg_tol, palette=shared)[0]
        except Exception as e:
            hint = " - out of GPU memory: close other GPU apps and retry" if "out of memory" in str(e).lower() else ""
            err = f"{d} view: {type(e).__name__}: {e}{hint}"
            if not results:
                raise HTTPException(400 if isinstance(e, ValueError) else 500, err)
            break
        if shared is None and (refimg is None or palette_src == "result"):  # no reference palette to share: reuse the first view's
            a = np.asarray(r["sprite"])
            shared = np.unique(a[..., :3][a[..., 3] > 0], axis=0)
        results.append({"dir": d, "sprite": b64(r["sprite"]), "raw": b64(r["raw"].resize((256, 256))), "joints": joints,
                        "overrides": ov, "info": r["info"]})
    return {"results": results, "seed": base, "error": err}


class CharacterView(BaseModel):
    reference: str
    view: str
    locks: Optional[List[str]] = None
    description: str = ""
    checkpoint: str
    lora: str = ""
    lora_weight: float = 1.0
    art_style: str = "anime"
    size: int = 256
    gen_size: int = 768
    steps: int = 20
    cfg: float = 4.0
    seed: int = -1
    sampler: str = "euler_a"
    negative: str = ""
    bg: str = "white"
    ip_scale: float = .7
    colors: int = 24
    lock_palette: bool = True
    bg_tol: int = 40


@app.post("/api/character/view")
def character_view(b: CharacterView):
    """Generate one view from the same master image; no mutation of existing views."""
    from . import local_runtime as lr
    ckpt,lora_dir=_paths(b.checkpoint)
    art=_art_style(b.art_style)
    try:
        if not mf.describe(ckpt)["reference"]: raise ValueError("Select a model with image-reference support")
        if art=="pixel" and b.size not in (32,48,64,96,128): raise ValueError("Choose a pixel canvas of 32–128 px")
        if art!="pixel" and b.size!=256: raise ValueError("HD direction canvas is limited to 256 px")
        anchor=character.decode_reference(b.reference)
        if anchor.getchannel("A").getextrema()[0]<255: anchor=character.content(anchor)
        prompt=character.view_prompt(b.view,b.description,b.locks)
        if len(b.negative)>1800: raise ValueError("Negative prompt too long")
        ref=anchor if lr.route(ckpt) else gen.prep_reference(anchor,b.bg)
        seed=b.seed if b.seed>=0 else int(np.random.randint(0,2**31-1))
        gen.set_sampler(b.sampler)
        neg=", ".join(x for x in (b.negative,"multiple characters, duplicate views, text, cropped feet, scenery") if x)
        result=_run(ckpt,lora_dir,b.lora,b.lora_weight,prompt,neg,max(1,min(b.steps,50)),b.cfg,seed,b.bg,1,
                    ref,max(0.,min(b.ip_scale,1.)),lambda raw:character.finish(raw,anchor,art,b.size,b.colors,b.lock_palette,b.bg_tol),
                    gen_size=max(512,min(b.gen_size,1024))//64*64,art_style=art)["results"][0]
        sprite=_dec_img(result["sprite"])
        return {**result,"dir":b.view,"seed":seed,"joints":rig.autoplace(sprite),"overrides":[]}
    except ValueError as e: raise HTTPException(400,str(e))


class CharacterVariation(CharacterView):
    view: str = "S"  # variation does not force a camera angle
    target: str = "outfit"
    change: str
    lock_palette: bool = False


@app.post("/api/character/variation")
def character_variation(b: CharacterVariation):
    """Generate an independent candidate from the immutable master."""
    from . import local_runtime as lr
    ckpt,lora_dir=_paths(b.checkpoint)
    art=_art_style(b.art_style)
    try:
        if not mf.describe(ckpt)["reference"]: raise ValueError("Select a model with image-reference support")
        if b.size not in ((32,48,64,96,128) if art=="pixel" else (256,512,768,1024)):
            raise ValueError("Unsupported output size")
        prompt,locks=character.variation_prompt(b.description,b.target,b.change,b.locks)
        if len(b.negative)>1800: raise ValueError("Negative prompt too long")
        anchor=character.decode_reference(b.reference)
        if anchor.getchannel("A").getextrema()[0]<255: anchor=character.content(anchor)
        ref=anchor if lr.route(ckpt) else gen.prep_reference(anchor,b.bg)
        seed=b.seed if b.seed>=0 else int(np.random.randint(0,2**31-1))
        gen.set_sampler(b.sampler)
        # Do not force the old low-colour palette when the selected change can introduce new colours.
        palette_safe=b.lock_palette and b.target in ("pose","expression")
        neg=", ".join(x for x in (b.negative,"multiple characters, duplicate figures, text, cropped feet, scenery") if x)
        result=_run(ckpt,lora_dir,b.lora,b.lora_weight,prompt,neg,max(1,min(b.steps,50)),b.cfg,seed,b.bg,1,
                    ref,max(0.,min(b.ip_scale,1.)),lambda raw:character.finish_variation(raw,anchor,art,b.size,b.colors,palette_safe,b.bg_tol),
                    gen_size=max(512,min(b.gen_size,1024))//64*64,art_style=art)["results"][0]
        result["info"].update(target=b.target,change=b.change,locks=locks,checkpoint=b.checkpoint,
                              reference_method=lr.route(ckpt) or "sdxl_ip_adapter",lock_mode="reference_guidance")
        return result
    except ValueError as e: raise HTTPException(400,str(e))


class ModularAsset(BaseModel):
    recipe: dict
    category: str
    description: str
    view: str = "front"
    source: str = "body"
    replace_category: bool = True
    checkpoint: str
    lora: str = ""
    lora_weight: float = 1.0
    art_style: str = "anime"
    gen_size: int = 768
    steps: int = 20
    cfg: float = 4.0
    seed: int = -1
    sampler: str = "euler_a"
    negative: str = ""
    bg: str = "magenta"
    ip_scale: float = .4
    colors: int = 24
    bg_tol: int = 40


@app.post("/api/modular/generate_asset")
def modular_generate_asset(b: ModularAsset):
    """One isolated asset, fitted to the body; never mutates a project or recipe."""
    from . import local_runtime as lr
    ckpt,lora_dir=_paths(b.checkpoint)
    try:
        if not mf.describe(ckpt)["reference"]:raise ValueError("Select an image-reference-capable checkpoint")
        prompt=modular_assets.prompt(b.category,b.description,b.view)
        if b.bg not in ("white","green","magenta"):raise ValueError("Choose white, green or magenta background")
        if len(b.negative)>1800:raise ValueError("Negative prompt too long")
        recipe,images,ref,bb=modular_assets.reference(b.recipe,b.source)
        if len(recipe["layers"])>=modular.MAX_LAYERS:raise ValueError("Remove a layer before generating another")
        art="pixel" if recipe["pixel"] else _art_style(b.art_style if b.art_style!="pixel" else "anime")
        rect=modular_assets.region(b.category,bb,(recipe["width"],recipe["height"]))
        # A square RGB reference preserves the full character silhouette for all three runtimes.
        ref=gen.prep_reference(ref,b.bg,canvas=512)
        seed=b.seed if b.seed>=0 else int(np.random.randint(0,2**31-1))
        gen.set_sampler(b.sampler)
        res=_run(ckpt,lora_dir,b.lora,b.lora_weight,prompt,b.negative,max(1,min(b.steps,50)),b.cfg,seed,b.bg,1,
                 ref,max(.2,min(b.ip_scale,.8)),lambda raw:modular_assets.finish(raw,rect,recipe["pixel"],b.colors,b.bg_tol),
                 gen_size=max(512,min(b.gen_size,1024))//64*64,kind="modular_asset",art_style=art)["results"][0]
        info=res["info"]
        layer={"name":b.description.strip()[:80],"category":b.category,"image":res["sprite"],
               "x":info["x"],"y":info["y"],"scale":100,"opacity":100,"visible":True,"flip":False}
        # Validate the resulting recipe budget before presenting an addable candidate.
        modular.validate({**recipe,"layers":recipe["layers"]+[layer]})
        preview=modular_assets.candidate_preview(recipe,images,layer,b.replace_category)
        info.update(category=b.category,checkpoint=b.checkpoint,reference_method=lr.route(ckpt) or "sdxl_ip_adapter")
        return {"layer":layer,"preview":modular.png_uri(preview),"reference":modular.png_uri(ref),"raw":res["raw"],"info":info}
    except ValueError as e:raise HTTPException(400,str(e))


class ModularAnimation(BaseModel):
    recipe: dict
    anim: str = "walk"
    count: int = 8
    fps: int = 10
    facing: str = "right"
    near: str = "r"
    weapon: str = "r"
    amp: float = 1.0
    pad: int = 0
    softness: float = 0
    name: str = "modular_character"
    options: dict = {}


@app.get("/api/custom_skeleton/preset")
def custom_skeleton_preset(kind: str="humanoid"):
    try:return custom_skeleton.preset(kind)
    except ValueError as e:raise HTTPException(400,str(e))


@app.post("/api/custom_skeleton/validate")
def custom_skeleton_validate(body: dict=Body(...)):
    try:return custom_skeleton.validate(body)
    except ValueError as e:raise HTTPException(400,str(e))


@app.post("/api/custom_skeleton/weights")
def custom_skeleton_weights(body: dict=Body(...)):
    try:
        from . import custom_skin
        profile=custom_skeleton.validate(body.get("profile"))
        if profile.get("skin",{}).get("mode")!="weighted":raise ValueError("Enable weighted skinning first")
        size=(modular.integer(body.get("width"),1,1024,"source width"),modular.integer(body.get("height"),1,1024,"source height"))
        _,segments=custom_skeleton.transforms(profile,size)
        return {"image":b64(custom_skin.heatmap(profile,size,segments,body.get("bone")))}
    except (ValueError,TypeError) as e:raise HTTPException(400,str(e))


@app.post("/api/custom_skeleton/timeline")
def custom_timeline_preview(body: dict=Body(...)):
    try:
        frames,meta=custom_timeline.render(body.get("image"),body.get("profile"),body.get("padding",32),frame=body.get("frame"))
        return {**meta,"frames":[b64(im) for im in frames]}
    except (ValueError,TypeError,AttributeError) as e:raise HTTPException(400,str(e))


@app.post("/api/custom_skeleton/export_timeline")
def custom_timeline_export(body: dict=Body(...)):
    try:
        frames,meta=custom_timeline.render(body.get("image"),body.get("profile"),body.get("padding",32),preview=False)
        options=body.get("options") or {}
        if not isinstance(options,dict):raise ValueError("Invalid export options")
        # Fixed untrimmed canvas and rest root pivot, shared across every frame.
        options=dict(options,crop=False,uniform=True,smooth=not body["profile"].get("pixel",True))
        frames=custom_cleanup.apply(frames,meta,body.get("cleanup"))
        entry={**meta,"frames":frames}
        return exporter.export_pack([entry],options,meta["name"],ROOT)
    except (ValueError,TypeError,AttributeError) as e:raise HTTPException(400,str(e))


@app.post("/api/custom_skeleton/cleanup_mask")
def custom_cleanup_mask(body: dict=Body(...)):
    try:
        frame,mask,opts,meta=custom_cleanup.prepare(body)
        return {"original":b64(frame),"mask":b64(Image.fromarray(mask.astype("uint8")*255,"L")),
                "fingerprint":meta["fingerprint"],"frame":meta["indices"][0],"pixels":int(mask.sum())}
    except (ValueError,TypeError,AttributeError) as e:raise HTTPException(400,str(e))


@app.post("/api/custom_skeleton/cleanup")
def custom_cleanup_frame(body: dict=Body(...)):
    try:
        from .custom_skeleton import number
        ckpt,lora_dir=_paths(body.get("checkpoint"))
        model=mf.describe(ckpt)
        if model["family"]!="sdxl" or model.get("backend"):
            raise ValueError("Selective cleanup needs a verified SDXL inpainting-compatible checkpoint; Qwen/NetaYume do not expose mask inpainting")
        lora=body.get("lora","")
        if not isinstance(lora,str):raise ValueError("Invalid LoRA")
        mf.check_lora(ckpt,lora_dir,lora)
        lw=number(body.get("lora_weight",1),0,2,"LoRA weight")
        strength=number(body.get("strength",.35),.15,.75,"cleanup strength")
        steps=modular.integer(body.get("steps",20),8,40,"cleanup steps")
        guidance=number(body.get("cfg",5),1,12,"cleanup CFG")
        seed=modular.integer(body.get("seed",0),0,2**31-1,"cleanup seed")
        size=modular.integer(body.get("size",768),512,1024,"inference size")
        if size not in (512,768,1024):raise ValueError("Choose 512, 768 or 1024 inference size")
        prompt=body.get("prompt","");negative=body.get("negative","")
        if not isinstance(prompt,str) or not isinstance(negative,str) or max(len(prompt),len(negative))>2000:
            raise ValueError("Invalid cleanup prompt")
        frame,mask,opts,meta=custom_cleanup.prepare(body)
        pixel=body["profile"].get("pixel",True)
        style="pixel" if pixel else body.get("art_style","custom")
        if style not in styles.PRESETS or (not pixel and style=="pixel"):style="custom"
        gen.set_sampler(body.get("sampler","euler_a"))
        text="preserve same character identity, costume, pose, proportions, colors and linework; repair local joint seams and malformed folds"
        if prompt.strip():text+=", "+prompt.strip()
        out,info=custom_cleanup.cleanup(frame,mask,opts,gen.inpaint,ckpt,lora,lw,lora_dir,text,negative,strength,steps,guidance,seed,size,pixel,style)
        return {"sprite":b64(out),"original":b64(frame),"fingerprint":meta["fingerprint"],"frame":meta["indices"][0],"info":info}
    except (ValueError,TypeError,AttributeError) as e:raise HTTPException(400,str(e))
    except RuntimeError as e:raise HTTPException(500,"Cleanup failed: "+str(e))


@app.post("/api/custom_skeleton/ik")
def custom_skeleton_ik(body: dict=Body(...)):
    try:
        p=custom_skeleton.validate(body.get("profile"))
        size=(modular.integer(body.get("width"),1,1024,"source width"),modular.integer(body.get("height"),1,1024,"source height"))
        frame=body.get("frame")
        if frame is not None:
            if "timeline" not in p:raise ValueError("Create a timeline first")
            frame=modular.integer(frame,0,p["timeline"]["count"]-1,"IK frame")
            p=custom_timeline.pose(p,frame)
        solved,points,reports=custom_ik.solve(p,size,frame)
        return {"bones":points,"chains":reports,"angles":{b["id"]:b["angle"] for b in solved["bones"]}}
    except (ValueError,TypeError,AttributeError) as e:raise HTTPException(400,str(e))


@app.post("/api/custom_skeleton/pose")
def custom_skeleton_pose(body: dict=Body(...)):
    try:
        image,points=custom_skeleton.render(body.get("image"),body.get("profile"),body.get("padding",32))
        return {"sprite":b64(image),"size":list(image.size),"bones":points}
    except (ValueError,AttributeError,TypeError) as e:raise HTTPException(400,str(e))


@app.post("/api/modular/rig")
def modular_rig_info(body: dict = Body(...)):
    try:return modular_rig.describe(body)
    except ValueError as e:raise HTTPException(400,str(e))


def _modular_clip(b):
    return modular_rig.render(b.recipe,b.anim,b.count,b.facing,b.near,b.weapon,b.amp,b.pad,softness=b.softness)


@app.post("/api/modular/animate")
def modular_animate(b: ModularAnimation):
    try:
        frames,meta=_modular_clip(b)
        return {"frames":[b64(im) for im in frames],"fps":max(1,min(60,b.fps)),"size":meta["size"],"pivot":meta["pivot"]}
    except ValueError as e:raise HTTPException(400,str(e))


@app.post("/api/modular/export_animation")
def modular_export_animation(b: ModularAnimation):
    try:
        frames,meta=_modular_clip(b)
        entries=[{"name":b.anim,"fps":max(1,min(60,b.fps)),"loop":b.anim not in rig.ONE_SHOT,"frames":frames,"pivot":tuple(meta["pivot"])}]
        return exporter.export_pack(entries,dict(b.options,smooth=meta["render_mode"]=="hd"),b.name,ROOT)
    except ValueError as e:raise HTTPException(400,str(e))


class ModularLayerExport(ModularAnimation):
    columns: int = 8
    include_hidden: bool = True
    individual: bool = False


@app.post("/api/modular/export_layers")
def modular_export_layers(b: ModularLayerExport):
    try:
        return layer_export.export(b.recipe,b.anim,b.count,b.fps,b.facing,b.near,b.weapon,b.amp,b.pad,b.softness,b.name,ROOT,
                                   b.columns,b.include_hidden,b.individual)
    except ValueError as e:raise HTTPException(400,str(e))


@app.post("/api/modular/render")
def modular_render(body: dict = Body(...)):
    try:return {"sprite":modular.png_uri(modular.render(body))}
    except ValueError as e:raise HTTPException(400,str(e))


@app.post("/api/modular/validate")
def modular_validate(body: dict = Body(...)):
    try:return modular.validate(body)[0]
    except ValueError as e:raise HTTPException(400,str(e))


@app.post("/api/modular/export")
def modular_export(body: dict = Body(...)):
    try:
        data=modular.bundle(body)
        return StreamingResponse(io.BytesIO(data),media_type="application/zip",
                                 headers={"Content-Disposition":'attachment; filename="character_layers.zip"'})
    except ValueError as e:raise HTTPException(400,str(e))


@app.get("/api/library")
def library_list(kind: str="",q: str=""):
    try:return {"entries":asset_library.list_entries(ROOT,kind,q)}
    except ValueError as e:raise HTTPException(400,str(e))


@app.post("/api/library")
def library_save(body: dict=Body(...)):
    try:return asset_library.save(ROOT,body)
    except ValueError as e:raise HTTPException(400,str(e))


@app.get("/api/library/{entry_id}/preview")
def library_preview(entry_id: str):
    try:return FileResponse(asset_library.preview_path(ROOT,entry_id),media_type="image/png")
    except (ValueError,FileNotFoundError) as e:raise HTTPException(404,str(e))


@app.get("/api/library/{entry_id}")
def library_get(entry_id: str):
    try:return asset_library.load(ROOT,entry_id)
    except (ValueError,FileNotFoundError) as e:raise HTTPException(404,str(e))


@app.delete("/api/library/{entry_id}")
def library_delete(entry_id: str):
    try:return asset_library.delete(ROOT,entry_id)
    except (ValueError,FileNotFoundError) as e:raise HTTPException(404,str(e))


@app.post("/api/library/{entry_id}/apply")
def library_apply(entry_id: str,body: dict=Body(...)):
    try:return asset_library.apply(ROOT,entry_id,body.get("recipe"),body.get("keep_placement") is True)
    except FileNotFoundError as e:raise HTTPException(404,str(e))
    except ValueError as e:raise HTTPException(400,str(e))


@app.get("/api/model_manager")
def model_manager():
    from . import local_runtime as lr
    md=cfg()["models_dir"]
    root,python=lr.runtime()
    s=state()
    models=[]
    for name,info in s["model_info"].items():
        p=_checkpoint_path(Path(md),name)
        route,missing=lr.readiness(p)
        components=[]
        if route:
            components=[root/"comfy/sd.py",python]
            if route=="qwen":components+=list(lr.qwen_files(p.parent.parent,p).values())+[root/"comfy_extras/nodes_qwen.py"]
        try:size=p.stat().st_size if p.is_file() else None
        except OSError:size=None
        models.append({"name":name,**info,"path":str(p),"bytes":size,"missing":missing if route else [],
                       "components":[{"path":str(c),"present":c.is_file()} for c in components],
                       "loras":[{"name":n,"family":family,"compatibility":mf.compatibility(info["family"],family)}
                                for n,family in s["lora_families"].items()]})
    return {"models":models,"lora_families":s["lora_families"],"models_dir":md,"gpu":s["gpu"],"runtime_root":str(root),"runtime_python":str(python),
            "runtime_present":python.is_file() and (root/"comfy/sd.py").is_file(),
            "note":"Header and file-presence inspection only; does not load model weights or benchmark GPU compatibility."}


# ---------------- diagnostics ----------------
@app.get("/api/diag")
def diag_run():
    return diag.run_checks(ROOT, cfg()["models_dir"], llmm.state())


class GpuTest(BaseModel):
    checkpoint: str
    lora: str = ""


@app.post("/api/diag/gpu_test")
def diag_gpu_test(b: GpuTest):
    ckpt, lora_dir = _paths(b.checkpoint)
    from . import local_runtime as lr
    if lr.route(ckpt):raise HTTPException(400,"This GPU benchmark is for SDXL; use the local worker readiness in the model picker and a small generation for a live check.")
    try:
        return gen.smoke_test(ckpt, b.lora, lora_dir)
    except Exception as e:
        hint = " - out of GPU memory: close other GPU apps and retry" if "out of memory" in str(e).lower() else ""
        raise HTTPException(500, f"{type(e).__name__}: {e}{hint}")


@app.post("/api/diag/llm_test")
def diag_llm_test():
    try:
        return llmm.selftest()
    except llm.LlmError as e:
        raise HTTPException(400, str(e))


# ---------------- local assistant (llama.cpp server loaded on demand) ----------------
def _save_cfg(updates):
    data = cfg()
    data.update(updates)
    CFG_PATH.write_text(json.dumps(data, indent=2))


llmm = llm.Manager(ROOT, cfg, _save_cfg)
atexit.register(llmm.stop)


class LlmCfg(BaseModel):
    server: Optional[str] = None
    model: Optional[str] = None
    gpu_layers: Optional[int] = None
    ctx: Optional[int] = None
    idle_min: Optional[int] = None
    search_dir: Optional[str] = None


@app.get("/api/llm/state")
def llm_state(rescan: bool = False):
    return llmm.state(rescan)


@app.post("/api/llm/config")
def llm_config(c: LlmCfg):
    try:
        llmm.update(**{k: getattr(c, k) for k in ("server", "model", "gpu_layers", "ctx", "idle_min", "search_dir")
                       if getattr(c, k) is not None})
    except llm.LlmError as e:
        raise HTTPException(400, str(e))
    return llmm.state(rescan=c.search_dir is not None or c.server is not None)


@app.post("/api/llm/start")
def llm_start():
    try:
        llmm.start()
    except llm.LlmError as e:
        raise HTTPException(400, str(e))
    return llmm.state()


@app.post("/api/llm/stop")
def llm_stop():
    llmm.stop()
    return llmm.state()


class ChatBody(BaseModel):
    messages: List[dict]
    context: str = ""


@app.post("/api/llm/chat")
def llm_chat(b: ChatBody):
    return StreamingResponse(llmm.chat_events(b.messages, b.context), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ---------------- portraits ----------------
@app.post("/api/portrait/base")
def portrait_base(ref: Optional[UploadFile] = File(None), prompt: str = Form(""), negative: str = Form(""),
                  checkpoint: str = Form(...), lora: str = Form(""), lora_weight: float = Form(1.0),
                  steps: int = Form(25), cfg: float = Form(7.0), seed: int = Form(-1), bg: str = Form("light gray"),
                  n: int = Form(2), size: int = Form(128), colors: int = Form(24), transparent: bool = Form(False),
                  ip_scale: float = Form(0.6), bg_tol: int = Form(40), crisp: bool = Form(True),
                  clean: bool = Form(True), sampler: str = Form("euler_a")):
    ckpt, lora_dir = _paths(checkpoint)
    gen.set_sampler(sampler)
    ip_img = None
    if ref is not None:  # use a sprite as the look reference (IP-Adapter)
        ip_img = gen.prep_reference(px.crop_to_content(px.remove_bg(Image.open(ref.file), bg_tol)), bg)
    size = max(32, min(size, 256))
    post = lambda raw: px.pixelize(raw, "canvas", size, max(4, min(colors, 64)), "none", transparent, bg_tol,
                                   remove_shadow=False, crisp=crisp, clean=clean)
    return _run(ckpt, lora_dir, lora, lora_weight, prompt, negative, steps, cfg, seed, bg, max(1, min(n, 4)), ip_img,
                ip_scale, post, None, 0.8, None, 1024, "portrait")


@app.post("/api/portrait/expressions")
def portrait_expressions(base: UploadFile = File(...), mask: str = Form(...), items: str = Form(...),
                         character: str = Form(""), negative: str = Form(""), checkpoint: str = Form(...),
                         lora: str = Form(""), lora_weight: float = Form(1.0), strength: float = Form(0.82),
                         steps: int = Form(25), cfg: float = Form(7.0), seed: int = Form(-1), extra: int = Form(4),
                         sampler: str = Form("euler_a")):
    ckpt, lora_dir = _paths(checkpoint)
    gen.set_sampler(sampler)
    try:
        img = Image.open(base.file).convert("RGBA")
        m = json.loads(mask)
        its = [(str(i.get("name", ""))[:30] or "expression", str(i.get("text", ""))[:200]) for i in json.loads(items)[:16]]
    except Exception:
        raise HTTPException(400, "bad portrait, mask or expression list")
    if not its:
        raise HTTPException(400, "pick at least one expression")
    gen_ = portrait.expression_events(img, m, its, ckpt, lora, lora_weight, lora_dir, character, negative,
                                      max(.3, min(strength, .95)), max(8, min(steps, 50)), cfg, seed, max(0, min(extra, 8)))
    return StreamingResponse(gen_, media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


class PortraitItem(BaseModel):
    name: str
    image: str


class PortraitExport(BaseModel):
    name: str = "portrait"
    images: List[PortraitItem]
    columns: int = 4
    godot_path: str = "res://sprites/"
    ppu: int = 32


@app.post("/api/portrait/export")
def portrait_export(b: PortraitExport):
    """Individual PNGs + one sheet + Godot SpriteFrames (one 1-frame animation per expression) + Unity importer data."""
    if not 1 <= len(b.images) <= 32:
        raise HTTPException(400, "need 1-32 portraits")
    entries, used = [], set()
    for it in b.images:
        try:
            im = _dec_img(it.image)
        except Exception:
            raise HTTPException(400, f"bad image: {it.name}")
        nm = re.sub(r"[^A-Za-z0-9_-]+", "_", it.name).strip("_")[:30] or "expression"
        while nm in used:
            nm += "_2"
        used.add(nm)
        entries.append({"name": nm, "fps": 1, "loop": False, "frames": [im], "pivot": (im.width // 2, im.height // 2)})
    if len({e["frames"][0].size for e in entries}) != 1:
        raise HTTPException(400, "all portraits must share one size")
    opts = {"layout": "grid", "columns": max(1, min(b.columns, 16)), "crop": False, "uniform": True, "godot": True,
            "godot_path": b.godot_path, "unity": True, "ppu": b.ppu, "gif": False, "frames": True}
    try:
        return exporter.export_pack(entries, opts, f"{b.name}_portraits", ROOT)
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")


# ---------------- projects ----------------
def _proj(fn, *a):
    try:
        return fn(ROOT, *a)
    except projects.ProjectError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, f"{type(e).__name__}: {e}")


@app.get("/api/projects")
def projects_list():
    return {"projects": projects.list_projects(ROOT)}


@app.post("/api/projects/save")
def projects_save(body: dict = Body(...)):
    return _proj(projects.save, body.get("name"), body)


@app.get("/api/projects/{name}")
def projects_load(name: str):
    return _proj(projects.load, name)


@app.delete("/api/projects/{name}")
def projects_delete(name: str):
    _proj(projects.delete, name)
    return {"ok": True}


@app.post("/api/projects/{name}/sprites")
def projects_add_sprite(name: str, body: dict = Body(...)):
    return {"id": _proj(projects.add_sprite, name, body.get("sprite"))}


@app.get("/api/projects/{name}/sprites")
def projects_sprites(name: str):
    return {"sprites": _proj(projects.list_sprites, name)}


@app.delete("/api/projects/{name}/sprites/{sid}")
def projects_del_sprite(name: str, sid: str):
    _proj(projects.delete_sprite, name, sid)
    return {"ok": True}


# ---------------- tiles and props ----------------
@app.post("/api/tiles/seamless")
def tiles_seamless(file: UploadFile = File(...)):
    """Make a pixel tile seamless (no new colours): picks pixels from the image or its half-shifted copy through a dither mask."""
    img = Image.open(file.file).convert("RGBA")
    if max(img.size) > 512 or min(img.size) < 4:
        raise HTTPException(400, "tile must be between 4 and 512 px")
    out = tiles.seamless_pixels(img)
    return {"sprite": b64(out), "info": {"size": list(out.size), "seam_before": tiles.seam_score(img), "seam": tiles.seam_score(out)}}


@app.post("/api/tiles/offset")
def tiles_offset(file: UploadFile = File(...), dx: int = Form(-1), dy: int = Form(-1)):
    """Shift with wrap-around (-1 = half the size) to inspect / repaint the seams."""
    img = Image.open(file.file).convert("RGBA")
    out = tiles.wrap_offset(img, None if dx < 0 else dx, None if dy < 0 else dy)
    return {"sprite": b64(out), "info": {"size": list(out.size), "seam": tiles.seam_score(img)}}


class RepairBody(BaseModel):
    tile: str
    prompt: str = ""
    negative: str = ""
    checkpoint: str
    lora: str = ""
    lora_weight: float = 1.0
    steps: int = 22
    cfg: float = 7.0
    seed: int = -1
    bg: str = "white"
    strength: float = 0.55
    band: float = 0.16
    sampler: str = "euler_a"


@app.post("/api/tiles/repair")
def tiles_repair(b: RepairBody):
    """AI seam repair: the AI redraws only the (half-shifted) seam cross of a tile; everything else stays exactly."""
    try:
        tile = Image.open(io.BytesIO(base64.b64decode(b.tile.split(",", 1)[1]))).convert("RGBA")
    except Exception:
        raise HTTPException(400, "the tile is not a valid image")
    ckpt, lora_dir = _paths(b.checkpoint)
    gen.set_sampler(b.sampler)
    seed = b.seed if b.seed >= 0 else int(np.random.randint(0, 2**31 - 1))
    prompt = b.prompt.strip() or "seamless texture"   # gen.inpaint wraps it with the tile template itself
    try:
        out, info = tiles.repair_seams(tile, gen.inpaint, prompt, b.negative, ckpt, b.lora, b.lora_weight, lora_dir,
                                       max(0.2, min(b.strength, 0.95)), max(8, min(b.steps, 60)), b.cfg, seed, b.bg, max(0.08, min(b.band, 0.4)))
    except tiles.TileError as e:
        raise HTTPException(400, str(e))
    except HTTPException:
        raise
    except Exception as e:
        hint = " - out of GPU memory: close other GPU apps and retry" if "out of memory" in str(e).lower() else ""
        diag.record_error("tiles/repair", "500", f"{type(e).__name__}: {e}")
        raise HTTPException(500, f"{type(e).__name__}: {e}{hint}")
    info["seed"] = seed
    return {"sprite": b64(out), "info": info}


class AnimBody(BaseModel):
    tile: str
    mode: str = "scroll"              # scroll | ripple | shimmer
    frames: int = 8
    direction: str = "right"
    amount: float = 0
    density: float = 0.25
    seed: int = 1
    name: str = "animated_tile"
    ms: int = 120
    godot: bool = True
    godot_path: str = "res://tiles/"
    tiled: bool = True


def _anim_frames(b):
    try:
        tile = Image.open(io.BytesIO(base64.b64decode(b.tile.split(",", 1)[1]))).convert("RGBA")
    except Exception:
        raise HTTPException(400, "the tile is not a valid image")
    if max(tile.size) > 256 or min(tile.size) < 4:
        raise HTTPException(400, "tile must be between 4 and 256 px")
    try:
        return tiles.animate_tile(tile, b.mode, b.frames, b.direction, b.amount, b.density, b.seed)
    except tiles.TileError as e:
        raise HTTPException(400, str(e))


@app.post("/api/tiles/animate")
def tiles_animate(b: AnimBody):
    return {"frames": [b64(f) for f in _anim_frames(b)], "ms": max(20, min(b.ms, 2000))}


@app.post("/api/tiles/export_anim")
def tiles_export_anim(b: AnimBody):
    frames = _anim_frames(b)
    try:
        return tiles.export_animated(frames, b.name, dict(ms=b.ms, godot=b.godot, godot_path=b.godot_path, tiled=b.tiled), ROOT)
    except tiles.TileError as e:
        raise HTTPException(400, str(e))


class TileSetBody(BaseModel):
    name: str = "tileset"
    tiles: List[dict]                 # [{name, image(data URL)}]
    columns: int = 8
    spacing: int = 0
    margin: int = 0
    godot: bool = True
    godot_path: str = "res://tiles/"
    tiled: bool = True


@app.post("/api/tiles/export")
def tiles_export(b: TileSetBody):
    if not b.tiles:
        raise HTTPException(400, "add at least one tile first")
    imgs, names = [], []
    for i, t in enumerate(b.tiles[:512]):
        try:
            imgs.append(Image.open(io.BytesIO(base64.b64decode(str(t.get("image", "")).split(",", 1)[1]))).convert("RGBA"))
        except Exception:
            raise HTTPException(400, f"tile {i + 1} is not a valid image")
        names.append(t.get("name") or "")
    solid = [bool(t.get("solid")) for t in b.tiles[:512]]
    try:
        return tiles.export_tileset(imgs, names, dict(columns=b.columns, spacing=b.spacing, margin=b.margin, godot=b.godot,
                                                      godot_path=b.godot_path, tiled=b.tiled, solid=solid), b.name, ROOT)
    except tiles.TileError as e:
        raise HTTPException(400, str(e))


class TerrainBody(BaseModel):
    a: str                            # terrain A tile (data URL), e.g. grass
    b: Optional[str] = None           # ground tile B (data URL), e.g. dirt (optional)
    c: Optional[str] = None           # terrain C (multi sets)
    d: Optional[str] = None           # terrain D (multi sets, optional)
    kind: str = "blob47"              # blob47 | edge16 | corner16 | multi
    names: List[str] = []             # terrain names A, B, C, D
    inset: int = 0                    # border inset in px (0 = automatic)
    round: int = -1                   # convex corner rounding in px (-1 = automatic)
    rim: str = "dark"                 # none | dark | light
    base: str = "bake"                # bake (ground under A) | transparent
    ground: bool = True               # add the plain ground tile to the sheet
    name: str = "terrain"
    terrain_name: str = "Terrain"
    columns: int = 8
    godot: bool = True
    godot_path: str = "res://tiles/"
    tiled: bool = True


def _terrain_set(b):
    def img(u, what):
        try:
            return Image.open(io.BytesIO(base64.b64decode(str(u).split(",", 1)[1]))).convert("RGBA")
        except Exception:
            raise HTTPException(400, f"{what} is not a valid image")
    if b.kind in terrain.CORNER_KINDS:
        slots = [(b.a, "terrain tile A"), (b.b, "ground tile B"), (b.c, "terrain tile C"), (b.d, "terrain tile D")]
        if b.kind == "corner16":
            texs = [img(b.a, slots[0][1]), img(b.b, slots[1][1]) if b.b else None]
        else:
            if not (b.b and b.c):
                raise HTTPException(400, "a multi-terrain set needs terrains A, B and C (D is optional)")
            texs = [img(u, w) for u, w in slots if u]
        try:
            return terrain.generate_corner(texs, None if b.round < 0 else b.round, b.rim)
        except terrain.TerrainError as e:
            raise HTTPException(400, str(e))
    try:
        return terrain.generate_set(img(b.a, "terrain tile A"), img(b.b, "ground tile B") if b.b else None, b.kind, b.inset,
                                    None if b.round < 0 else b.round, b.rim, b.base, b.ground)
    except terrain.TerrainError as e:
        raise HTTPException(400, str(e))


@app.post("/api/terrain/generate")
def terrain_generate(b: TerrainBody):
    res = _terrain_set(b)
    corner = res["kind"] in terrain.CORNER_KINDS
    return {"tiles": [{"index": t["index"], "mask": t.get("mask"), "corners": t.get("corners"), "image": b64(t["image"])} for t in res["tiles"]],
            "ground": b64(res["ground"]) if res.get("ground") is not None else None, "lookup": res.get("lookup", []), "kind": res["kind"],
            "tile_size": res["tile_size"], "inset": res.get("inset", 0), "round": res.get("sigma", res.get("round", 0)), "rim": res["rim"],
            "base": res.get("base", "bake"), "n": res.get("n", 2) if corner else 2}


@app.post("/api/terrain/export")
def terrain_export(b: TerrainBody):
    res = _terrain_set(b)
    try:
        opts = dict(columns=b.columns, godot=b.godot, godot_path=b.godot_path, tiled=b.tiled)
        if res["kind"] in terrain.CORNER_KINDS:
            return terrain.export_corner(res, b.name, opts, ROOT, b.names or [b.terrain_name])
        return terrain.export_terrain(res, b.name, opts, ROOT, b.terrain_name)
    except terrain.TerrainError as e:
        raise HTTPException(400, str(e))


# ---------------- generation queue + history ----------------
def _exec_job(kind, params, inputs, progress):
    """Runs one queued job (called by the queue's worker thread). Returns the list of results."""
    gen._job_context.progress = progress
    gen._job_context.cancelled = getattr(progress,"cancelled",None)
    try:
        if kind == "generate":
            return _do_generate(GenParams(**params))["results"]
        return _do_reference(inputs["ref"], inputs.get("pose"), params)["results"]
    finally:
        gen._job_context.progress = None
        gen._job_context.cancelled = None


_JOBS = None


def _jobmgr():
    global _JOBS
    if _JOBS is None or _JOBS.dir.parent != Path(ROOT):
        if _JOBS is not None:
            _JOBS.shutdown()
        _JOBS = jobs.Manager(ROOT, _exec_job)
    return _JOBS


def _job(fn, *a, **k):
    try:
        return fn(*a, **k)
    except jobs.JobError as e:
        raise HTTPException(400, str(e))


@app.post("/api/queue/add")
def queue_add(body: dict = Body(...)):
    """body: {kind: generate|reference, params: {...same fields as /api/generate or /api/reference...}, ui: {...}, images: {ref, pose}}"""
    params = body.get("params") or {}
    if not params.get("checkpoint"):
        raise HTTPException(400, "pick a checkpoint first")
    return _job(_jobmgr().add, body.get("kind"), params, body.get("ui"), body.get("images"))


@app.get("/api/queue")
def queue_state():
    return _jobmgr().queue()


@app.post("/api/queue/pause")
def queue_pause(body: dict = Body(...)):
    return {"paused": _jobmgr().set_paused(body.get("paused", True))}


@app.post("/api/queue/cancel_all")
def queue_cancel_all():
    return {"cancelled": _jobmgr().cancel_all()}


@app.post("/api/jobs/{jid}/cancel")
def job_cancel(jid: str):
    return _job(_jobmgr().cancel, jid)


@app.get("/api/history")
def history_list(limit: int = 40, offset: int = 0, fav: bool = False, q: str = "", kind: str = ""):
    return _jobmgr().history(limit, offset, fav, q, kind)


@app.post("/api/history/clear")
def history_clear(body: dict = Body(...)):
    return {"deleted": _jobmgr().clear_history(keep_favs=body.get("keep_favs", True))}


@app.get("/api/jobs/{jid}")
def job_get(jid: str):
    return _job(_jobmgr().get, jid)


@app.post("/api/jobs/{jid}/meta")
def job_meta(jid: str, body: dict = Body(...)):
    return _job(_jobmgr().update, jid, body.get("fav"), body.get("note"))


@app.post("/api/jobs/{jid}/rerun")
def job_rerun(jid: str, body: dict = Body(...)):
    return _job(_jobmgr().rerun, jid, bool(body.get("new_seed")))


@app.delete("/api/jobs/{jid}")
def job_delete(jid: str):
    _job(_jobmgr().delete, jid)
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(ROOT / "ui" / "index.html")


app.mount("/ui", StaticFiles(directory=ROOT / "ui"), name="ui")

if __name__ == "__main__":
    import uvicorn
    port = cfg().get("port", 8765)
    print(f"\nSpriteForge running at http://127.0.0.1:{port}\n")
    uvicorn.run(app, host="127.0.0.1", port=port)
