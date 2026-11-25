"""Palette tools: parsing, export round-trip, user library, remap/dither, merge, hue variants, ramps."""
from _common import *
from engine import palettes as P, pixelize as px

r = P.parse_any("s.hex", b"1a1c2c\n#5d275d\nB13E53\n\n5d275d\n"); ok(r["colors"] == ["#1a1c2c", "#5d275d", "#b13e53"] and r["name"] == "s", "hex: comments / # / case / duplicates")
ok(P.parse_any("t.gpl", b"GIMP Palette\nName: T\n#\n 26  28  44\tdark\n255 255 255\twhite\n")["colors"] == ["#1a1c2c", "#ffffff"], "gpl")
ok(P.parse_any("j.pal", b"JASC-PAL\n0100\n2\n255 0 0\n0 255 0\n")["colors"] == ["#ff0000", "#00ff00"], "jasc pal")
im = Image.new("RGB", (4, 1)); im.putdata([(255, 0, 0), (0, 255, 0), (0, 255, 0), (0, 0, 255)])
ok(P.parse_any("s.png", png_bytes(im))["colors"] == ["#ff0000", "#00ff00", "#0000ff"], "swatch png: order of appearance, duplicates removed")
for label, data, name in (("photo", png_bytes(Image.fromarray(np.random.RandomState(0).randint(0, 255, (40, 40, 3), dtype=np.uint8), "RGB")), "p.png"), ("garbage", b"hello", "x.hex")):
    try: P.parse_any(name, data); ok(False, label)
    except P.PaletteError: ok(True, f"{label} rejected with PaletteError")

root = tmpdir(); cols = ["#1a1c2c", "#5d275d", "#b13e53", "#ef7d57"]; e = P.export_files(root, "My Pal!", cols); d = Path(e["dir"])
ok(all(P.parse_any("x" + Path(f).suffix, (d / f).read_bytes())["colors"] == cols for f in ("My_Pal.hex", "My_Pal.gpl", "My_Pal.pal", "My_Pal-1px.png")), "hex / gpl / pal / png exports re-import identically")
n = P.save_user(root, "Hero Team", ["#ff0000", "#00ff00", "#0000ff"]); ok("Hero Team" in px.PALETTES, "saved palette becomes usable by name in the converters")
try: P.save_user(root, "pico8", ["#fff"]); ok(False, "builtin")
except P.PaletteError: ok(True, "built-in names cannot be overwritten")
P.delete_user(root, "Hero Team"); ok("Hero Team" not in px.PALETTES and all(k in px.PALETTES for k in px.BUILTIN_PALETTES), "delete removes it; built-ins survive")

grad = np.zeros((64, 128, 4), np.uint8); grad[..., 3] = 255
for x in range(128): grad[:, x, :3] = int(x * 255 / 127)
grad[:8, :, 3] = 0; Gm = Image.fromarray(grad, "RGBA"); bw = [[0, 0, 0], [255, 255, 255]]
for mode in ("none", "bayer2", "bayer4", "floyd"):
    o, _ = P.remap(Gm, bw, mode, 1.0); a = np.asarray(o)
    ok({tuple(c[:3]) for c in a.reshape(-1, 4) if c[3]} <= {(0, 0, 0), (255, 255, 255)} and (a[:8, :, 3] == 0).all(), f"remap {mode}: only palette colours, transparency kept")
o, _ = P.remap(Gm, bw, "floyd", 1.0); w = (np.asarray(o)[..., 0] == 255)[8:]  # visible rows only (the top 8 are transparent)
for lo, hi in ((0, 64), (64, 128)):
    ok(abs(float(P.lch(grad[20, lo:hi, :3])[0].mean()) - float(w[:, lo:hi].mean())) < .04, f"floyd keeps PERCEIVED brightness (columns {lo}-{hi})")
o, note = P.remap(Image.new("RGBA", (600, 600), (128, 128, 128, 255)), bw, "floyd"); ok("ordered" in note, "very large image falls back from floyd")
rng = np.random.RandomState(1); base = np.zeros((32, 32, 4), np.uint8); base[..., 3] = 255; base[:, :16, :3] = (200, 60, 50); base[:, 16:, :3] = (40, 80, 200)
nz = base.copy(); nz[..., :3] = np.clip(nz[..., :3].astype(int) + rng.randint(-4, 5, (32, 32, 3)), 0, 255).astype(np.uint8)
o, pal = P.merge_similar(Image.fromarray(nz, "RGBA"), .05); ok(len(pal) == 2, "merge collapses noisy colours to the 2 real ones")
sp = synth_sprite()[0]; a0 = np.asarray(sp); opm = a0[..., 3] > 0; L0 = P.lch(a0[opm][:, :3])[0]
worst = 0
for v in P.variants(sp, [45, 90, 135, 180, 225, 270, 315], protect=[[240, 200, 160]], keep_dark=True):
    a = np.asarray(v["image"]); worst = max(worst, float(np.abs(P.lch(a[opm][:, :3])[0] - L0).max()))
    skin = (a0[..., :3] == [240, 200, 160]).all(-1); assert (a[skin][:, :3] == [240, 200, 160]).all()
ok(worst < .02, f"hue variants keep lightness (worst dL {worst:.4f}) and never touch protected colours")
sat = Image.new("RGBA", (3, 1), (0, 0, 0, 255)); sat.putdata([(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)])
v = P.variants(sat, [180], keep_dark=False)[0]; ok(np.abs(P.lch(np.asarray(v["image"])[..., :3].reshape(-1, 3))[0] - P.lch(np.asarray(sat)[..., :3].reshape(-1, 3))[0]).max() < .02, "even pure primaries keep lightness (gamut-aware)")
for c in ([200, 60, 50], [60, 110, 200], [250, 200, 40], [128, 128, 128]):
    r5 = P.ramp(c, 5); Ls = [float(P.lch(np.array([P.from_hex(h)], np.uint8))[0][0]) for h in r5]
    ok(len(r5) == 5 and all(Ls[i] < Ls[i + 1] for i in range(4)) and r5[2] == P.to_hex(c), f"ramp {P.to_hex(c)}: 5 steps dark->light, centre is the base colour")
ok(P.sort_colors(["#ffffff", "#000000", "#808080"], "lightness") == ["#000000", "#808080", "#ffffff"], "sort by lightness")
ex = P.extract(sp); ok(ex["total"] == 7 and ex["colors"][0]["count"] >= ex["colors"][-1]["count"], "extract: counts sorted")
done("test_palettes")
