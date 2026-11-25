"""Tile follow-ups: corner / multi-terrain sets, animated tiles, collision shapes, AI seam repair (fake inpaint), endpoints, projects."""
from _common import *
install_fastapi_stubs()
import re
import xml.dom.minidom as X
from scipy import ndimage as ndi
from engine import terrain as TR, tiles as T, main as M, projects
HTTPException = http_exception()

def tex(n, c1, c2, seed):
    r = np.random.RandomState(seed); y, x = np.mgrid[0:n, 0:n]
    k = ((x * 3 + y * 5 + r.randint(0, 3, (n, n))) % 7 < 3)[..., None]
    return Image.fromarray(np.where(k, np.array(c1), np.array(c2)).astype(np.uint8)).convert("RGBA")
A16 = tex(16, (60, 150, 60), (40, 110, 50), 1); B16 = tex(16, (140, 100, 60), (110, 80, 50), 2); C16 = tex(16, (60, 90, 200), (40, 60, 160), 3); D16 = tex(16, (230, 230, 240), (200, 200, 220), 4)
cols = lambda im: {tuple(c) for c in np.asarray(im).reshape(-1, 4)}

# ================= corner sets =================
ok(TR.corner_index((0, 0, 0, 0), 2) == 0 and TR.corner_index((1, 0, 1, 1), 2) == 11 and TR.corner_index((2, 1, 0, 2), 3) == ((2 * 3 + 1) * 3 + 0) * 3 + 2 and
   [TR.corner_index(c, 3) for c in TR.corner_tuples(3)] == list(range(81)), "corner index = ((nw*N+ne)*N+se)*N+sw, tuples come in index order (same fixture as the JS test)")
for N, T_ in ((2, 16), (3, 16)):
    shapes = {TR.corner_tile_classes(c, N, T_)[0].tobytes() for c in TR.corner_tuples(N)}
    ok(len(shapes) == N ** 4, f"N={N}: all {N ** 4} corner combinations give different tiles")
c0, _ = TR.corner_tile_classes((0, 0, 0, 0), 2, 16); c1, _ = TR.corner_tile_classes((1, 1, 1, 1), 2, 16)
ok((c0 == 0).all() and (c1 == 1).all(), "all corners the same terrain -> a pure tile")
q, _ = TR.corner_tile_classes((0, 1, 1, 1), 2, 16); ok(q[0, 0] == 0 and q[-1, -1] == 1 and q[0, -1] == 1 and q[-1, 0] == 1 and 0.15 < (q == 0).mean() < 0.35, "one corner A: a rounded quarter around that corner")
h, _ = TR.corner_tile_classes((0, 1, 1, 0), 2, 16); ok((h[:, 0] == 0).all() and (h[:, -1] == 1).all(), "two A corners on one side: a straight half")

# exact joins: every tile is a crop of ONE global mask (random corner maps, 2 and 3 terrains, 16 and 24 px)
for N, T_ in ((2, 16), (3, 16), (3, 24)):
    ss = TR._css(T_); C = T_ * ss; sig = TR._sigma(T_, None); rng = np.random.RandomState(N * 100 + T_); n = 8
    for trial in range(2):
        raw = [ndi.gaussian_filter(rng.rand(n, n), 1.0) for _ in range(N)]; L = np.stack(raw).argmax(0)
        G = TR._classes(np.kron(L, np.ones((C, C), np.int32)), ss, sig, N); GR = TR._rim_mask(G)
        bad = 0
        for y in range(1, n - 2):
            for x in range(1, n - 2):
                tc, tr = TR.corner_tile_classes((L[y, x], L[y, x + 1], L[y + 1, x + 1], L[y + 1, x]), N, T_)
                sl = (slice(int((y + .5) * T_), int((y + 1.5) * T_)), slice(int((x + .5) * T_), int((x + 1.5) * T_)))
                bad += int((tc != G[sl]).sum() + (tr != GR[sl]).sum())
        ok(bad == 0, f"N={N} {T_}px random map {trial}: every corner tile equals the crop of the whole-map result (neighbours join exactly, rim included)")

