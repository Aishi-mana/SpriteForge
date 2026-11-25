"""Autotile / terrain sets: neighbour logic, exact tile joins against a whole-map mask, colours, export (Godot terrain, Tiled wang set), endpoints, projects."""
from _common import *
install_fastapi_stubs()
import re
import xml.dom.minidom as X
from engine import terrain as TR, tiles as T, main as M, projects
HTTPException = http_exception()

def tex(n, c1, c2, seed):
    r = np.random.RandomState(seed); y, x = np.mgrid[0:n, 0:n]
    k = ((x * 3 + y * 5 + r.randint(0, 3, (n, n))) % 7 < 3)[..., None]
    return Image.fromarray(np.where(k, np.array(c1), np.array(c2)).astype(np.uint8)).convert("RGBA")
GRASS = tex(16, (60, 150, 60), (40, 110, 50), 1); DIRT = tex(16, (140, 100, 60), (110, 80, 50), 2)

# ---------------- neighbour logic ----------------
ok(len(TR.canonical_masks("blob47")) == 47 and len(TR.canonical_masks("edge16")) == 16, "47 blob tiles and 16 edge tiles")
plus = [[0, 1, 0], [1, 1, 1], [0, 1, 0]]
ok(TR.neighbor_mask(plus, 1, 1) == 85 and TR.neighbor_mask(plus, 1, 0) == 16 | 32 | 8 and TR.neighbor_mask(plus, 0, 1) == 4 | 2 | 8 and TR.neighbor_mask([[1, 1], [1, 1]], 0, 0) == 4 | 8 | 16,
   "neighbour bits are clockwise from north (N=1 NE=2 E=4 SE=8 S=16 SW=32 W=64 NW=128); outside the grid is empty")
ok(TR.canon_blob(255) == 255 and TR.canon_blob(2) == 0 and TR.canon_blob(1 | 2) == 1 and TR.canon_blob(1 | 2 | 4) == 7 and TR.canon_edge(255) == 85, "a corner bit only counts when both touching edges are set")
for kind in TR.KINDS:
    lk = TR.lookup_table(kind); ms = TR.canonical_masks(kind)
    ok(len(lk) == 256 and all(ms[lk[m]] == TR.canon_for(kind)(m) for m in range(256)), f"{kind}: lookup maps every raw mask to the tile with its canonical mask")

# ---------------- geometry ----------------
shapes = {}
for m in range(256): shapes.setdefault(TR.tile_masks(m, "blob47", 16)[0].tobytes(), set()).add(TR.canon_blob(m))
ok(len(shapes) == 47 and all(len(v) == 1 for v in shapes.values()), "the geometry itself gives exactly 47 different shapes for the 256 raw neighbour patterns (the reduction is real)")
shapes = {}
for m in range(256): shapes.setdefault(TR.tile_masks(m, "edge16", 16)[0].tobytes(), set()).add(TR.canon_edge(m))
ok(len(shapes) == 16, "edge16: 16 different shapes")
full, _ = TR.tile_masks(255, "blob47", 16); iso, _ = TR.tile_masks(0, "blob47", 16)
ok(full.all() and not iso[0, 0] and iso[8, 8] and not iso[0].any() and not iso[:, 0].any() and not iso[-1].any(), "full tile is all A; the isolated blob keeps clear of every tile edge")
top, _ = TR.tile_masks(255 & ~1, "blob47", 16)  # N missing
ok(not top[0].any() and top[-1].all() and top[8, 8], "an exposed side recedes from that edge only")
inner, _ = TR.tile_masks(255 & ~2, "blob47", 16)
ok(not inner[0, -1] and inner[0, 0] and inner[-1, -1] and inner.sum() > 16 * 16 - 20, "a missing diagonal makes a small notch in that corner only")
cx = TR.tile_masks(0, "blob47", 16)[0]; ok(np.array_equal(cx, cx[:, ::-1]) and np.array_equal(cx, cx[::-1]), "the isolated blob is symmetric")

