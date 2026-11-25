"""Palette tools: import (.hex .gpl .pal / swatch PNG), your own palette library, remap with optional dithering,
reduce / merge colours, hue-shifted colour variants, shading ramps, sorting and export. All colour maths is in OKLab."""
import io, json, re
from pathlib import Path
import numpy as np
from PIL import Image
from . import pixelize as px

BAYER = {2: np.array([[0, 2], [3, 1]]), 4: np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])}


class PaletteError(ValueError):
    pass


def to_hex(c):
    return "#%02x%02x%02x" % tuple(int(v) for v in c)


def from_hex(s):
    s = str(s).strip().lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    if not re.fullmatch(r"[0-9a-fA-F]{6}", s):
        raise PaletteError(f"not a colour: {s!r}")
    return [int(s[i:i + 2], 16) for i in (0, 2, 4)]


def _dedupe(cols):
    seen, out = set(), []
    for c in cols:
        k = tuple(int(v) for v in c)
        if k not in seen:
            seen.add(k)
            out.append(list(k))
    return out


def _arr(cols):
    return np.array([from_hex(c) if isinstance(c, str) else c for c in cols], np.uint8).reshape(-1, 3)


# ---------------- colour science (OKLab / OKLCH) ----------------
def _lin(L, a, b):
    """OKLab -> linear sRGB, NOT clipped (so out-of-gamut colours can be detected)."""
    L, a, b = (np.asarray(v, np.float64) for v in (L, a, b))
    l_, m_, s_ = L + 0.3963377774 * a + 0.2158037573 * b, L - 0.1055613458 * a - 0.0638541728 * b, L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return np.stack([4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
                     -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
                     -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s], -1)


def from_oklab(L, a, b):
    lin = np.clip(_lin(L, a, b), 0, 1)
    srgb = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1 / 2.4) - 0.055)
    return np.clip(np.round(srgb * 255), 0, 255).astype(np.uint8)


def lch(rgb):
    lab = px._to_oklab(np.asarray(rgb, np.uint8)).astype(np.float64)
    return lab[..., 0], np.hypot(lab[..., 1], lab[..., 2]), np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360


def from_lch(L, C, h):
    """OKLCH -> sRGB. If the colour is outside the sRGB gamut its chroma is reduced (lightness and hue are kept),
    instead of clipping, which would shift the lightness and break the shading."""
    L, C, h = (np.asarray(v, np.float64) for v in np.broadcast_arrays(L, C, h))
    cs, sn = np.cos(np.radians(h)), np.sin(np.radians(h))
    inside = lambda c: ((_lin(L, c * cs, c * sn) >= -1e-4) & (_lin(L, c * cs, c * sn) <= 1 + 1e-4)).all(-1)
    lo, hi = np.zeros_like(C), C.copy()
    ok = inside(C)
    for _ in range(16):
        mid = (lo + hi) / 2
        good = inside(mid)
        lo, hi = np.where(good, mid, lo), np.where(good, hi, mid)
    Cf = np.where(ok, C, lo)
    return from_oklab(L, Cf * cs, Cf * sn)


# ---------------- parsing / exporting ----------------
def parse_hex(text):
    toks = re.findall(r"#?[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", text)
    cols = [from_hex(t) for t in toks]
    if not cols:
        raise PaletteError("no colours found (expected one hex colour per line, like ff0044)")
    return _dedupe(cols)


def parse_gpl(text):
    cols = []
    for line in text.splitlines():
        m = re.match(r"^\s*(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})(\s|$)", line)
        if m and not line.lstrip().startswith("#"):
            cols.append([min(255, int(m.group(i))) for i in (1, 2, 3)])
    if not cols:
        raise PaletteError("no colours found in this GIMP palette")
    return _dedupe(cols)