r2 = TR.generate_corner([A16, B16]); ims = [t["image"] for t in r2["tiles"]]
allowed = cols(A16) | cols(B16) | {r2["rim_color"]}
ok(r2["kind"] == "corner16" and len(ims) == 16 and all(i.size == (16, 16) for i in ims) and set().union(*[cols(i) for i in ims]) <= allowed and all((np.asarray(i)[..., 3] == 255).all() for i in ims), "16 opaque tiles using only A's, B's and one rim colour")
ok(np.array_equal(np.asarray(ims[0]), np.asarray(A16)) and np.array_equal(np.asarray(ims[15]).reshape(-1, 4)[0], np.asarray(B16).reshape(-1, 4)[0]), "tile 0 is pure A (texture phase kept); the last tile is B")
rt = TR.generate_corner([A16, None]); ti = np.asarray(rt["tiles"][5]["image"]); ok(rt["transparent_b"] and (ti[..., 3] == 0).any() and (ti[..., 3] == 255).any() and len(rt["tiles"]) == 16, "without B the ground is transparent")
rn = TR.generate_corner([A16, B16], rim="none"); ok(rn["rim_color"] is None and set().union(*[cols(t["image"]) for t in rn["tiles"]]) <= cols(A16) | cols(B16), "rim none adds no colour")
r3 = TR.generate_corner([A16, B16, C16]); ok(r3["kind"] == "multi" and len(r3["tiles"]) == 81 and r3["n"] == 3 and set().union(*[cols(t["image"]) for t in r3["tiles"]]) <= cols(A16) | cols(B16) | cols(C16) | {r3["rim_color"]}, "multi-terrain: 81 tiles for 3 terrains, only their colours")
mid = r3["tiles"][TR.corner_index((0, 1, 2, 0), 3)]["image"]; ok(len({tuple(p) for p in np.asarray(mid).reshape(-1, 4)} & cols(C16)) > 0 and len({tuple(p) for p in np.asarray(mid).reshape(-1, 4)} & cols(B16)) > 0, "a tile with corners A,B,C,A really shows B and C")
r4 = TR.generate_corner([tex(8, (1, 2, 3), (4, 5, 6), 1), tex(8, (9, 9, 9), (8, 8, 8), 2), tex(8, (50, 60, 70), (80, 90, 100), 3), tex(8, (200, 10, 10), (190, 20, 20), 4)]); ok(len(r4["tiles"]) == 256 and r4["n"] == 4, "4 terrains: 256 tiles")
ok(TR.generate_corner([A16, B16], rnd=0)["sigma"] == 0 and TR.generate_corner([A16, B16], rnd=99)["sigma"] == 2.4, "rounding is honoured and clamped (<= 15 % of the tile so joins stay exact)")
def raises(fn, what):
    try: fn(); ok(False, what)
    except TR.TerrainError: ok(True, what + " -> TerrainError")
raises(lambda: TR.generate_corner([tex(15, (1, 1, 1), (2, 2, 2), 1), tex(15, (3, 3, 3), (4, 4, 4), 1)]), "odd tile size")
raises(lambda: TR.generate_corner([A16, tex(32, (1, 2, 3), (4, 5, 6), 1)]), "size mismatch")
raises(lambda: TR.generate_corner([A16, None, C16]), "multi set with a missing terrain")
raises(lambda: TR.generate_corner([A16]), "a single terrain")
raises(lambda: TR.generate_corner([A16, B16], rim="glow"), "unknown rim")

tmp = tmpdir()
e = TR.export_corner(r2, "Shore", dict(columns=8, godot=True, godot_path="res://art/t", tiled=True), tmp, ["Grass", "Sand"]); d = Path(e["dir"])
meta = json.loads((d / "terrain.json").read_text()); tres = (d / "Shore.tres").read_text(); sheet = Image.open(d / "Shore.png")
ok(e["count"] == 16 and sheet.size == (8 * 16, 2 * 16) and meta["terrains"] == ["Grass", "Sand"] and meta["tiles"][11]["corners"] == {"nw": 1, "ne": 0, "se": 1, "sw": 1}, "sheet + json with the corner terrains of every tile")
ok("terrain_set_0/mode = 1" in tres and 'terrain_0/name = "Grass"' in tres and "terrain_1/name" not in tres and tres.count("/0/terrain = 0") == 16, "Godot: match-corners terrain set with ONE terrain (A); all 16 tiles belong to it")
def gbits(i): return set(re.findall(rf"^{i % 8}:{i // 8}/0/terrains_peering_bit/(\w+) = 0$", tres, re.M))
ok(gbits(0) == {"top_left_corner", "top_right_corner", "bottom_right_corner", "bottom_left_corner"} and gbits(15) == set() and gbits(7) == {"top_left_corner"} and
   gbits(TR.corner_index((0, 1, 1, 0), 2)) == {"top_left_corner", "bottom_left_corner"}, "peering bits only on the corners that are terrain A")
