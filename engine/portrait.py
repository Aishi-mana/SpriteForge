"""Portrait expressions: repaint only a face-area mask of a pixel portrait (SDXL inpaint), keep everything else
pixel-identical, and snap the result back to the portrait's own palette (plus a few extra colours for blush, tears...)."""
import base64, io, json
import numpy as np
from PIL import Image
from . import generate as gen, rig
from .refine import CANDIDATE_BG, _nearest_palette
from . import diag

EXPRESSIONS = {
    "happy": "smiling, happy eyes, cheerful",
    "sad": "sad, downturned eyes, teary, frowning",
    "angry": "angry, furrowed brows, glaring, frowning mouth",
    "surprised": "surprised, wide eyes, raised eyebrows, open mouth",
    "embarrassed": "embarrassed, blushing cheeks, looking away, small shy smile",
    "smug": "smug smirk, half-lidded eyes, one raised eyebrow",
    "sleepy": "sleepy, closed eyes, relaxed face, yawning",
    "pain": "in pain, wincing, eyes shut tight, gritted teeth",
    "scared": "scared, wide eyes, small trembling mouth, sweat drop",
    "determined": "determined, focused eyes, slight frown, firm mouth",
    "laughing": "laughing, closed happy eyes, wide open smile",
    "serious": "serious, calm eyes, neutral mouth",
}