def parse_jasc(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines or not lines[0].startswith("JASC-PAL"):
        raise PaletteError("not a JASC .pal file")
    cols = []
    for l in lines[3:]:
        m = re.match(r"^(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})", l)
        if m:
            cols.append([min(255, int(m.group(i))) for i in (1, 2, 3)])
    if not cols:
        raise PaletteError("no colours found in this .pal file")
    return _dedupe(cols)


def parse_image(data, limit=256):
    im = Image.open(io.BytesIO(data)).convert("RGBA")
    a = np.asarray(im).reshape(-1, 4)
    cols = _dedupe([c[:3] for c in a if c[3] >= 128])  # order of first appearance = the swatch order
    if not cols:
        raise PaletteError("the image has no visible colours")
    if len(cols) > limit:
        raise PaletteError(f"the image has {len(cols)} colours; a palette image should have at most {limit} (one pixel or block per colour)")
    return cols


def parse_any(filename, data):
    ext = Path(filename or "").suffix.lower()
    name = (Path(filename or "palette").stem or "palette")[:40]
    try:
        if ext in (".png", ".gif", ".bmp", ".webp"):
            cols = parse_image(data)
        else:
            text = data.decode("utf-8-sig", "ignore")
            if text.lstrip().startswith("JASC-PAL"):
                cols = parse_jasc(text)
            elif text.lstrip().startswith("GIMP Palette") or ext == ".gpl":
                cols = parse_gpl(text)
            else:
                cols = parse_hex(text)
    except PaletteError:
        raise
    except Exception as e:
        raise PaletteError(f"could not read {filename}: {type(e).__name__}")
    if len(cols) > 1024:
        raise PaletteError("too many colours (max 1024)")
    return {"name": name, "colors": [to_hex(c) for c in cols]}


def export_files(root, name, colors):
    cols = _arr(colors)
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")[:40] or "palette"
    d = Path(root) / "exports" / "palettes"
    d.mkdir(parents=True, exist_ok=True)
    hexes = [to_hex(c)[1:] for c in cols]
    (d / f"{safe}.hex").write_text("\n".join(hexes) + "\n")
    (d / f"{safe}.gpl").write_text("GIMP Palette\nName: %s\nColumns: 8\n#\n" % safe + "\n".join("%3d %3d %3d\t%s" % (*c, h) for c, h in zip(cols, hexes)) + "\n")
    (d / f"{safe}.pal").write_text("JASC-PAL\n0100\n%d\n" % len(cols) + "\n".join("%d %d %d" % tuple(c) for c in cols) + "\n")
    strip = Image.fromarray(cols.reshape(1, -1, 3), "RGB")
    strip.save(d / f"{safe}-1px.png")
    strip.resize((len(cols) * 16, 16), Image.NEAREST).save(d / f"{safe}-swatch.png")
    return {"dir": str(d), "files": [f"{safe}{s}" for s in (".hex", ".gpl", ".pal", "-1px.png", "-swatch.png")]}


# ---------------- your palette library (palettes/*.json) ----------------
def _slug(name):
    s = re.sub(r"[^A-Za-z0-9 _-]+", "", str(name or "")).strip()[:40]
    if not s:
        raise PaletteError("palette name is empty (letters, numbers, space, - and _)")
    return s


def list_user(root):
    d = Path(root) / "palettes"
    out = []
    for f in sorted(d.glob("*.json")) if d.exists() else []:
        try:
            j = json.loads(f.read_text())
            out.append({"name": j["name"], "colors": [to_hex(from_hex(c)) for c in j["colors"]]})
        except Exception:
            continue
    return out


def load_into_px(root):
    """Make saved palettes usable everywhere a palette name is accepted (Generate, Reference, Pixelize...)."""
    for k in [k for k in px.PALETTES if k not in px.BUILTIN_PALETTES]:
        del px.PALETTES[k]
    for p in list_user(root):
        if p["name"] not in px.BUILTIN_PALETTES and p["colors"]:
            px.PALETTES[p["name"]] = _arr(p["colors"])


def save_user(root, name, colors):
    name = _slug(name)
    if name in px.BUILTIN_PALETTES:
        raise PaletteError(f'"{name}" is a built-in palette name; choose another')
    cols = _dedupe(_arr(colors).tolist())
    if not 1 <= len(cols) <= 256:
        raise PaletteError("a palette needs 1-256 colours")
    d = Path(root) / "palettes"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps({"name": name, "colors": [to_hex(c) for c in cols]}))
    load_into_px(root)
    return name