tsx = (d / "Shore.tsx").read_text(); dom = X.parseString(tsx); wt = {w.getAttribute("tileid"): w.getAttribute("wangid") for w in dom.getElementsByTagName("wangtile")}
ok(len(wt) == 16 and 'type="corner"' in tsx and len(dom.getElementsByTagName("wangcolor")) == 2 and wt["0"] == "0,1,0,1,0,1,0,1" and wt["15"] == "0,2,0,2,0,2,0,2" and wt["11"] == "0,1,0,2,0,2,0,2", "Tiled: valid corner wang set with 2 colours; wangid = top, topright, right, bottomright, ...")
e3 = TR.export_corner(r3, "Land", dict(columns=9), tmp, ["Grass", "Dirt", "Water"]); t3 = (Path(e3["dir"]) / "Land.tres").read_text()
ok(e3["count"] == 81 and all(f"terrain_{k}/name" in t3 for k in range(3)) and t3.count("/0/terrain_set = 0") == 81 and "/0/terrain = 2\n" in t3, "multi: three terrains declared, 81 tiles in the set")
iA = TR.corner_index((0, 0, 1, 2), 3); ok(re.search(rf"^{iA % 9}:{iA // 9}/0/terrain = 0$", t3, re.M) and re.search(rf"^{iA % 9}:{iA // 9}/0/terrains_peering_bit/bottom_left_corner = 2$", t3, re.M), "multi: the tile's terrain is its most common corner terrain, bits carry each corner's terrain")
ok(len(X.parseString((Path(e3["dir"]) / "Land.tsx").read_text()).getElementsByTagName("wangtile")) == 81, "multi: 81 wang tiles in Tiled")
ok(Path(TR.export_corner(r2, "../../x", {}, tmp)["dir"]).resolve().parent == (tmp / "exports").resolve(), "hostile name stays in exports/")

# ================= animated tiles =================
base = tex(16, (60, 150, 60), (40, 110, 50), 7)
fr = T.animate_tile(base, "scroll", 8, "right"); ok(len(fr) == 8 and all(f.size == (16, 16) for f in fr) and np.array_equal(np.asarray(fr[0]), np.asarray(base)), "scroll: 8 frames, frame 0 is the tile")
ok(all(np.array_equal(np.asarray(fr[i]), np.roll(np.asarray(base), 2 * i, axis=1)) for i in range(8)), "scroll right moves 1/frames of the width per frame (loops exactly)")
ok(np.array_equal(np.roll(np.asarray(fr[7]), 2, axis=1), np.asarray(fr[0])), "the last frame leads back into the first (seamless loop)")
for dr in ("left", "down", "up", "diag"): ok(T.animate_tile(base, "scroll", 4, dr)[1].tobytes() != base.tobytes(), f"scroll {dr}")
rp = T.animate_tile(base, "ripple", 8); a0 = np.asarray(base)
ok(all(any(np.array_equal(np.asarray(f)[y], np.roll(a0[y], s, axis=0)) for s in range(-8, 9)) for f in rp for y in range(16)) and cols(rp[3]) <= cols(base), "ripple: every row is the original row shifted sideways, no new colours")
ok(len({f.tobytes() for f in rp}) == 8, "ripple frames are all different")
sh = T.animate_tile(base, "shimmer", 8, density=0.3, seed=3); ok(all(cols(f) <= cols(base) for f in sh) and len({f.tobytes() for f in sh}) > 3, "shimmer: only the tile's own colours, frames differ")
ch = np.mean([(np.asarray(f) != a0).any(axis=2).mean() for f in sh]); ok(ch < 0.3 and T.animate_tile(base, "shimmer", 8, density=0.3, seed=3)[2].tobytes() == sh[2].tobytes(), "shimmer changes a limited share of pixels and is deterministic for a seed")
def raises2(fn, what):
    try: fn(); ok(False, what)
    except T.TileError: ok(True, what + " -> TileError")
