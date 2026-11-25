"""Mannequin templates (all views / styles / heights) and generation from a template with a fake model."""
import math
from _common import *
from PIL import ImageDraw
from scipy import ndimage as ndi
from engine import templates as T, rig, pixelize as px
from engine.refine import CANDIDATE_BG

bad, n, worst = [], 0, 99
for view in T.VIEWS:
    for style in ("normal", "chibi"):
        for h in range(32, 129):
            sp, j, ov = T.make_dummy(h, style, view); a = np.asarray(sp); lab = rig.assign_parts(sp, j, ov); counts = [int((lab == i).sum()) for i in range(10)]
            on = all(a[min(int(math.floor(y)), sp.height - 1), min(int(math.floor(x)), sp.width - 1), 3] > 0 for x, y in j.values())
            n += 1; worst = min(worst, min(counts))
            if not (sp.height == h and min(counts) >= 3 and on and len(ov) == int((a[..., 3] > 0).sum())): bad.append((view, style, h))
ok(not bad, f"all {n} mannequins (5 views x 2 styles x every height 32-128): exact height, joints on body, every bone has pixels (min {worst}), every pixel assigned" + (f" BAD {bad[:4]}" if bad else ""))
f, _, _ = T.make_dummy(64, "normal", "front"); b, _, _ = T.make_dummy(64, "normal", "back"); fa, ba = np.asarray(f), np.asarray(b)
ok(f.size == b.size and ((fa[..., 3] > 0) == (ba[..., 3] > 0)).all() and (fa != ba).any(), "back view: same silhouette as front, different head shading")

tpl, joints, ov = T.make_dummy(64, "normal", "front"); w, h = tpl.size; m = np.asarray(tpl)[..., 3] >= 128
ref = Image.new("RGB", (200, 300), (255, 255, 255)); d = ImageDraw.Draw(ref)
d.rectangle([60, 100, 140, 210], fill=(40, 80, 200)); d.ellipse([75, 30, 125, 95], fill=(240, 200, 160)); d.rectangle([40, 100, 60, 230], fill=(200, 30, 40)); d.rectangle([140, 100, 160, 230], fill=(200, 30, 40)); d.rectangle([70, 210, 130, 290], fill=(60, 60, 70))
refcols = {(40, 80, 200), (240, 200, 160), (200, 30, 40), (60, 60, 70)}
seen, cache = {}, {}
def fake(ck, lo, lw, ld, pr, neg, img, mask, st, steps, cfg, seed, bg, kind, ip, ips):
    seen.update(img=img, mask=mask, bg=bg, pr=pr, ip=ip, ips=ips, seed=seed)
    a = np.asarray(img).copy(); mk = np.asarray(mask) > 0; ys, xs = np.nonzero(mk); y0, y1, cx = ys.min(), ys.max(), (xs.min() + xs.max()) / 2
    yy, xx = np.mgrid[:1024, :1024]; band = (yy - y0) / (y1 - y0 + 1)
    a[mk] = np.where(band[..., None] < .25, np.array([240, 200, 160]), np.where(band[..., None] < .6, np.array([40, 80, 200]), np.array([60, 60, 70])))[mk]
    ring = mk & ~cache["m"]; a[ring & (xx > cx)] = [200, 30, 40]; a[ring & (xx <= cx)] = cache["bg"]   # cape on the right, plain background on the left
    return Image.fromarray(a)
def run(freedom, pal="reference", refimg=ref, n=1, seed=-1, palette=None):
    k = max(1, 1024 // max(w, h)); ox, oy = (1024 - w * k) // 2, (1024 - h * k) // 2
    mm = np.zeros((1024, 1024), bool); mm[oy:oy + h * k, ox:ox + w * k] = np.kron(m.astype(np.uint8), np.ones((k, k), np.uint8)).astype(bool); cache["m"] = mm
    probe = {}
    T.generate_from_template(tpl, refimg, "p", "", "c", "l", 1, "d", .85, 20, 7, 1, 1, freedom, .8, 12, pal, True, inpaint_fn=lambda *a: probe.update(bg=a[12]) or a[6], palette=palette)
    cache["bg"] = CANDIDATE_BG[probe["bg"]]
    return T.generate_from_template(tpl, refimg, "knight", "", "c", "l", 1, "d", .85, 20, 7, seed, n, freedom, .8, 12, pal, True, inpaint_fn=fake, palette=palette)
r = run(0)[0]; sp = np.asarray(r["sprite"]); k = r["info"]["scale"]
ok(r["sprite"].size == tpl.size and ((sp[..., 3] > 0) == m).all(), "freedom 0: exactly the template's size and silhouette")
im = np.asarray(seen["img"]); mk = np.asarray(seen["mask"]) > 0; bgc = np.array(CANDIDATE_BG[seen["bg"]])
ok((im[~mk] == bgc).all() and mk.sum() == m.sum() * k * k, "the model gets a plain background outside the mask; the mask is the silhouette scaled exactly")
ok(seen["ip"] is not None and seen["ips"] == .8 and "knight" in seen["pr"], "reference and prompt reach the model")
r = run(2)[0]; sp = np.asarray(r["sprite"]); a = sp[..., 3] > 0; mf = ndi.binary_dilation(m, iterations=2); extra = a & ~m
ok(a[m].all() and extra.any() and (extra <= mf).all() and (sp[..., 3][~mf] == 0).all(), "freedom 2: template pixels stay, extra pixels only inside the ring, nothing outside")
cxm = (np.nonzero(m)[1].min() + np.nonzero(m)[1].max()) / 2; ok((np.nonzero(extra)[1] >= cxm - 1).all(), "ring is opaque only where the model drew something (not where it left background)")
pix = {tuple(c[:3]) for c in sp.reshape(-1, 4) if c[3]}; near = lambda c: min(sum((x - y) ** 2 for x, y in zip(c, rc)) for rc in refcols) ** .5
ok(len(pix) <= 12 and all(near(c) < 40 for c in pix), "palette comes from the reference")
forced = np.array([[10, 10, 10], [250, 250, 250], [200, 30, 40], [40, 80, 200]], np.uint8); r = run(1, palette=forced)[0]; pf = {tuple(c[:3]) for c in np.asarray(r["sprite"]).reshape(-1, 4) if c[3]}
ok(pf <= {tuple(c) for c in forced}, "a forced palette (used to keep directions consistent) overrides everything")
r = run(2, refimg=None)[0]; ok(seen["ip"] is None and r["sprite"].size == tpl.size, "works without a reference")
ok([x["seed"] for x in run(1, n=3, seed=100)] == [100, 101, 102], "variations use consecutive seeds")
for label, t_, exp in (("empty", Image.new("RGBA", (32, 48), (0, 0, 0, 0)), "empty"), ("too large", Image.new("RGBA", (300, 300), (255, 0, 0, 255)), "between")):
    try: T.generate_from_template(t_, ref, "p", "", "c", "l", 1, "d", inpaint_fn=fake); ok(False, label)
    except ValueError as e: ok(exp in str(e), f"{label} template -> clear error")
r = run(0)[0]; fr, _ = rig.render(r["sprite"], joints, ov, "walk", 8, "right", "both", "r", 1, 0, 1, 4)
ok(all((np.asarray(f)[..., 3] > 0).sum() > .8 * int(m.sum()) for f in fr), "the template's rig animates the generated sprite")
done("test_templates")