def delete_user(root, name):
    f = Path(root) / "palettes" / f"{_slug(name)}.json"
    if f.exists():
        f.unlink()
    load_into_px(root)


# ---------------- operations on images ----------------
def _rgba(img):
    a = np.asarray(img.convert("RGBA"))
    return a, a[..., 3] >= 128


def _uniq(a, op):
    rgb = a[..., :3][op].astype(np.int64)
    key = (rgb[:, 0] << 16) | (rgb[:, 1] << 8) | rgb[:, 2]
    uk, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
    return np.stack([(uk >> 16) & 255, (uk >> 8) & 255, uk & 255], 1).astype(np.uint8), inv, cnt


def _paint(op, cols_per_pixel):
    out = np.zeros(op.shape + (4,), np.uint8)
    out[op, :3] = cols_per_pixel
    out[op, 3] = 255
    return Image.fromarray(out, "RGBA")


def extract(img, n=0):
    a, op = _rgba(img)
    if not op.any():
        return {"colors": [], "total": 0}
    uniq, inv, cnt = _uniq(a, op)
    total = len(uniq)
    if (n and total > n) or total > 256:
        k = n if n else 64
        px_ = a[..., :3][op]
        pal = px.smart_palette(px_[np.random.RandomState(0).choice(len(px_), min(len(px_), 200000), replace=False)], k)
        idx = px._nearest(px_[:, None, :], pal)[:, 0]
        cnt, uniq = np.bincount(idx, minlength=len(pal)), pal
    order = np.argsort(-cnt, kind="stable")
    return {"colors": [{"hex": to_hex(uniq[i]), "count": int(cnt[i])} for i in order if cnt[i] > 0], "total": total}


def remap(img, pal, dither="none", strength=0.5):
    """Snap every pixel to the nearest palette colour. dither: none | bayer2 | bayer4 | floyd. Returns (image, note)."""
    pal = np.asarray(pal, np.uint8).reshape(-1, 3)
    a, op = _rgba(img)
    H, W = op.shape
    if not op.any() or len(pal) == 0:
        return Image.fromarray(np.zeros((H, W, 4), np.uint8), "RGBA"), "nothing to remap"
    note = ""
    strength = float(np.clip(strength, 0, 1))
    pl = px._to_oklab(pal).astype(np.float32)
    lab = px._to_oklab(a[..., :3]).astype(np.float32)
    if dither == "floyd" and H * W > 200000:
        dither, note = "bayer4", "image is large, used ordered dithering instead of Floyd-Steinberg"
    idx = np.full((H, W), -1, np.int32)
    if dither in ("bayer2", "bayer4"):
        n = 2 if dither == "bayer2" else 4
        thr = (BAYER[n] + 0.5) / BAYER[n].size - 0.5
        bias = thr[np.arange(H)[:, None] % n, np.arange(W)[None, :] % n]
        v = lab.copy()
        v[..., 0] += bias * strength * 0.30
        vv = v[op]
        best = np.empty(len(vv), np.int32)
        for s in range(0, len(vv), 50000):
            best[s:s + 50000] = ((vv[s:s + 50000, None, :] - pl[None]) ** 2).sum(-1).argmin(1)
        idx[op] = best
    elif dither == "floyd":
        work = lab.copy()
        for y in range(H):
            for x in range(W):
                if not op[y, x]:
                    continue
                v = work[y, x]
                k = int(((pl - v) ** 2).sum(1).argmin())
                idx[y, x] = k
                e = (v - pl[k]) * strength
                if x + 1 < W: work[y, x + 1] += e * 7 / 16
                if y + 1 < H:
                    if x > 0: work[y + 1, x - 1] += e * 3 / 16
                    work[y + 1, x] += e * 5 / 16
                    if x + 1 < W: work[y + 1, x + 1] += e / 16
    else:
        idx[op] = px._nearest(a[..., :3][op][:, None, :], pal)[:, 0]
    return _paint(op, pal[idx[op]]), note