raises2(lambda: T.animate_tile(base, "spin"), "unknown mode"); raises2(lambda: T.animate_tile(base, "scroll", 4, "sideways"), "unknown direction")
ok(len(T.animate_tile(base, "scroll", 1)) == 2 and len(T.animate_tile(base, "scroll", 99)) == 32, "frame count is clamped to 2..32")
ex = T.export_animated(fr, "Water!", dict(ms=100, godot=True, godot_path="res://t", tiled=True), tmp); dd = Path(ex["dir"]); st = Image.open(dd / "Water.png")
ok(st.size == (16 * 8, 16) and (dd / "Water_preview.gif").exists() and json.loads((dd / "animation.json").read_text())["duration_ms"] == 100 and ex["frames"] == 8, "strip sheet, preview gif, json")
ok(all(st.crop((i * 16, 0, i * 16 + 16, 16)).tobytes() == fr[i].tobytes() for i in range(8)), "frames sit side by side in order")
tr_ = (dd / "Water.tres").read_text(); ok(tr_.count("/animation_frame_") == 8 and "0:0/animation_frame_7/duration = 0.1" in tr_ and tr_.index("animation_frame_0") < tr_.index("0:0/0 = 0") and 'path="res://t/Water.png"' in tr_, "Godot: animated tile 0:0 with 8 frame durations (seconds)")
tx = (dd / "Water.tsx").read_text(); X.parseString(tx); ok(tx.count("<frame ") == 8 and 'duration="100"' in tx and 'columns="8"' in tx and 'tilecount="8"' in tx, "Tiled: tile 0 has an animation over tiles 0-7")
raises2(lambda: T.export_animated(fr[:1], "x", {}, tmp), "a single frame is not an animation")

# ================= collision shapes in the tileset export =================
til = [Image.new("RGBA", (16, 16), (i * 40, 9, 9, 255)) for i in range(4)]
ec = T.export_tileset(til, ["a", "b", "c", "d"], dict(columns=2, solid=[True, False, True], godot=True, tiled=True), "walls", tmp); dc = Path(ec["dir"])
tc = (dc / "walls.tres").read_text(); poly = "PackedVector2Array(-8, -8, 8, -8, 8, 8, -8, 8)"
ok(tc.count("physics_layer_0/polygon_0/points") == 2 and f"0:0/0/physics_layer_0/polygon_0/points = {poly}" in tc and f"0:1/0/physics_layer_0/polygon_0/points = {poly}" in tc and "1:0/0/physics_layer_0" not in tc and "physics_layer_0/collision_layer = 1" in tc, "Godot: full-tile collision polygon on the solid tiles only + one physics layer")
sx = X.parseString((dc / "walls.tsx").read_text()); tiles_ = sx.getElementsByTagName("tile"); ok([len(t.getElementsByTagName("objectgroup")) for t in tiles_] == [1, 0, 1, 0] and tiles_[0].getElementsByTagName("object")[0].getAttribute("width") == "16", "Tiled: collision rectangle on the solid tiles only")
ok([t["solid"] for t in json.loads((dc / "tileset.json").read_text())["tiles"]] == [True, False, True, False], "tileset.json records solid")
ok("physics" not in (Path(T.export_tileset(til, [], dict(godot=True), "plain", tmp)["dir"]) / "plain.tres").read_text(), "no physics layer when nothing is solid")
odd = T.export_tileset([Image.new("RGBA", (15, 15), (1, 2, 3, 255))], [], dict(solid=[True]), "odd", tmp); ok("PackedVector2Array(-7.5, -7.5, 7.5, -7.5, 7.5, 7.5, -7.5, 7.5)" in (Path(odd["dir"]) / "odd.tres").read_text(), "odd tile sizes give half-pixel polygon corners")

# ================= AI seam repair (fake inpaint) =================
def texture(n=256, seed=1):
    r = np.random.RandomState(seed); y, x = np.mgrid[0:n, 0:n] / n
    base_ = 110 + 60 * np.sin(6.0 * x + 2 * y) + 40 * np.cos(9.0 * y - 3 * x) + 90 * x
    g = np.stack([base_, base_ * 0.8, base_ * 0.6], -1) + r.normal(0, 6, (n, n, 3)); return Image.fromarray(np.clip(g, 0, 255).astype(np.uint8), "RGB")
