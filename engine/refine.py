"""AI cleanup of rig-animated frames: repaint only small areas around moving joints (SDXL inpaint at low strength),
then snap back to the sprite's own palette. Everything outside the masks is left byte-identical."""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from . import generate as gen, rig

CANDIDATE_BG = {"white": (255, 255, 255), "light gray": (204, 204, 204), "green": (0, 255, 0), "magenta": (255, 0, 255)}


def seam_mask(frame, jpos, radius):
    """Discs around each moving joint, limited to the (slightly dilated) silhouette so gaps inside it are included."""
    a = np.asarray(frame)[..., 3] > 0
    h, w = a.shape
    yy, xx = np.mgrid[0:h, 0:w]
    m = np.zeros((h, w), bool)
    for x, y in jpos.values():
        m |= (xx + .5 - x) ** 2 + (yy + .5 - y) ** 2 <= radius ** 2
    return m & ndi.binary_dilation(a, iterations=2)


def _nearest_palette(rgb, cols, chunk=120000):
    flat = rgb.reshape(-1, 3).astype(np.int32)
    c = cols.astype(np.int32)
    idx = np.empty(len(flat), np.int32)
    for s in range(0, len(flat), chunk):
        d = ((flat[s:s + chunk, None, :] - c[None]) ** 2).sum(-1)
        idx[s:s + chunk] = d.argmin(1)
    return idx.reshape(rgb.shape[:2])


def refine(frames, meta, sprite, ckpt, lora, lora_w, lora_dir, prompt, negative="", strength=0.45, steps=22, cfg=7.0,
           seed=-1, radius=0, size=1024, inpaint_fn=None):
    inpaint_fn = inpaint_fn or gen.inpaint
    arr = np.asarray(sprite.convert("RGBA"))
    op = arr[..., 3] >= 128
    cols = np.unique(arr[op][:, :3], axis=0) if op.any() else np.zeros((0, 3), np.uint8)
    use_pal = 0 < len(cols) <= 96
    if use_pal:  # background colour that is as far from the sprite's colours as possible
        bgname = max(CANDIDATE_BG, key=lambda n: ((cols.astype(int) - np.array(CANDIDATE_BG[n])) ** 2).sum(1).min())
    else:
        bgname = "magenta"
    bg = np.array(CANDIDATE_BG[bgname])
    keys = ((cols[:, 0].astype(np.int64) << 16) | (cols[:, 1].astype(np.int64) << 8) | cols[:, 2].astype(np.int64)) if use_pal else None
    w, h = frames[0].size
    k = max(1, size // max(w, h))
    ox, oy = (size - w * k) // 2, (size - h * k) // 2
    sprite_h = h - 2 * meta["pad"]
    r = radius if radius > 0 else max(3.0, .09 * sprite_h)
    if seed is None or seed < 0:
        seed = int(np.random.randint(0, 2**31 - 1))
    out, reverted, reverted_idx = [], 0, []
    for i, f in enumerate(frames):
        m = seam_mask(f, meta["joints"][i], r)
        if not m.any():
            out.append(f)
            continue
        big = f.resize((w * k, h * k), Image.NEAREST)
        img = Image.new("RGB", (size, size), tuple(int(v) for v in bg))
        img.paste(big.convert("RGB"), (ox, oy), big)
        mk = Image.new("L", (size, size), 0)
        mk.paste(Image.fromarray((m * 255).astype(np.uint8)).resize((w * k, h * k), Image.NEAREST), (ox, oy))
        res = inpaint_fn(ckpt, lora, lora_w, lora_dir, prompt, negative, img, mk, strength, steps, cfg, seed, bgname)
        crop = np.asarray(res.convert("RGB"))[oy:oy + h * k, ox:ox + w * k].astype(np.int16)
        is_bg = np.abs(crop - bg).max(-1) <= 70
        rgb = cols[_nearest_palette(crop, cols)] if use_pal else crop.astype(np.uint8)
        hi = Image.fromarray(np.dstack([rgb, np.where(is_bg, 0, 255)]).astype(np.uint8), "RGBA")
        new = np.asarray(rig._downsample(hi, k, keys, cols, use_pal))
        fa = np.asarray(f).copy()
        before, after = int(((fa[..., 3] > 0) & m).sum()), int(((new[..., 3] > 0) & m).sum())
        if after < .6 * before or after > 1.4 * before + 12:  # AI wandered off: keep the rig frame
            reverted += 1
            reverted_idx.append(i)
            out.append(f)
            continue
        fa[m] = new[m]
        out.append(Image.fromarray(fa, "RGBA"))
    return out, {"bg": bgname, "seed": seed, "reverted": reverted, "reverted_idx": reverted_idx, "radius": round(r, 1)}


def redo_frames(entry, idx, seed, strength, inpaint_fn=None):
    """Re-run the AI only for frames `idx` (from the original rig frames, new seed) and merge into the cached result.
    entry = {"raw", "imgs", "meta", "cfg"} as stored by the animate endpoint. Returns (all frames, info for idx)."""
    c = entry["cfg"]
    sub = [entry["raw"][i] for i in idx]
    meta2 = {**entry["meta"], "joints": [entry["meta"]["joints"][i] for i in idx]}
    new, info = refine(sub, meta2, c["sprite"], c["ckpt"], c["lora"], c["lora_w"], c["lora_dir"], c["character"],
                       c["negative"], strength, c["steps"], c["cfg"], seed, c["radius"], inpaint_fn=inpaint_fn)
    imgs = list(entry["imgs"])
    for j, i in enumerate(idx):
        imgs[i] = new[j]
    entry["imgs"] = imgs
    info["reverted_idx"] = [idx[j] for j in info["reverted_idx"]]  # back to whole-animation frame numbers
    return imgs, info
