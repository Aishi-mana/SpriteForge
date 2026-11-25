"""Sprite templates: a neutral mannequin ("dummy") with a matching rig, and generation of a sprite that keeps the template's
exact size, silhouette and alignment while taking its look from a reference image (SDXL inpaint inside the silhouette + IP-Adapter)."""
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from . import generate as gen, pixelize as px
from .refine import CANDIDATE_BG

OUT = (50, 52, 66, 255)
COL = {"head": (205, 208, 218, 255), "neck": (178, 182, 196, 255), "torso": (150, 156, 172, 255), "uarm": (170, 175, 190, 255),
       "farm": (186, 191, 205, 255), "hand": (212, 215, 226, 255), "thigh": (124, 130, 150, 255), "shin": (140, 146, 166, 255),
       "foot": (200, 203, 216, 255), "far": (112, 118, 138, 255), "headback": (150, 152, 168, 255)}
STYLES = {  # fractions of the usable height / width
    "normal": dict(head_h=.14, head_w=.13, neck=.025, torso=.30, legs=.43, arm=.40, sh=.15, hip=.09, aw=.075, lw=.10),
    "chibi": dict(head_h=.36, head_w=.36, neck=.02, torso=.22, legs=.27, arm=.28, sh=.15, hip=.10, aw=.08, lw=.10)}


VIEWS = ("front", "back", "side", "diag", "diag_back")  # south, north, east, south-east, north-east (the others are mirrors)
BONE = {"torso": 0, "head": 1, "l_arm_u": 2, "l_arm_l": 3, "r_arm_u": 4, "r_arm_l": 5, "l_leg_u": 6, "l_leg_l": 7, "r_leg_u": 8, "r_leg_l": 9}