raw_tile, _ = T.tile_post(texture(512), 32, 12, "none", seamless=False)        # a tile with a hard seam
calls = []
def good_inpaint(ckpt, lora, lw, ld, prompt, neg, image, mask, strength, steps, cfg, seed, bg, kind, *a, **k):
    calls.append(dict(image=image, mask=mask, kind=kind, prompt=prompt, strength=strength))
    from PIL import ImageFilter
    return image.filter(ImageFilter.GaussianBlur(45))        # a "smoothing" AI: it hides the old seam by painting soft content over it
fixed, info = T.repair_seams(raw_tile, good_inpaint, "mossy stones", "", "ck", "", 1.0, "ld", 0.55, 20, 7, 3)
c = calls[-1]; mk = np.asarray(c["mask"]) > 0
ok(c["image"].size == (1024, 1024) and c["mask"].size == (1024, 1024) and c["kind"] == "tile" and c["prompt"] == "mossy stones" and 0.15 < mk.mean() < 0.45, "the AI gets the half-shifted 1024 image, a cross-shaped mask (not the whole tile) and the tile template")
ok(mk[512, 5] and mk[5, 512] and not mk[5, 5] and not mk[1000, 1000], "the mask is a cross through the middle (where the old seam now is)")
ok(info["seam"] < info["seam_before"] / 2 and fixed.size == (32, 32) and cols(fixed) <= cols(raw_tile), f"seam {info['seam_before']} -> {info['seam']}, same palette")
n = 32; shift = T.wrap_offset(raw_tile); band = np.zeros((n, n), bool); yy, xx = np.mgrid[0:n, 0:n]; bw = info["band"]
band = (np.abs(xx - n // 2) < bw / 2 + .5) | (np.abs(yy - n // 2) < bw / 2 + .5)
fs = np.asarray(T.wrap_offset(fixed)); ok((fs[~band] == np.asarray(shift)[~band]).all(), "everything outside the cross is kept pixel for pixel")
def evil(*a, **k): return Image.new("RGB", (1024, 1024), (250, 0, 250))      # a terrible AI: flat magenta
bad, binfo = T.repair_seams(raw_tile, evil, "x", "", "ck", "", 1.0, "ld"); fb = np.asarray(bad)
ok(cols(bad) <= cols(raw_tile) and fb.shape == (32, 32, 4), "even a useless AI answer is snapped to the tile's palette")
a = np.asarray(bad).astype(int); a2 = np.asarray(T.wrap_offset(bad)).astype(int); step = np.abs(np.diff(a2[..., :3], axis=1)).mean()
ok(np.abs(a2[:, 0, :3] - a2[:, -1, :3]).mean() < 1.3 * step + 1, "whatever the AI draws, the borders of the shifted tile are untouched, so the wrap-around join stays continuous")
odd_t, _ = T.tile_post(texture(512, 4), 24, 10, "none", seamless=False); oddf, oi = T.repair_seams(odd_t, good_inpaint, "x", "", "ck", "", 1.0, "ld"); ok(oddf.size == (24, 24) and oi["seam"] < oi["seam_before"], "24 px tile (1024 is not a multiple)")
for bad_tile in (Image.new("RGBA", (16, 24), (1, 1, 1, 255)), Image.new("RGBA", (4, 4), (1, 1, 1, 255))):
    raises2(lambda: T.repair_seams(bad_tile, good_inpaint, "x", "", "ck", "", 1.0, "ld"), f"tile {bad_tile.size}")

# ================= endpoints =================
tmp2 = tmpdir(); M.ROOT = tmp2; M.CFG_PATH = tmp2 / "config.json"; md = tmp2 / "m"; (md / "checkpoints").mkdir(parents=True); (md / "loras").mkdir(); (md / "checkpoints" / "sd_xl_base_1.0.safetensors").write_bytes(b"x")
M.CFG_PATH.write_text(json.dumps({"models_dir": str(md)})); CK = "sd_xl_base_1.0.safetensors"
r = M.terrain_generate(M.TerrainBody(a=data_url(A16), b=data_url(B16), kind="corner16")); ok(len(r["tiles"]) == 16 and r["tiles"][11]["corners"] == [1, 0, 1, 1] and r["lookup"] == [] and r["n"] == 2 and from_url(r["tiles"][0]["image"]).size == (16, 16), "corner16 endpoint")
r = M.terrain_generate(M.TerrainBody(a=data_url(A16), b=data_url(B16), c=data_url(C16), d=data_url(D16) if False else None, kind="multi")); ok(len(r["tiles"]) == 81 and r["n"] == 3, "multi endpoint with 3 terrains")
for bad, what in ((M.TerrainBody(a=data_url(A16), b=data_url(B16), kind="multi"), "multi without C"), (M.TerrainBody(a=data_url(A16), kind="corner16", c="junk", b="junk"), "broken B")):
    try: M.terrain_generate(bad); ok(False, what)
    except HTTPException as ex_: ok(ex_.status_code == 400, what + " -> 400")
r = M.terrain_export(M.TerrainBody(a=data_url(A16), b=data_url(B16), c=data_url(C16), kind="multi", name="world", names=["Grass", "Dirt", "Water"], columns=9)); ok(r["count"] == 81 and "Water" in (Path(r["dir"]) / "world.tres").read_text(), "multi export endpoint uses the terrain names")
r = M.terrain_export(M.TerrainBody(a=data_url(A16), b=data_url(B16), kind="blob47", name="blob")); ok(r["count"] == 47, "blob export still works")
M.gen.inpaint = good_inpaint; M.gen.SAMPLER = None
r = M.tiles_repair(M.RepairBody(tile=data_url(raw_tile), prompt="mossy stones", checkpoint=CK, seed=5, strength=0.5)); ok(from_url(r["sprite"]).size == (32, 32) and r["info"]["seam"] < r["info"]["seam_before"] and r["info"]["seed"] == 5, "repair endpoint")
try: M.tiles_repair(M.RepairBody(tile="junk", checkpoint=CK)); ok(False, "junk")
except HTTPException as ex_: ok(ex_.status_code == 400, "broken tile -> 400")
try: M.tiles_repair(M.RepairBody(tile=data_url(raw_tile), checkpoint="nope.safetensors")); ok(False, "ckpt")
except HTTPException as ex_: ok(ex_.status_code == 400 and "checkpoint not found" in ex_.detail, "missing checkpoint -> readable 400")
def oom(*a, **k): raise RuntimeError("CUDA out of memory")
M.gen.inpaint = oom
try: M.tiles_repair(M.RepairBody(tile=data_url(raw_tile), checkpoint=CK)); ok(False, "oom")
except HTTPException as ex_: ok(ex_.status_code == 500 and "out of GPU memory" in ex_.detail, "out of memory -> readable error with advice")
body = M.AnimBody(tile=data_url(base), mode="ripple", frames=6, ms=90); r = M.tiles_animate(body); ok(len(r["frames"]) == 6 and r["ms"] == 90 and from_url(r["frames"][0]).size == (16, 16), "animate endpoint")
r = M.tiles_export_anim(M.AnimBody(tile=data_url(base), mode="shimmer", frames=4, name="lava", ms=150)); ok(r["frames"] == 4 and (Path(r["dir"]) / "lava.tres").exists(), "animation export endpoint")
for bad in (M.AnimBody(tile="junk"), M.AnimBody(tile=data_url(base), mode="spin")):
    try: M.tiles_animate(bad); ok(False, "bad anim")
    except HTTPException as ex_: ok(ex_.status_code == 400, "bad animation request -> 400")
r = M.tiles_export(M.TileSetBody(name="solidset", tiles=[{"name": "wall", "image": data_url(til[0]), "solid": True}, {"name": "floor", "image": data_url(til[1])}], columns=2))
ok("physics_layer_0/polygon_0/points" in (Path(r["dir"]) / "solidset.tres").read_text(), "tileset export endpoint passes the solid flags")

# ================= projects =================
projects.save(tmp2, "P22", {"tileset": {"tiles": [{"name": "wall", "image": data_url(til[0]), "solid": True}, {"name": "floor", "image": data_url(til[1]), "solid": False}]},
                            "images": {"terrc": data_url(C16), "terrd": data_url(D16)}}); doc = projects.load(tmp2, "P22")
ok([t["solid"] for t in doc["tileset"]["tiles"]] == [True, False] and doc["images"]["terrc"] and from_url(doc["images"]["terrd"]).tobytes() == D16.tobytes(), "solid flags and terrains C / D are saved with the project")
done("test_tilefx")