# exact joins: every tile is a crop of ONE global mask (random maps)
for T_ in (16, 32):
    r, rho = TR._params(T_, 0, None); ss = TR._supersample(T_); R = T_ * ss; rng = np.random.RandomState(T_)
    for trial in range(3):
        n = 9; grid = (ndi_blur := __import__("scipy.ndimage", fromlist=["x"]).gaussian_filter(rng.rand(n, n), 1.0)) > np.median(ndi_blur)
        F = np.kron(grid, np.ones((R, R), bool))
        gA, gR = TR._pipeline(F, T_, ss, r, rho, 1)
        bad = 0
        for y in range(1, n - 1):
            for x in range(1, n - 1):
                if not grid[y, x]: continue
                tA, tR = TR.tile_masks(TR.neighbor_mask(grid, x, y), "blob47", T_, 0, None, 1)
                sl = (slice(y * T_, (y + 1) * T_), slice(x * T_, (x + 1) * T_))
                bad += int((tA != gA[sl]).sum() + (tR != gR[sl]).sum())
        ok(bad == 0, f"{T_}px random map {trial}: every tile equals the crop of the whole-map mask (adjacent tiles join exactly, rim included)")

# ---------------- generated set ----------------
res = TR.generate_set(GRASS, DIRT, "blob47")
ims = [t["image"] for t in res["tiles"]]
ok(len(ims) == 47 and all(i.size == (16, 16) and i.mode == "RGBA" for i in ims) and res["ground"] is not None and len(res["lookup"]) == 256, "47 opaque tiles + ground tile + lookup")
allowed = {tuple(c) for c in np.asarray(GRASS).reshape(-1, 4)} | {tuple(c) for c in np.asarray(DIRT).reshape(-1, 4)} | {res["rim_color"]}
used = {tuple(c) for i in ims for c in np.asarray(i).reshape(-1, 4)}
ok(used <= allowed and res["rim_color"] not in {tuple(c) for c in np.asarray(GRASS).reshape(-1, 4)} and all((np.asarray(i)[..., 3] == 255).all() for i in ims), "only A's colours, B's colours and ONE rim colour; fully opaque when the ground is baked in")
ok(np.array_equal(np.asarray(res["tiles"][46]["image"]), np.asarray(GRASS)) and res["tiles"][46]["mask"] == 255, "tile 255 is exactly terrain A")
iso_img = np.asarray(res["tiles"][0]["image"]); ok(res["tiles"][0]["mask"] == 0 and (iso_img[0, 0] == np.asarray(DIRT)[0, 0]).all(), "tile 0 (no neighbours) shows the ground in its corners")
inside = TR.tile_masks(0, "blob47", 16, 0, None, 1)[0]
ok((np.asarray(res["tiles"][0]["image"])[~inside] == np.asarray(DIRT)[~inside]).all() and any(tuple(p) == res["rim_color"] for p in iso_img.reshape(-1, 4)), "outside the mask: B's pixels, in the same texture phase; the rim colour appears on the border")
dark = res["rim_color"]; lum = lambda c: .299 * c[0] + .587 * c[1] + .114 * c[2]
ok(lum(dark) < lum((40, 110, 50)), "the dark rim is darker than A's darkest colour")
lightres = TR.generate_set(GRASS, DIRT, "blob47", rim="light"); ok(lum(lightres["rim_color"]) > lum((60, 150, 60)), "the light rim is lighter than A's lightest colour")
nor = TR.generate_set(GRASS, DIRT, "blob47", rim="none"); ok(nor["rim_color"] is None and {tuple(c) for i in nor["tiles"] for c in np.asarray(i["image"]).reshape(-1, 4)} <= allowed - {res["rim_color"]}, "rim = none adds no colour")
tr = TR.generate_set(GRASS, None, "blob47"); ti = np.asarray(tr["tiles"][0]["image"])
ok(tr["base"] == "transparent" and ti[0, 0, 3] == 0 and ti[8, 8, 3] == 255 and tr["ground"] is None, "without a ground tile the set is transparent outside A")
tr2 = TR.generate_set(GRASS, DIRT, "blob47", base="transparent"); ok(np.asarray(tr2["tiles"][0]["image"])[0, 0, 3] == 0 and tr2["ground"] is None, "base = transparent ignores B")
ok(TR.generate_set(GRASS, DIRT, ground=False)["ground"] is None, "ground tile is optional")
e16 = TR.generate_set(GRASS, DIRT, "edge16"); ok(len(e16["tiles"]) == 16 and len(e16["lookup"]) == 256 and e16["tiles"][-1]["mask"] == 85, "edge16 set")
for sz in (8, 24, 48, 64):
    s = TR.generate_set(tex(sz, (60, 150, 60), (40, 110, 50), 3), tex(sz, (140, 100, 60), (110, 80, 50), 4), "edge16"); ok(all(t["image"].size == (sz, sz) for t in s["tiles"]), f"tile size {sz}")