def _b64(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def ellipse_mask(n, m):
    cx, cy = float(m.get("cx", .5)), float(m.get("cy", .45))
    rx, ry = max(.02, float(m.get("rx", .27))), max(.02, float(m.get("ry", .30)))
    yy, xx = np.mgrid[0:n, 0:n]
    return (((xx + .5) / n - cx) / rx) ** 2 + (((yy + .5) / n - cy) / ry) ** 2 <= 1


def prep(base, mask_n, size=1024):
    """Upscale the portrait with nearest-neighbour onto a 1024 canvas for the inpaint model."""
    n = base.width
    k = max(1, size // n)
    off = (size - n * k) // 2
    arr = np.asarray(base.convert("RGBA"))
    has_alpha = bool((arr[..., 3] < 250).any())
    op = arr[..., 3] >= 128
    cols = np.unique(arr[op][:, :3], axis=0) if op.any() else np.zeros((0, 3), np.uint8)
    use_pal = 0 < len(cols) <= 96
    if has_alpha:  # transparent portrait: paint on a background colour far from the palette
        bgname = max(CANDIDATE_BG, key=lambda c: ((cols.astype(int) - np.array(CANDIDATE_BG[c])) ** 2).sum(1).min()) if use_pal else "magenta"
        bg = np.array(CANDIDATE_BG[bgname])
    else:
        border = np.concatenate([arr[0, :, :3], arr[-1, :, :3], arr[:, 0, :3], arr[:, -1, :3]])
        bg, bgname = np.median(border, 0).astype(int), "light gray"
    big = base.convert("RGBA").resize((n * k, n * k), Image.NEAREST)
    img = Image.new("RGB", (size, size), tuple(int(v) for v in bg))
    img.paste(big.convert("RGB"), (off, off), big if has_alpha else None)
    mk = Image.new("L", (size, size), 0)
    mk.paste(Image.fromarray((mask_n * 255).astype(np.uint8)).resize((n * k, n * k), Image.NEAREST), (off, off))
    return dict(img=img, mask=mk, n=n, k=k, off=off, has_alpha=has_alpha, cols=cols, use_pal=use_pal, bg=bg,
                bgname=bgname, arr=arr)


def _extra_colors(px, cols, k):
    """New colours the AI introduced inside the face area (blush, tears...), reduced to at most k."""
    empty = np.zeros((0, 3), np.uint8)
    if len(px) == 0 or k <= 0:
        return empty
    if len(px) > 20000:
        px = px[np.random.RandomState(0).choice(len(px), 20000, replace=False)]
    d = ((px[:, None, :].astype(int) - cols[None].astype(int)) ** 2).sum(-1).min(1)
    far = px[d > 45 ** 2]
    if len(far) < max(12, int(.02 * len(px))):
        return empty
    q = Image.fromarray(far.astype(np.uint8).reshape(1, -1, 3)).quantize(colors=k, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    pal = np.array(q.getpalette()[:3 * k]).reshape(-1, 3)
    used = sorted({i for _, i in q.getcolors() if i < len(pal)})
    return pal[used].astype(np.uint8)


def finish(res, P, mask_n, max_extra):
    n, k, off = P["n"], P["k"], P["off"]
    crop = np.asarray(res.convert("RGB"))[off:off + n * k, off:off + n * k].astype(np.int16)
    maskhi = np.kron(mask_n.astype(np.uint8), np.ones((k, k), np.uint8)).astype(bool)
    is_bg = (np.abs(crop - P["bg"]).max(-1) <= 70) if P["has_alpha"] else np.zeros(crop.shape[:2], bool)
    extras = np.zeros((0, 3), np.uint8)
    if P["use_pal"]:
        extras = _extra_colors(crop[maskhi & ~is_bg].astype(np.uint8), P["cols"], max_extra)
        pal = np.unique(np.vstack([P["cols"], extras]), axis=0)  # sorted rows == ascending colour keys
        rgb = pal[_nearest_palette(crop, pal)]
        keys = (pal[:, 0].astype(np.int64) << 16) | (pal[:, 1].astype(np.int64) << 8) | pal[:, 2].astype(np.int64)
        hi = Image.fromarray(np.dstack([rgb, np.where(is_bg, 0, 255)]).astype(np.uint8), "RGBA")
        new = np.asarray(rig._downsample(hi, k, keys, pal, True))
    else:
        hi = Image.fromarray(np.dstack([crop.astype(np.uint8), np.where(is_bg, 0, 255).astype(np.uint8)]), "RGBA")
        new = np.asarray(rig._downsample(hi, k, None, None, False))
    out = P["arr"].copy()
    out[mask_n] = new[mask_n]
    if not P["has_alpha"]:
        out[..., 3] = 255
    return Image.fromarray(out, "RGBA"), extras


def expression_events(base, mask, items, ckpt, lora, lora_w, lora_dir, character, negative, strength, steps, cfg, seed,
                      max_extra, inpaint_fn=None):
    """Generator of SSE events: status / result (one per expression, as soon as it is done) / error / done."""
    inpaint_fn = inpaint_fn or gen.inpaint
    ev = lambda o: "data: " + json.dumps(o) + "\n\n"
    if base.width != base.height or base.width > 512:
        yield ev({"error": "the base portrait must be square and at most 512 px"})
        return
    mask_n = ellipse_mask(base.width, mask or {})
    if not mask_n.any():
        yield ev({"error": "the face area is empty: drag on the portrait to draw it"})
        return
    P = prep(base, mask_n)
    if seed is None or seed < 0:
        seed = int(np.random.randint(0, 2**31 - 1))
    for i, (name, text) in enumerate(items):
        yield ev({"status": f"Expression {i + 1}/{len(items)}: {name}…"})
        try:
            prompt = ", ".join(s for s in (character.strip(), (text or EXPRESSIONS.get(name, name)).strip()) if s)
            res = inpaint_fn(ckpt, lora, lora_w, lora_dir, prompt, negative, P["img"], P["mask"], strength, steps, cfg, seed,
                             P["bgname"], "expression")
            out, extras = finish(res, P, mask_n, max_extra)
        except Exception as e:
            hint = " - out of GPU memory: close other GPU apps and retry" if "out of memory" in str(e).lower() else ""
            diag.record_error("portrait/expressions", "SSE", f"{type(e).__name__}: {e}")
            yield ev({"error": f"{type(e).__name__}: {e}{hint}"})
            return
        yield ev({"result": {"name": name, "image": _b64(out), "extra": extras.tolist()}})
    yield ev({"done": True, "seed": seed})