def merge_similar(img, delta=0.05):
    """Merge colours closer than `delta` (OKLab) into the more common one. Returns (image, palette hex list)."""
    a, op = _rgba(img)
    if not op.any():
        return img.convert("RGBA"), []
    uniq, inv, cnt = _uniq(a, op)
    lab = px._to_oklab(uniq).astype(np.float64)
    kept, mapto = [], np.zeros(len(uniq), np.int32)
    for i in np.argsort(-cnt, kind="stable"):
        hit = next((j for j, k in enumerate(kept) if np.sqrt(((lab[i] - lab[k]) ** 2).sum()) < delta), None)
        if hit is None:
            kept.append(i)
            hit = len(kept) - 1
        mapto[i] = hit
    newcols = uniq[np.array(kept)]
    return _paint(op, newcols[mapto[inv]]), [to_hex(c) for c in newcols]


def variants(img, shifts, protect=(), chroma=1.0, keep_dark=True):
    """Hue-rotated copies (OKLCH: lightness is kept, so shading stays correct). Protected colours never change."""
    a, op = _rgba(img)
    if not op.any():
        return []
    uniq, inv, cnt = _uniq(a, op)
    L, C, h = lch(uniq)
    prot = np.zeros(len(uniq), bool)
    keys = {tuple(c) for c in _arr(list(protect)).tolist()} if len(protect) else set()
    for i, c in enumerate(uniq):
        prot[i] = tuple(int(v) for v in c) in keys
    if keep_dark:
        prot |= L < 0.30
    out = []
    for s in shifts:
        new = from_lch(L, np.clip(C * float(chroma), 0, 0.4), (h + float(s)) % 360)
        new[prot] = uniq[prot]
        pal = _dedupe(new.tolist())
        out.append({"shift": float(s), "image": _paint(op, new[inv]), "palette": [to_hex(c) for c in pal]})
    return out


def ramp(rgb, n=5, spread=1.0):
    """Shading ramp dark -> light around a colour: lightness steps, shadows drift to blue-violet, highlights to yellow."""
    n = int(np.clip(n, 2, 9))
    L0, C0, h0 = (float(v[0]) for v in lch(np.array([rgb], np.uint8)))
    out = []
    for t in np.linspace(-1, 1, n):
        target = 265.0 if t < 0 else 95.0
        dh = ((target - h0 + 180) % 360) - 180
        h = h0 + np.sign(dh) * min(abs(dh), 30.0) * abs(t) if C0 > 0.02 else h0
        C = C0 * (1 - 0.22 * max(t, 0) - 0.08 * max(-t, 0))
        L = float(np.clip(L0 + t * 0.20 * spread, 0.06, 0.97))
        out.append(from_lch(np.array(L), np.array(C), np.array(h)).tolist())
    if n % 2:
        out[n // 2] = [int(v) for v in rgb]
    return [to_hex(c) for c in _dedupe(out)]


def sort_colors(cols, key="lightness"):
    arr = _arr(cols)
    L, C, h = lch(arr)
    if key == "hue":
        order = sorted(range(len(arr)), key=lambda i: (0, L[i], 0) if C[i] < 0.03 else (1, h[i], L[i]))
    else:
        order = sorted(range(len(arr)), key=lambda i: L[i])
    return [to_hex(arr[i]) for i in order]