def make_dummy(height=64, style="normal", view="front"):
    """Returns (RGBA sprite, joints, overrides). `overrides` is an exact pixel -> bone assignment (the dummy knows which shape
    drew every pixel), so even the side view, where limbs overlap the torso, rigs perfectly. Limbs are shaded differently so their
    structure reads for the AI."""
    H = int(np.clip(height, 32, 128))
    s = STYLES.get(style, STYLES["normal"])
    m = max(1, round(H * .03))
    Hu = H - 2 * m
    f = lambda k: s[k] * Hu
    view = view if view in VIEWS else "front"
    hc = COL["headback"] if view in ("back", "diag_back") else COL["head"]  # the back of the head reads differently from the face
    ext = (f("sh") + f("aw") + .03 * Hu) if view != "side" else (max(f("head_w") * .8, f("sh") * .8) + .09 * Hu)
    W = int(2 * np.ceil(ext) + 2 * m)
    W += W % 2
    img, lab = Image.new("RGBA", (W, H), (0, 0, 0, 0)), Image.new("L", (W, H), 255)
    d, dl = ImageDraw.Draw(img), ImageDraw.Draw(lab)
    cx = W / 2

    def R(x0, y0, x1, y1, c, bone):
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        box = [x0, y0, max(x1, x0 + 1) - 1, max(y1, y0 + 1) - 1]  # never smaller than one pixel
        d.rectangle(box, fill=c, outline=OUT)
        dl.rectangle(box, fill=BONE[bone], outline=BONE[bone])

    def E(x0, y0, x1, y1, c, bone):
        box = [int(x0), int(y0), max(int(x1), int(x0) + 1), max(int(y1), int(y0) + 1)]
        d.ellipse(box, fill=c, outline=OUT)
        dl.ellipse(box, fill=BONE[bone], outline=BONE[bone])

    y_top = m
    y_neck = y_top + f("head_h")
    y_sh = y_neck + f("neck")
    y_hip = y_sh + f("torso")
    y_sole = H - m
    foot = max(1, round(.04 * Hu))
    y_ank = y_sole - foot
    knee = (y_hip + y_ank) / 2
    arm_end = y_sh + f("arm")
    elbow = (y_sh + arm_end) / 2
    sh, hip, aw, lw = f("sh"), f("hip"), max(2, f("aw")), max(2, f("lw"))
    gap = 1
    if view in ("front", "back"):
        lw = min(lw, hip - gap)
        for sx, p in ((-1, "l"), (1, "r")):
            x0, x1 = (cx - hip, cx - gap) if sx < 0 else (cx + gap, cx + hip)
            R(x0, y_hip - 1, x1, knee, COL["thigh"], f"{p}_leg_u"); R(x0, knee - 1, x1, y_ank, COL["shin"], f"{p}_leg_l")
            R((x0 - foot) if sx < 0 else x0, y_ank - 1, x1 if sx < 0 else (x1 + foot), y_sole, COL["foot"], f"{p}_leg_l")
        poly = [(cx - sh, y_sh), (cx + sh - 1, y_sh), (cx + hip - 1, y_hip), (cx - hip, y_hip)]
        d.polygon(poly, fill=COL["torso"], outline=OUT); dl.polygon(poly, fill=BONE["torso"], outline=BONE["torso"])
        for sx, p in ((-1, "l"), (1, "r")):
            ax0 = cx - sh - aw if sx < 0 else cx + sh
            R(ax0, y_sh, ax0 + aw, elbow, COL["uarm"], f"{p}_arm_u"); R(ax0, elbow - 1, ax0 + aw, arm_end - foot, COL["farm"], f"{p}_arm_l")
            R(ax0, arm_end - foot - 1, ax0 + aw, arm_end, COL["hand"], f"{p}_arm_l")
        nw = max(1.5, f("head_w") * .22)
        R(cx - nw, y_neck - 1, cx + nw, y_sh + 1, COL["neck"], "head")
        E(cx - f("head_w") / 2, y_top, cx + f("head_w") / 2 - 1, y_neck, hc, "head")
        lxo = (hip + gap) / 2
        J = {"head": [cx - .5, y_top + max(1.5, .3 * f("head_h"))], "neck": [cx, y_neck], "pelvis": [cx, y_hip - 1]}
        for sx, p in ((-1, "l"), (1, "r")):
            axc = cx + sx * (sh + aw / 2)
            J[f"{p}_shoulder"] = [cx + sx * (sh - 1.5), y_sh + 1]; J[f"{p}_elbow"] = [axc, elbow]; J[f"{p}_wrist"] = [axc, arm_end - foot]
            J[f"{p}_hip"] = [cx + sx * lxo, y_hip]; J[f"{p}_knee"] = [cx + sx * lxo, knee]; J[f"{p}_ankle"] = [cx + sx * lxo, y_ank]
    elif view == "side":  # side view, facing right: "l_" = far side (screen-left), "r_" = near side
        off = max(2, round(.04 * Hu))
        tw = max(5, f("sh") * (1.35 if style == "chibi" else 1.25), 2 * off + aw + 4)  # always deeper than the arms' footprint, so the torso shows
        lw = min(lw, tw)
        toe = max(foot * 2, round(.07 * Hu))
        for sx, p in ((-1, "l"), (1, "r")):  # far leg first, near leg on top
            lx = cx - lw / 2 + sx * off
            c1, c2 = (COL["far"], COL["far"]) if sx < 0 else (COL["thigh"], COL["shin"])
            R(lx, y_hip - 1, lx + lw, knee, c1, f"{p}_leg_u"); R(lx, knee - 1, lx + lw, y_ank, c2, f"{p}_leg_l")
            R(lx, y_ank - 1, lx + lw + toe, y_sole, COL["foot"], f"{p}_leg_l")
        R(cx - tw / 2, y_sh, cx + tw / 2, y_hip, COL["torso"], "torso")
        for sx, p in ((-1, "l"), (1, "r")):
            ax = cx - aw / 2 + sx * off
            cu, cf = (COL["far"], COL["far"]) if sx < 0 else (COL["uarm"], COL["farm"])
            R(ax, y_sh, ax + aw, elbow, cu, f"{p}_arm_u"); R(ax, elbow - 1, ax + aw, arm_end - foot, cf, f"{p}_arm_l")
            R(ax, arm_end - foot - 1, ax + aw, arm_end, COL["hand"], f"{p}_arm_l")
        R(cx - .5, y_neck - 1, cx + 2.5, y_sh + 1, COL["neck"], "head")
        hw = f("head_w")
        E(cx - hw / 2 + 1, y_top, cx + hw / 2, y_neck, COL["head"], "head")
        R(cx + hw / 2, y_top + f("head_h") * .5, cx + hw / 2 + max(1, round(.02 * Hu)), y_top + f("head_h") * .62, COL["head"], "head")  # nose
        J = {"head": [cx + .5, y_top + max(1.5, .3 * f("head_h"))], "neck": [cx + 1, y_neck], "pelvis": [cx, y_hip - 1]}
        for sx, p in ((-1, "l"), (1, "r")):
            c = cx + sx * off
            J[f"{p}_shoulder"] = [c, y_sh + 1]; J[f"{p}_elbow"] = [c, elbow]; J[f"{p}_wrist"] = [c, arm_end - foot]
            J[f"{p}_hip"] = [c, y_hip]; J[f"{p}_knee"] = [c, knee]; J[f"{p}_ankle"] = [c, y_ank]
    else:  # three-quarter view, facing right (south-east, or north-east with the darker "back of head"): between front and side
        off = max(2, round(.04 * Hu))
        tw_side = max(5, f("sh") * (1.35 if style == "chibi" else 1.25), 2 * off + aw + 4)
        tw = (2 * sh + tw_side) / 2
        lc = ((hip + gap) / 2 + off) / 2
        ac = ((sh + aw / 2) + off) / 2
        lw_d = max(2, min(lw, 2 * lc - 1))
        toe = max(foot * 1.5, round(.05 * Hu))
        for sx, p in ((-1, "l"), (1, "r")):  # far leg first, near leg on top
            x0 = cx + sx * lc - lw_d / 2
            c1, c2 = (COL["far"], COL["far"]) if sx < 0 else (COL["thigh"], COL["shin"])
            R(x0, y_hip - 1, x0 + lw_d, knee, c1, f"{p}_leg_u"); R(x0, knee - 1, x0 + lw_d, y_ank, c2, f"{p}_leg_l")
            R(x0, y_ank - 1, x0 + lw_d + toe, y_sole, COL["foot"], f"{p}_leg_l")
        acf = max(ac, tw / 2 - aw / 2 + 2.5)  # the far arm must stick out past the torso edge, or it has no visible pixels
        arm_c = lambda sx: acf if sx < 0 else ac
        ax = lambda sx: cx + sx * arm_c(sx) - aw / 2
        R(ax(-1), y_sh, ax(-1) + aw, elbow, COL["far"], "l_arm_u"); R(ax(-1), elbow - 1, ax(-1) + aw, arm_end - foot, COL["far"], "l_arm_l")
        R(ax(-1), arm_end - foot - 1, ax(-1) + aw, arm_end, COL["hand"], "l_arm_l")  # far arm: behind the torso
        poly = [(cx - tw / 2, y_sh), (cx + tw / 2 - 1, y_sh), (cx + tw * .4 - 1, y_hip), (cx - tw * .4, y_hip)]
        d.polygon(poly, fill=COL["torso"], outline=OUT); dl.polygon(poly, fill=BONE["torso"], outline=BONE["torso"])
        R(ax(1), y_sh, ax(1) + aw, elbow, COL["uarm"], "r_arm_u"); R(ax(1), elbow - 1, ax(1) + aw, arm_end - foot, COL["farm"], "r_arm_l")
        R(ax(1), arm_end - foot - 1, ax(1) + aw, arm_end, COL["hand"], "r_arm_l")  # near arm: in front of the torso
        R(cx - .5, y_neck - 1, cx + 2.5, y_sh + 1, COL["neck"], "head")
        hw = f("head_w")
        E(cx - hw / 2 + 1, y_top, cx + hw / 2 + 1, y_neck, hc, "head")
        if view == "diag":
            R(cx + hw / 2 + 1, y_top + f("head_h") * .5, cx + hw / 2 + 1 + max(1, round(.02 * Hu)), y_top + f("head_h") * .62, COL["head"], "head")  # nose
        J = {"head": [cx + .5, y_top + max(1.5, .3 * f("head_h"))], "neck": [cx + 1, y_neck], "pelvis": [cx, y_hip - 1]}
        for sx, p in ((-1, "l"), (1, "r")):
            J[f"{p}_shoulder"] = [cx + sx * (tw / 2 - 2.5), y_sh + 1]; J[f"{p}_elbow"] = [cx + sx * arm_c(sx), elbow]; J[f"{p}_wrist"] = [cx + sx * arm_c(sx), arm_end - foot]
            J[f"{p}_hip"] = [cx + sx * lc, y_hip]; J[f"{p}_knee"] = [cx + sx * lc, knee]; J[f"{p}_ankle"] = [cx + sx * lc, y_ank]
    la, ia = np.array(lab), np.asarray(img)[..., 3] > 0
    missing = ia & (la == 255)  # a stray edge pixel the label drawing did not hit: take the nearest labelled pixel's bone
    if missing.any():
        iy, ix = ndi.distance_transform_edt(la == 255, return_indices=True)[1]
        la[missing] = la[iy[missing], ix[missing]]
    ys, xs = np.nonzero(ia & (la != 255))
    overrides = [[int(x), int(y), int(la[y, x])] for y, x in zip(ys, xs)]
    return img, {k: [round(float(v[0]), 1), round(float(v[1]), 1)] for k, v in J.items()}, overrides


