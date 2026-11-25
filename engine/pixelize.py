"""Turn blurry AI 'pixel style' images into real pixel-grid sprites. No model dependency."""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def _hex(items):
    return np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in items], dtype=np.uint8)


PALETTES = {
    "pico8": _hex("000000 1D2B53 7E2553 008751 AB5236 5F574F C2C3C7 FFF1E8 FF004D FFA300 FFEC27 00E436 29ADFF 83769C FF77A8 FFCCAA".split()),
    "gameboy": _hex("0f380f 306230 8bac0f 9bbc0f".split()),
    "cga16": _hex("000000 0000aa 00aa00 00aaaa aa0000 aa00aa aa5500 aaaaaa 555555 5555ff 55ff55 55ffff ff5555 ff55ff ffff55 ffffff".split()),
    "c64": _hex("000000 ffffff 813338 75cec8 8e3c97 56ac4d 2e2c9b edf171 8e5029 553800 c46c71 4a4a4a 7b7b7b a9ff9f 706deb b2b2b2".split()),
    "sweetie16": _hex("1a1c2c 5d275d b13e53 ef7d57 ffcd75 a7f070 38b764 257179 29366f 3b5dc9 41a6f6 73eff7 f4f4f4 94b0c2 566c86 333c57".split()),
}
BUILTIN_PALETTES = list(PALETTES)


def remove_bg(img, tol=40):
    """Flood-style key: border-connected pixels close to the dominant border colour become transparent."""
    img = img.convert("RGBA")
    a = np.asarray(img)[..., 3]
    if a.min() < 250:  # already has transparency
        return img
    rgb = np.asarray(img.convert("RGB")).astype(np.int16)
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    q = border // 16
    keys, counts = np.unique(q, axis=0, return_counts=True)
    bg = border[(q == keys[counts.argmax()]).all(1)].mean(0)
    cand = np.abs(rgb - bg).max(2) <= tol
    lab, _ = ndi.label(cand)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bgmask = np.isin(lab, list(edge))
    # trim 1px halo of background colour mixed into the edge
    bgmask = ndi.binary_dilation(bgmask, iterations=1) & (np.abs(rgb - bg).max(2) <= tol * 2.2) | bgmask
    out = img.copy()
    out.putalpha(Image.fromarray(np.where(bgmask, 0, 255).astype(np.uint8)))
    return out


def crop_to_content(img, pad=2):
    bb = img.getchannel("A").getbbox()
    if not bb:
        return img
    l, t, r, b = bb
    return img.crop((max(l - pad, 0), max(t - pad, 0), min(r + pad, img.width), min(b + pad, img.height)))