big = TR.generate_set(tex(48, (60, 150, 60), (40, 110, 50), 3), None, "blob47"); a48 = TR.tile_masks(0, "blob47", 48, 0, None, 2)[1]; ok(a48.sum() > 0 and big["inset"] >= 2, "48 px tiles use a 2 px rim and a proportional inset")
c1 = TR.generate_set(GRASS, DIRT, "blob47", inset=2, rnd=0); c2 = TR.generate_set(GRASS, DIRT, "blob47", inset=5, rnd=3)
ok(c1["inset"] == 2 and c1["round"] == 0 and c2["inset"] == 4 and c2["round"] == 3, "inset / round are honoured and clamped (inset <= 30% of the tile so joins stay exact)")
ok(TR.generate_set(GRASS, DIRT, inset=99)["inset"] == 4, "huge inset is clamped")

# validation
def raises(fn, what):
    try: fn(); ok(False, what)
    except TR.TerrainError: ok(True, what + " -> TerrainError")
raises(lambda: TR.generate_set(GRASS, tex(32, (1, 2, 3), (4, 5, 6), 1)), "size mismatch A/B")
raises(lambda: TR.generate_set(Image.new("RGBA", (16, 24), (9, 9, 9, 255))), "non-square tile")
raises(lambda: TR.generate_set(Image.new("RGBA", (16, 16), (9, 9, 9, 0))), "transparent A")
raises(lambda: TR.generate_set(GRASS, kind="blob99"), "unknown kind")
raises(lambda: TR.generate_set(GRASS, rim="glow"), "unknown rim")
raises(lambda: TR.generate_set(Image.new("RGBA", (4, 4), (9, 9, 9, 255))), "tile too small")