def _ref_rgba(ref, tol=40):
    """Reference illustration -> RGBA with the background removed (or the whole picture if removal would eat it)."""
    r = ref.convert("RGBA")
    rb = px.remove_bg(r, tol)
    if (np.asarray(rb)[..., 3] >= 128).mean() < .05:
        r.putalpha(255)
        return r
    return px.crop_to_content(rb)


def generate_from_template(template, ref, prompt, negative, ckpt, lora, lora_w, lora_dir, strength=.85, steps=25, cfg=7.0, seed=-1,
                           n=1, freedom=2, ip_scale=.8, colors=20, palette_src="reference", clean=True, inpaint_fn=None, bg_tol=40, palette=None):
    """The result has exactly the template's pixel size and silhouette (plus `freedom` px of room for hair, capes...), so a rig made
    for the template fits every sprite generated from it. Inside the silhouette SDXL repaints (inpaint, `strength`), guided by the
    reference image (IP-Adapter, `ip_scale`) and the prompt. The palette comes from the reference (or from the result)."""
    inpaint_fn = inpaint_fn or gen.inpaint
    T = template.convert("RGBA")
    w, h = T.size
    if max(w, h) > 256 or min(w, h) < 8:
        raise ValueError("the template must be between 8 and 256 px")
    ta = np.asarray(T)
    m = ta[..., 3] >= 128
    if not m.any():
        raise ValueError("the template is empty")
    fr = max(0, min(int(freedom), 8))
    mf = ndi.binary_dilation(m, iterations=fr) if fr else m  # silhouette + the allowed ring around it
    ref_rgba = _ref_rgba(ref, bg_tol) if ref is not None else None
    pal_ref = None
    if ref_rgba is not None:
        ra = np.asarray(ref_rgba)
        rp = ra[..., :3][ra[..., 3] >= 128]
        if len(rp):
            pal_ref = px.smart_palette(rp[np.random.RandomState(0).choice(len(rp), min(len(rp), 150000), replace=False)], max(2, int(colors)))
    forced = np.asarray(palette, np.uint8).reshape(-1, 3) if palette is not None and len(palette) else None  # e.g. the first view's palette, so all views share colours
    basis = forced if forced is not None else (pal_ref if pal_ref is not None else np.unique(ta[..., :3][m], axis=0))
    bgname = max(CANDIDATE_BG, key=lambda c: ((basis.astype(int) - np.array(CANDIDATE_BG[c])) ** 2).sum(1).min())  # far from the sprite's colours
    bg = np.array(CANDIDATE_BG[bgname])
    k = max(1, 1024 // max(w, h))
    ox, oy = (1024 - w * k) // 2, (1024 - h * k) // 2
    big = T.resize((w * k, h * k), Image.NEAREST)
    init = Image.new("RGB", (1024, 1024), tuple(int(v) for v in bg))
    init.paste(big.convert("RGB"), (ox, oy), big)
    up = lambda mk: np.kron(mk.astype(np.uint8), np.ones((k, k), np.uint8)).astype(bool)
    m_hi, mf_hi = up(m), up(mf)
    mask = Image.new("L", (1024, 1024), 0)
    mask.paste(Image.fromarray((mf_hi * 255).astype(np.uint8)), (ox, oy))
    ip_img = gen.prep_reference(ref_rgba, bgname) if ref_rgba is not None else None
    base = seed if seed is not None and seed >= 0 else int(np.random.randint(0, 2**31 - 1 - max(1, n)))
    out = []
    for i in range(max(1, int(n))):
        res = inpaint_fn(ckpt, lora, lora_w, lora_dir, prompt, negative, init, mask, strength, steps, cfg, base + i, bgname, "sprite",
                         ip_img, ip_scale)
        crop = np.asarray(res.convert("RGB"))[oy:oy + h * k, ox:ox + w * k]
        is_bg = np.abs(crop.astype(np.int16) - bg).max(-1) <= 70
        alpha_hi = m_hi | ((mf_hi & ~m_hi) & ~is_bg)  # inside the template: always sprite; in the ring: only what is not background
        hi = Image.fromarray(np.dstack([crop, (alpha_hi * 255).astype(np.uint8)]), "RGBA")
        pal = forced if forced is not None else (pal_ref if (palette_src == "reference" and pal_ref is not None) else px._choose_palette(hi, colors, "none"))
        sprite = px.crisp_reduce(hi, w, h, k, pal)
        if clean:
            sprite = px.despeckle(sprite)
        arr = np.asarray(sprite).copy()
        arr[~mf] = 0
        out.append({"sprite": Image.fromarray(arr, "RGBA"), "raw": res, "seed": base + i,
                    "info": {"seed": base + i, "size": [w, h], "bg": bgname, "colors": int(len(pal)), "scale": k}})
    return out
