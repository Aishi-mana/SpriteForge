"""AI joint cleanup (refine) and portrait expressions, with fake inpainting functions."""
from _common import *
from PIL import ImageDraw
from engine import rig, refine, portrait as P

sp, J, OV = synth_sprite()
raw, meta = rig.render(sp, J, OV, "walk", 8, "right", "r", "r", 1.0, 0, 1, 4)
ident = lambda ck, lo, lw, ld, pr, neg, img, mask, st, steps, cfg, seed, bg: img
out, info = refine.refine(raw, meta, sp, "c", "l", 1, "d", "p", inpaint_fn=ident, seed=1)
ok(all((np.asarray(a) == np.asarray(b)).all() for a, b in zip(raw, out)), "an identity 'AI' reproduces every frame exactly (mask, scale and alignment are right)")
def noisy(ck, lo, lw, ld, pr, neg, img, mask, st, steps, cfg, seed, bg):
    a = np.asarray(img).copy(); m = np.asarray(mask) > 0; a[m] = np.clip(a[m].astype(int) + np.random.randint(-25, 25, a[m].shape), 0, 255); return Image.fromarray(a.astype(np.uint8))
out, info = refine.refine(raw, meta, sp, "c", "l", 1, "d", "p", inpaint_fn=noisy, seed=1)
pal = {tuple(c) for c in np.unique(np.asarray(sp)[np.asarray(sp)[..., 3] > 0][:, :3], axis=0)}; bad = outside = 0
for i, (a, b) in enumerate(zip(raw, out)):
    A, B = np.asarray(a), np.asarray(b); m = refine.seam_mask(a, meta["joints"][i], info["radius"])
    bad += sum(1 for p in B[B[..., 3] > 0][:, :3] if tuple(p) not in pal); outside += int((A[~m] != B[~m]).any(-1).sum())
ok(bad == 0 and outside == 0, "noisy AI output is snapped back to the sprite's palette and nothing outside the seam masks changes")
def eraser(ck, lo, lw, ld, pr, neg, img, mask, st, steps, cfg, seed, bg):
    a = np.asarray(img).copy(); a[np.asarray(mask) > 0] = [255, 0, 255]; return Image.fromarray(a)
out, info = refine.refine(raw, meta, sp, "c", "l", 1, "d", "p", inpaint_fn=eraser, seed=1)
ok(info["reverted"] == 8 and sorted(info["reverted_idx"]) == list(range(8)) and all((np.asarray(a) == np.asarray(b)).all() for a, b in zip(raw, out)), "an AI that erases the figure is detected and every frame reverts to the rig version")
entry = {"raw": raw, "imgs": out, "meta": meta, "cfg": {"sprite": sp, "ckpt": "c", "lora": "l", "lora_w": 1, "lora_dir": "d", "character": "k", "negative": "", "steps": 22, "cfg": 7, "radius": 0}}
imgs, info2 = refine.redo_frames(entry, [2, 5], 99, .5, inpaint_fn=eraser)
ok(info2["reverted_idx"] == [2, 5] and len(imgs) == 8 and all((np.asarray(imgs[i]) == np.asarray(out[i])).all() for i in (0, 1, 3, 4, 6, 7)), "redo touches only the chosen frames and maps indices back to the whole animation")

N = 96; base = Image.new("RGBA", (N, N), (200, 200, 205, 255)); d = ImageDraw.Draw(base)
d.ellipse([22, 14, 74, 72], fill=(240, 200, 165, 255)); d.pieslice([20, 8, 76, 50], 180, 360, fill=(170, 40, 40, 255)); d.rectangle([32, 44, 40, 48], fill=(60, 110, 200, 255)); d.rectangle([56, 44, 64, 48], fill=(60, 110, 200, 255)); d.rectangle([42, 60, 54, 62], fill=(120, 40, 50, 255)); d.rectangle([30, 76, 66, 95], fill=(40, 70, 150, 255))
mask = {"cx": .5, "cy": .5, "rx": .26, "ry": .2}; B = np.asarray(base); mn = P.ellipse_mask(N, mask)
def blush(ck, lo, lw, ld, pr, neg, img, m, st, steps, cfg, seed, bg, kind):
    a = np.asarray(img).copy(); mm = np.asarray(m) > 0; yy, xx = np.mgrid[:a.shape[0], :a.shape[1]]
    for cx in (310, 700): a[mm & (((xx - cx) ** 2 + (yy - 640) ** 2) < 45 ** 2)] = [245, 120, 150]
    return Image.fromarray(a)
ev = lambda im, **k: [json.loads(e[5:]) for e in P.expression_events(im, mask, [("happy", "")], "c", "l", 1, "d", "red hair", "", .82, 25, 7, 5, k.get("extra", 4), inpaint_fn=blush)]
res = [e["result"] for e in ev(base) if "result" in e][0]; o = np.asarray(from_url(res["image"]))
ok((o[~mn] == B[~mn]).all() and (o[mn] != B[mn]).any(), "expression: not one pixel outside the face area changes")
ok(res["extra"] == [[245, 120, 150]], "new colours (blush) are kept as extras")
o0 = np.asarray(from_url([e["result"] for e in ev(base, extra=0) if "result" in e][0]["image"])); ok(len({tuple(c[:3]) for c in o0.reshape(-1, 4)} - {tuple(c[:3]) for c in B.reshape(-1, 4)}) == 0, "with extras off everything snaps to the base palette")
a = B.copy(); a[(a[..., :3] == [200, 200, 205]).all(-1), 3] = 0; tb = Image.fromarray(a, "RGBA"); ot = np.asarray(from_url([e["result"] for e in ev(tb) if "result" in e][0]["image"]))
ok(ot[0, 0, 3] == 0 and ot[40, 48, 3] == 255, "transparent portraits stay transparent outside the figure")
ok("square" in ev(Image.new("RGBA", (64, 48)))[0]["error"], "non-square portrait -> clear error")
ok("empty" in [json.loads(x[5:]) for x in P.expression_events(base, {"cx": 5, "cy": 5, "rx": .1, "ry": .1}, [("a", "")], "c", "l", 1, "d", "", "", .8, 25, 7, 5, 4, inpaint_fn=blush)][0]["error"], "empty face area -> clear error")
def boom(*a): raise RuntimeError("CUDA out of memory")
last = [json.loads(x[5:]) for x in P.expression_events(base, mask, [("a", "")], "c", "l", 1, "d", "", "", .8, 25, 7, 5, 4, inpaint_fn=boom)][-1]; ok("out of GPU memory" in last["error"], "out-of-memory gives a helpful hint")
done("test_portrait_refine")
