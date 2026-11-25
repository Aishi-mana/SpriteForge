"""Pixel conversion: crisp vs legacy accuracy, grid detection, palettes, outline, edge cases."""
from _common import *
from PIL import ImageDraw, ImageFilter
from engine import pixelize as px

# ground truth: 64x64 art with outlines and a dither patch, upscaled 8x, blurred and noised like AI output
rng = np.random.RandomState(3)
G = Image.new("RGBA", (64, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(G)
cols = [(30, 20, 40), (200, 60, 50), (230, 130, 90), (245, 205, 160), (60, 100, 190), (40, 70, 140), (120, 125, 135), (200, 205, 215), (90, 50, 30), (250, 235, 120)]
d.ellipse([20, 4, 44, 28], fill=cols[3], outline=cols[0]); d.pieslice([19, 2, 45, 24], 180, 360, fill=cols[1], outline=cols[0])
d.rectangle([22, 14, 26, 16], fill=cols[4]); d.rectangle([38, 14, 42, 16], fill=cols[4]); d.rectangle([30, 22, 34, 22], fill=cols[8])
d.rectangle([16, 30, 48, 52], fill=cols[5], outline=cols[0]); d.rectangle([18, 32, 46, 40], fill=cols[4])
d.rectangle([10, 32, 16, 50], fill=cols[2], outline=cols[0]); d.rectangle([48, 32, 54, 50], fill=cols[2], outline=cols[0])
d.rectangle([20, 53, 30, 62], fill=cols[8], outline=cols[0]); d.rectangle([34, 53, 44, 62], fill=cols[8], outline=cols[0])
d.rectangle([3, 20, 5, 50], fill=cols[7], outline=cols[0]); d.rectangle([30, 34, 34, 38], fill=cols[9])
A = np.array(G)
for y in range(42, 50):
    for x in range(20, 44):
        if (x + y) % 2 == 0 and A[y, x, 3]: A[y, x, :3] = cols[6]
G = Image.fromarray(A, "RGBA"); gt = np.asarray(G)
big = Image.new("RGBA", (1024, 1024), (255, 255, 255, 255)); big.alpha_composite(G.resize((512, 512), Image.NEAREST), (256, 256))
ai = big.convert("RGB").filter(ImageFilter.GaussianBlur(1.1))
ai = Image.fromarray(np.clip(np.asarray(ai).astype(int) + rng.randint(-7, 8, (1024, 1024, 3)), 0, 255).astype(np.uint8))
bb = G.getchannel("A").getbbox(); gtc = gt[bb[1]:bb[3], bb[0]:bb[2]]; op = gtc[..., 3] > 0

def acc(sp):
    a = np.asarray(sp).astype(int)
    if a.shape[:2] != gtc.shape[:2]: return -1
    return ((np.abs(a[..., :3] - gtc[..., :3].astype(int)).max(-1) <= 30) & (a[..., 3] > 0)).sum() / op.sum() * 100

for n in (8, 16):
    new, info = px.pixelize(ai, "auto", colors=n, crisp=True); old, _ = px.pixelize(ai, "auto", colors=n, crisp=False)
    ok(info.get("grid") == 8 and acc(new) >= 97, f"crisp auto, {n} colours: grid 8, {acc(new):.1f}% of pixels correct (legacy {acc(old):.1f}%)")
    ok(acc(new) > acc(old) + 8, f"crisp beats legacy by a clear margin at {n} colours")
sp, _ = px.pixelize(ai, "fixed", 40, 12); ok(sp.height == 40, f"fixed size 40 -> {sp.size}")
pc, _ = px.pixelize(ai, "canvas", 128, 12, do_remove_bg=False); ok(pc.size == (128, 128), "canvas mode keeps the canvas size")

# grid detection
src = synth_sprite()[0]
ok([(px.detect_grid(px.crop_to_content(src.resize((src.width * S, src.height * S), Image.NEAREST))) or [None])[0] for S in (4, 6, 8, 10)] == [4, 6, 8, 10],
   "clean upscales x4 x6 x8 x10 are detected at their true grid (no half-size sub-harmonic)")
sm = Image.fromarray(np.dstack([np.tile(np.linspace(0, 255, 300), (300, 1))] * 3).astype(np.uint8))
ok(px.detect_grid(sm) is None, "a smooth gradient has no grid")

# palettes / outline / edge cases
ref, _ = px.pixelize(ai, "fixed", 48, 8); pal = px.palette_from_sprite(ref)
for mode, sz in (("fixed", 48), ("canvas", 128)):
    s, _ = px.pixelize(ai, mode, sz, 16, pal); cc = {tuple(c[:3]) for c in np.asarray(s).reshape(-1, 4) if c[3]}
    ok(cc <= {tuple(c) for c in pal}, f"{mode}: palette lock uses only the given colours")
s, _ = px.pixelize(ai, "fixed", 40, 12, "pico8"); ok({tuple(c[:3]) for c in np.asarray(s).reshape(-1, 4) if c[3]} <= {tuple(c) for c in px.PALETTES["pico8"]}, "named preset palette is respected")
a1, _ = px.pixelize(ai, "fixed", 40, 12, outline="selective"); b0, _ = px.pixelize(ai, "fixed", 40, 12, outline="none")
ok((a1.width - b0.width, a1.height - b0.height) == (2, 2), "outline adds a 1 px ring (+2 px per axis) in fixed mode")
c, _ = px.pixelize(ai, "canvas", 128, 12, do_remove_bg=False, outline="dark"); ok(c.size == (128, 128), "canvas mode never changes size, even with an outline")
for name, im in (("blank", Image.new("RGBA", (300, 300), (255, 255, 255, 255))), ("tiny", Image.new("RGBA", (5, 7), (10, 20, 30, 255))), ("transparent", Image.new("RGBA", (200, 200), (0, 0, 0, 0)))):
    good = True
    for mode in ("fixed", "auto", "canvas"):
        try: px.pixelize(im, mode, 32, 8, outline="selective")
        except Exception as e: good = False; print("   ", name, mode, type(e).__name__, e)
    ok(good, f"degenerate input '{name}' works in every mode")
s, _ = px.pixelize(ai, "fixed", 48, 12, crisp=False); ok(s.height == 48, "legacy converter still available (crisp=False)")
done("test_pixelize")