# ---------------- export ----------------
tmp = tmpdir(); e = TR.export_terrain(res, "Meadow", dict(columns=8, godot=True, godot_path="res://art/terrain", tiled=True), tmp, "Grass!")
d = Path(e["dir"]); meta = json.loads((d / "terrain.json").read_text()); sheet = Image.open(d / "Meadow.png").convert("RGBA")
ok(e["count"] == 47 and e["ground"] and sheet.size == (8 * 16, 6 * 16) and len(meta["lookup"]) == 256 and len(meta["tiles"]) == 47 and meta["ground"]["index"] == 47, "sheet 8x6 with 47 tiles + ground, json with the 256-entry lookup")
ok(all(sheet.crop((m["x"], m["y"], m["x"] + 16, m["y"] + 16)).tobytes() == ims[m["index"]].tobytes() for m in meta["tiles"]), "every tile sits exactly in its json position")
g = meta["ground"]; ok(sheet.crop((g["x"], g["y"], g["x"] + 16, g["y"] + 16)).tobytes() == DIRT.tobytes(), "the ground tile is in the sheet")
tres = (d / "Meadow.tres").read_text()
ok('path="res://art/terrain/Meadow.png"' in tres and "terrain_set_0/mode = 0" in tres and 'terrain_set_0/terrain_0/name = "Grass"' in tres and "terrain_set_0/terrain_0/color = Color(" in tres and "load_steps=3" in tres, "Godot .tres: texture path, terrain set (match corners and sides), terrain name and colour")
cells = re.findall(r"^(\d+):(\d+)/0 = 0$", tres, re.M); ok(len(cells) == 48 and tres.count("/0/terrain_set = 0") == 47 and tres.count("/0/terrain = 0") == 47, "48 tiles registered, 47 of them in the terrain (the ground tile is not)")
def bits_of(col, row): return set(re.findall(rf"^{col}:{row}/0/terrains_peering_bit/(\w+) = 0$", tres, re.M))
idx_full = [t["index"] for t in res["tiles"] if t["mask"] == 255][0]; idx_iso = [t["index"] for t in res["tiles"] if t["mask"] == 0][0]; idx_n = [t["index"] for t in res["tiles"] if t["mask"] == 1][0]
ok(len(bits_of(idx_full % 8, idx_full // 8)) == 8 and not bits_of(idx_iso % 8, idx_iso // 8) and bits_of(idx_n % 8, idx_n // 8) == {"top_side"}, "peering bits: full tile has all 8, isolated none, mask N exactly top_side")
ok(bits_of(idx_full % 8, idx_full // 8) == {"right_side", "bottom_right_corner", "bottom_side", "bottom_left_corner", "left_side", "top_left_corner", "top_side", "top_right_corner"}, "the 8 Godot peering bit names")
tsx = (d / "Meadow.tsx").read_text(); dom = X.parseString(tsx); wt = dom.getElementsByTagName("wangtile")
ok(len(wt) == 47 and 'tilecount="48"' in tsx and 'type="mixed"' in tsx and 'name="Grass"' in tsx, "Tiled .tsx is valid XML with a mixed wang set of 47 tiles (ground tile excluded)")
w255 = [w for w in wt if w.getAttribute("tileid") == str(idx_full)][0].getAttribute("wangid"); w1 = [w for w in wt if w.getAttribute("tileid") == str(idx_n)][0].getAttribute("wangid")
ok(w255 == "1,1,1,1,1,1,1,1" and w1 == "1,0,0,0,0,0,0,0", "wang ids run top, topright, right, ... topleft")
e2 = TR.export_terrain(e16, "Edges", dict(godot=True, tiled=True), tmp); t2 = (Path(e2["dir"]) / "Edges.tres").read_text(); x2 = (Path(e2["dir"]) / "Edges.tsx").read_text()
ok("terrain_set_0/mode = 2" in t2 and "corner" not in t2.split("[resource]")[0] and 'type="edge"' in x2 and 'wangid="1,0,1,0,1,0,1,0"' in x2, "edge16: match-sides mode, no corner bits, Tiled edge wang set")
e3 = TR.export_terrain(tr, "Over", dict(godot=False, tiled=False), tmp); ok(e3["files"] == ["Over.png", "terrain.json", "README.txt"] and not e3["ground"] and e3["count"] == 47, "options: no Godot / Tiled files, no ground tile")
ok(Path(TR.export_terrain(res, "../../evil", {}, tmp)["dir"]).resolve().parent == (tmp / "exports").resolve(), "a hostile name cannot leave exports/")

# ---------------- endpoints ----------------
tmp2 = tmpdir(); M.ROOT = tmp2
b = M.TerrainBody(a=data_url(GRASS), b=data_url(DIRT), kind="blob47")
r = M.terrain_generate(b); ok(len(r["tiles"]) == 47 and r["tile_size"] == 16 and len(r["lookup"]) == 256 and from_url(r["tiles"][3]["image"]).size == (16, 16) and r["ground"] and r["tiles"][3]["mask"] in TR.canonical_masks("blob47"), "generate endpoint")
r = M.terrain_generate(M.TerrainBody(a=data_url(GRASS), kind="edge16")); ok(len(r["tiles"]) == 16 and r["ground"] is None and r["base"] == "transparent", "endpoint with only A")
for bad, what in ((M.TerrainBody(a="nonsense"), "broken image"), (M.TerrainBody(a=data_url(GRASS), b=data_url(tex(32, (1, 2, 3), (4, 5, 6), 1))), "size mismatch"), (M.TerrainBody(a=data_url(GRASS), kind="nope"), "bad kind")):
    try: M.terrain_generate(bad); ok(False, what)
    except HTTPException as ex: ok(ex.status_code == 400, what + " -> 400")
r = M.terrain_export(M.TerrainBody(a=data_url(GRASS), b=data_url(DIRT), name="endpoint", terrain_name="Grass", columns=8)); ok(r["count"] == 47 and (Path(r["dir"]) / "endpoint.tres").exists(), "export endpoint writes the files")

# ---------------- projects ----------------
projects.save(tmp2, "TW", {"images": {"terra": data_url(GRASS), "terrb": data_url(DIRT)}}); doc = projects.load(tmp2, "TW")
ok(doc["images"]["terra"] and from_url(doc["images"]["terrb"]).tobytes() == DIRT.tobytes(), "terrain A and B are saved with the project")
done("test_terrain")