def detect_grid(img, max_s=32):
    """Estimate the 'pixel' block size from edge periodicity. Returns (size, off_x, off_y) or None."""
    g = np.asarray(img.convert("L")).astype(np.float32)
    px = np.abs(np.diff(g, axis=1)).sum(0)
    py = np.abs(np.diff(g, axis=0)).sum(1)

    def score(p, s):
        h = s // 6  # blur spreads each edge over a few px, so integrate a small window
        q = np.convolve(p, np.ones(2 * h + 1), mode="same") if h else p
        tot = p.sum() + 1e-6
        sums = [q[o::s].sum() for o in range(s)]
        o = int(np.argmax(sums))
        return sums[o] / tot - (2 * h + 1) / s, (o + 1) % s, sums[o] / tot

    res = {}
    for s in range(2, min(max_s, min(g.shape) // 4) + 1):
        sx, ox, fx = score(px, s)
        sy, oy, fy = score(py, s)
        res[s] = ((sx + sy) / 2, ox, oy, (fx + fy) / 2)
    if not res:
        return None
    s = max(res, key=lambda k: res[k][0])
    if res[s][0] < 0.2:
        return None
    # sub-harmonic check: on a clean upscale 4 px "fits" as well as the true 8 px, so prefer the largest multiple
    # that still captures (almost) all of the edge energy; real finer detail loses energy at the larger size.
    for m in (4, 3, 2):
        s2 = s * m
        if s2 in res and res[s2][3] >= res[s][3] * 0.97 and s2 <= max_s:
            return s2, res[s2][1], res[s2][2]
    return s, res[s][1], res[s][2]


def palette_from_sprite(sprite, max_colors=64):
    """Exact colour set of a sprite (None if it isn't a real low-colour sprite)."""
    arr = np.asarray(sprite.convert("RGBA")).reshape(-1, 4)
    cols = np.unique(arr[arr[:, 3] >= 128][:, :3], axis=0)
    return cols.astype(np.uint8) if 0 < len(cols) <= max_colors else None


def quantize(sprite, colors=16, palette="none"):
    """palette: preset name, 'none', or an (N,3) uint8 array (e.g. from a reference sprite)."""
    arr = np.asarray(sprite).copy()
    a = arr[..., 3]
    rgb = arr[..., :3]
    opaque = a >= 128
    if not opaque.any():
        return sprite
    fill = rgb[opaque].mean(0).astype(np.uint8)
    rgb = np.where(opaque[..., None], rgb, fill)  # transparent junk must not eat palette slots
    pal = PALETTES.get(palette) if isinstance(palette, str) else palette
    if pal is not None:
        flat = rgb.reshape(-1, 3).astype(int)
        idx = ((flat[:, None, :] - pal.astype(int)[None]) ** 2).sum(2).argmin(1)
        out = pal[idx].reshape(rgb.shape)
    elif colors and colors > 0:
        q = Image.fromarray(rgb.astype(np.uint8)).quantize(colors=int(colors), method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        out = np.asarray(q.convert("RGB"))
    else:
        out = rgb
    return Image.fromarray(np.dstack([out, a]).astype(np.uint8), "RGBA")


def cleanup(sprite, alpha_thresh=128, min_blob=3):
    arr = np.asarray(sprite).copy()
    mask = arr[..., 3] >= alpha_thresh
    lab, n = ndi.label(mask, structure=np.ones((3, 3)))
    if n:
        sizes = ndi.sum(mask, lab, range(1, n + 1))
        for i, sz in enumerate(sizes, 1):
            if sz < min_blob:
                mask[lab == i] = False
    arr[..., 3] = np.where(mask, 255, 0)
    arr[~mask, :3] = 0
    return Image.fromarray(arr, "RGBA")


def drop_ground_shadow(sprite):
    """Remove a wide, flat, low-saturation blob sitting under the feet (typical AI 'ground shadow')."""
    arr = np.asarray(sprite).copy()
    a = arr[..., 3] >= 128
    if not a.any():
        return sprite
    ys, xs = np.where(a)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    H, W = y1 - y0 + 1, x1 - x0 + 1
    rgb = arr[..., :3].astype(int)
    low = a & ((rgb.max(2) - rgb.min(2)) < 20)
    lab, n = ndi.label(low, structure=np.ones((3, 3)))
    for i in range(1, n + 1):
        m = lab == i
        yy, xx = np.where(m)
        h, w = yy.max() - yy.min() + 1, xx.max() - xx.min() + 1
        if yy.max() >= y1 - 1 and w >= 0.3 * W and h <= 0.22 * H and yy.min() > y0 + 0.7 * H and m.sum() / (w * h) > 0.45:
            arr[m] = 0
    return Image.fromarray(arr, "RGBA")


def _pixelize_legacy(img, mode="fixed", size=64, colors=16, palette="none", do_remove_bg=True, bg_tol=40, alpha_thresh=128,
                     remove_shadow=True):
    """mode: 'fixed' = long side becomes `size` px; 'auto' = detect the grid size already baked into the image."""
    info = {}
    img = img.convert("RGBA")
    if do_remove_bg:
        img = remove_bg(img, bg_tol)
    if mode == "canvas":  # fixed-scale square canvas: no cropping, so every frame keeps the same scale/position
        sprite = img.resize((size, size), Image.BOX)
        sprite = quantize(sprite, colors, palette)
        if remove_shadow:
            sprite = drop_ground_shadow(sprite)
        sprite = cleanup(sprite, alpha_thresh)
        info["size"] = sprite.size
        return sprite, info
    img = crop_to_content(img)
    w, h = img.size
    if mode == "auto":
        grid = detect_grid(img)
        if grid:
            s, ox, oy = grid
            img = img.crop((ox, oy, w, h))
            w, h = img.size
            tw, th = max(w // s, 1), max(h // s, 1)
            info["grid"] = s
        else:
            info["grid"] = None
            info["note"] = "no clear grid found, used fixed size instead"
            mode = "fixed"
    if mode == "fixed":
        k = size / max(w, h)
        tw, th = max(round(w * k), 1), max(round(h * k), 1)
    sprite = img.resize((tw, th), Image.BOX)
    sprite = quantize(sprite, colors, palette)
    if remove_shadow:
        sprite = drop_ground_shadow(sprite)
    sprite = cleanup(sprite, alpha_thresh)
    info["size"] = sprite.size
    return sprite, info


# ======================= crisp pipeline (quantize first, then pick the dominant colour per cell) =======================
def _to_oklab(rgb):
    c = rgb.astype(np.float32) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    l = 0.4122214708 * c[..., 0] + 0.5363325363 * c[..., 1] + 0.0514459929 * c[..., 2]
    m = 0.2119034982 * c[..., 0] + 0.6806995451 * c[..., 1] + 0.1073969566 * c[..., 2]
    s = 0.0883024619 * c[..., 0] + 0.2817188376 * c[..., 1] + 0.6299787005 * c[..., 2]
    l, m, s = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return np.stack([0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                     1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                     0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s], -1)


def smart_palette(px, k, iters=10):
    """Perceptual (OKLab) k-means over the image's own colours. Each palette entry is a colour that really occurs
    in the image (the cluster's medoid), so no muddy averages end up in the palette."""
    px = np.asarray(px, np.uint8).reshape(-1, 3)
    key = (px[:, 0].astype(np.int64) << 16) | (px[:, 1].astype(np.int64) << 8) | px[:, 2].astype(np.int64)
    uk, counts = np.unique(key, return_counts=True)
    uniq = np.stack([(uk >> 16) & 255, (uk >> 8) & 255, uk & 255], 1).astype(np.uint8)
    if len(uniq) <= k:
        return uniq
    lab = _to_oklab(uniq)
    w = counts.astype(np.float32)
    centers = [lab[np.argmax(w)]]
    d = ((lab - centers[0]) ** 2).sum(1)
    for _ in range(1, k):
        i = int(np.argmax(d * np.sqrt(w)))  # far from existing centres, but not just rare noise
        centers.append(lab[i])
        d = np.minimum(d, ((lab - lab[i]) ** 2).sum(1))
    C = np.array(centers, np.float32)
    for _ in range(iters):
        a = ((lab[:, None, :] - C[None]) ** 2).sum(-1).argmin(1)
        for j in range(k):
            m = a == j
            if m.any():
                C[j] = (lab[m] * w[m, None]).sum(0) / w[m].sum()
    D = ((lab[:, None, :] - C[None]) ** 2).sum(-1)
    a = D.argmin(1)
    out = [uniq[m[np.argmin(D[m, j])]] for j in range(k) for m in [np.where(a == j)[0]] if len(m)]
    return np.unique(np.array(out, np.uint8), axis=0)


def _nearest(rgb, pal):
    """Index of the perceptually nearest palette colour for every pixel of an (H, W, 3) array."""
    flat = rgb.reshape(-1, 3).astype(np.int64)
    key = (flat[:, 0] << 16) | (flat[:, 1] << 8) | flat[:, 2]
    uk, inv = np.unique(key, return_inverse=True)
    u = np.stack([(uk >> 16) & 255, (uk >> 8) & 255, uk & 255], 1).astype(np.uint8)
    lp = _to_oklab(pal)
    best = np.empty(len(u), np.int32)
    for s in range(0, len(u), 60000):
        best[s:s + 60000] = ((_to_oklab(u[s:s + 60000])[:, None, :] - lp[None]) ** 2).sum(-1).argmin(1)
    return best[inv].reshape(rgb.shape[:2])


def _mode_down(idx, bh, bw, K):
    """Most common palette index in every bh x bw block (-1 = transparent; a block is opaque if >= half is)."""
    H, W = idx.shape
    h, w = H // bh, W // bw
    blocks = idx[:h * bh, :w * bw].reshape(h, bh, w, bw).transpose(0, 2, 1, 3).reshape(h, w, bh * bw)
    counts = np.stack([(blocks == k).sum(-1) for k in range(K)], -1)
    return np.where((blocks >= 0).sum(-1) * 2 >= bh * bw, counts.argmax(-1), -1)


def _choose_palette(img, colors, palette):
    pal = PALETTES.get(palette) if isinstance(palette, str) else palette
    if pal is not None:
        return pal
    a = np.asarray(img.convert("RGBA"))
    px = a[..., :3][a[..., 3] >= 128]
    if len(px) == 0:
        return np.zeros((1, 3), np.uint8)
    if len(px) > 200000:
        px = px[np.random.RandomState(0).choice(len(px), 200000, replace=False)]
    return smart_palette(px, int(colors) if colors and colors > 0 else 256)


def crisp_reduce(img, tw, th, S, pal):
    """Reduce img to tw x th: sample S x S points per output pixel (nearest, so no blended colours), snap them to the
    palette, then keep the dominant colour of each cell."""
    img = img.convert("RGBA")
    hi = img if img.size == (tw * S, th * S) else img.resize((tw * S, th * S), Image.NEAREST)
    a = np.asarray(hi)
    op = a[..., 3] >= 128
    idx = np.full(op.shape, -1, np.int32)
    if op.any():
        idx[op] = _nearest(a[op][:, None, :3], pal)[:, 0]
    low = _mode_down(idx, S, S, len(pal))
    out = np.zeros((th, tw, 4), np.uint8)
    m = low >= 0
    out[m, :3] = pal[low[m]]
    out[m, 3] = 255
    return Image.fromarray(out, "RGBA")


def despeckle(sprite, thresh=0.09):
    """Replace single stray pixels that nearly match the colour all around them (dither / AI noise). Real details
    (eye highlights, rivets) differ strongly from their surroundings, so they are left alone."""
    a = np.asarray(sprite).copy()
    op = a[..., 3] > 0
    key = np.where(op, (a[..., 0].astype(np.int64) << 16) | (a[..., 1].astype(np.int64) << 8) | a[..., 2].astype(np.int64), -1)
    P = np.pad(key, 1, constant_values=-1)
    H, W = key.shape
    N = np.stack([P[dy:dy + H, dx:dx + W] for dy in range(3) for dx in range(3) if (dy, dx) != (1, 1)])
    alone = op & ((N == key).sum(0) == 0)
    ys, xs = np.where(alone)
    for y, x in zip(ys, xs):
        nb = N[:, y, x]
        nb = nb[nb >= 0]
        if len(nb) < 6:
            continue
        vals, cnt = np.unique(nb, return_counts=True)
        j = int(cnt.argmax())
        if cnt[j] < 5:
            continue
        new = np.array([(vals[j] >> 16) & 255, (vals[j] >> 8) & 255, vals[j] & 255], np.uint8)
        if np.sqrt(((_to_oklab(new) - _to_oklab(a[y, x, :3])) ** 2).sum()) < thresh:
            a[y, x, :3] = new
    return Image.fromarray(a, "RGBA")


def add_outline(sprite, mode="selective", expand=True):
    """1 px outline around the silhouette. 'dark' = one dark colour; 'selective' = a darkened copy of the adjacent colour."""
    a = np.asarray(sprite)
    if expand:
        a = np.pad(a, ((1, 1), (1, 1), (0, 0)))
    a = a.copy()
    op = a[..., 3] > 0
    ring = ndi.binary_dilation(op, structure=ndi.generate_binary_structure(2, 1)) & ~op
    if not ring.any() or not op.any():
        return Image.fromarray(a, "RGBA")
    if mode == "dark":
        cols = a[op][:, :3].astype(int)
        lum = cols @ np.array([.299, .587, .114])
        c = cols[lum.argmin()]
        col = c if lum.min() < 80 else np.array([20, 16, 28])
        a[ring, :3] = col
    else:
        iy, ix = ndi.distance_transform_edt(~op, return_indices=True)[1]
        near = a[iy, ix, :3].astype(np.float32) * 0.38
        a[ring, :3] = near[ring].astype(np.uint8)
    a[ring, 3] = 255
    return Image.fromarray(a, "RGBA")


def pixelize(img, mode="fixed", size=64, colors=16, palette="none", do_remove_bg=True, bg_tol=40, alpha_thresh=128,
             remove_shadow=True, crisp=True, clean=True, outline="none"):
    """mode: 'fixed' = long side becomes `size` px; 'auto' = use the pixel grid baked into the image; 'canvas' = square
    canvas of `size` px (fixed scale, no cropping). crisp=False uses the old average-then-quantize converter."""
    if not crisp:
        return _pixelize_legacy(img, mode, size, colors, palette, do_remove_bg, bg_tol, alpha_thresh, remove_shadow)
    info = {}
    img = img.convert("RGBA")
    if do_remove_bg:
        img = remove_bg(img, bg_tol)
    expand = True
    if mode == "canvas":
        expand = False
        pal = _choose_palette(img, colors, palette)
        S = img.width // size if img.width == img.height and img.width % size == 0 and img.width // size >= 2 else 6
        sprite = crisp_reduce(img, size, size, S, pal)  # an exact integer ratio keeps the model's own pixel blocks
    else:
        img = crop_to_content(img)
        w, h = img.size
        pal = _choose_palette(img, colors, palette)
        grid = detect_grid(img)
        native = None
        if grid:
            s, ox, oy = grid
            nw, nh = (w - ox) // s, (h - oy) // s
            if nw >= 1 and nh >= 1:
                native = crisp_reduce(img.crop((ox, oy, ox + nw * s, oy + nh * s)), nw, nh, s, pal)
                info["grid"] = s
        if mode == "auto" and native is None:
            info["grid"], info["note"] = None, "no clear grid found, used fixed size instead"
        if mode == "auto" and native is not None:
            sprite = native
        else:
            base = native if native is not None else img
            bw, bh = base.size
            k = size / max(bw, bh)
            if native is not None and k >= 1:
                sprite = native
                info["note"] = f"native pixel grid is {max(bw, bh)} px, which is not larger than the target, so it was kept"
            else:
                sprite = crisp_reduce(base, max(round(bw * k), 1), max(round(bh * k), 1), 6, pal)
    if remove_shadow:
        sprite = drop_ground_shadow(sprite)
    if clean:
        sprite = despeckle(sprite)
    if outline in ("dark", "selective"):
        sprite = add_outline(sprite, outline, expand)
    sprite = cleanup(sprite, alpha_thresh)
    info["size"] = sprite.size
    return sprite, info
