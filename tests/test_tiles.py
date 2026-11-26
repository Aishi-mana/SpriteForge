"""Tiles and props: seamless maths, pixel seam repair, tile generation (fake SDXL), tileset / atlas export, projects, queue."""
from _common import *
install_fastapi_stubs()
from engine import tiles as T, main as M, projects, generate as G
HTTPException = http_exception()

def texture(n=1024, seed=1):
    """A realistic AI-like texture: low-frequency structure + a strong left-to-right trend (=> a hard seam) + fine noise."""
    r = np.random.RandomState(seed); y, x = np.mgrid[0:n, 0:n] / n
    base = 110 + 60 * np.sin(6.0 * x + 2 * y) + 40 * np.cos(9.0 * y - 3 * x) + 90 * x          # the trend makes left != right
    g = np.stack([base, base * 0.8 + 20 * np.sin(11 * x), base * 0.6 + 30 * np.cos(7 * y)], -1) + r.normal(0, 6, (n, n, 3))
    return Image.fromarray(np.clip(g, 0, 255).astype(np.uint8), "RGB")

# ---------------- seamless maths ----------------
raw = texture(); s0 = T.seam_score(raw); seam = T.make_seamless(raw); s1 = T.seam_score(seam)
ok(s0 > 3 and s1 < 1.6 and s1 < s0 / 3, f"smooth blend removes the seam (score {s0} -> {s1})")
a = np.asarray(seam).astype(int); step = np.abs(np.diff(a, axis=1)).mean(); ok(np.abs(a[:, 0] - a[:, -1]).mean() < 1.3 * step and np.abs(a[0] - a[-1]).mean() < 1.3 * step, "the wrap-around join is no bigger than a normal neighbour step")
w = T._weights(64, 48, .5); ok(w[0].max() == 0 and w[-1].max() == 0 and w[:, 0].max() == 0 and w[:, -1].max() == 0 and w[32, 24] > .99, "weight is exactly 0 on all four borders, 1 in the middle")
big = T.make_seamless(texture(256, 2)); ok(big.size == (256, 256) and big.mode == "RGB", "size and mode preserved")

# pixel tile with a 6-colour palette and a visible seam
pal = np.array([[20, 24, 40], [60, 90, 50], [90, 140, 70], [140, 190, 90], [200, 180, 120], [240, 230, 200]], np.uint8)
def pixel_tile(w=32, h=32):
    y, x = np.mgrid[0:h, 0:w]; idx = ((x * 6 // w) + ((x * 7 + y * 3) % 5 == 0)) % 6          # left dark -> right light, with speckles
    return Image.fromarray(np.dstack([pal[idx], np.full((h, w), 255, np.uint8)]), "RGBA")
for (w_, h_) in ((32, 32), (31, 17), (16, 24)):
    pt = pixel_tile(w_, h_); fixed = T.seamless_pixels(pt)
    cols0 = {tuple(c) for c in np.asarray(pt).reshape(-1, 4)}; cols1 = {tuple(c) for c in np.asarray(fixed).reshape(-1, 4)}
    ok(fixed.size == pt.size and cols1 <= cols0, f"{w_}x{h_}: pixel seam repair invents no colours")
    f = np.asarray(fixed).astype(int)[..., :3]; src = np.roll(np.asarray(pt), (h_ // 2, w_ // 2), axis=(0, 1)).astype(int)[..., :3]
    ok((f[:, 0] == src[:, 0]).all() and (f[:, -1] == src[:, -1]).all() and (f[0] == src[0]).all() and (f[-1] == src[-1]).all(), f"{w_}x{h_}: the border comes from the shifted copy (continuous by construction)")
pt = pixel_tile(); ok(T.seam_score(T.seamless_pixels(pt)) < T.seam_score(pt) / 2, "pixel seam score drops")
o = T.wrap_offset(pt); ok(np.array_equal(np.asarray(T.wrap_offset(o)), np.asarray(pt)), "offset by half twice restores an even-sized tile")
o = T.wrap_offset(pixel_tile(31, 17), 5, 3); ok(np.array_equal(np.asarray(T.wrap_offset(o, 31 - 5, 17 - 3)), np.asarray(pixel_tile(31, 17))), "offset is a wrap-around shift (odd sizes too)")
ok(T.tiled(pt, 3, 2).size == (96, 64), "tiled preview size")

# ---------------- tile generation ----------------
sp, info = T.tile_post(raw, 32, 12, "none", True)
arr = np.asarray(sp)
ok(sp.size == (32, 32) and (arr[..., 3] == 255).all(), "a tile is exactly size x size, fully opaque (no crop, no background removal)")
ok(len({tuple(c) for c in arr.reshape(-1, 4)}) <= 12 and info["seam"] < info["seam_raw"] / 2 and info["label"].startswith("seam"), f"palette limit respected, seam {info['seam_raw']} -> {info['seam']}")
sp2, i2 = T.tile_post(raw, 32, 12, "none", False); ok(i2["seam"] > 2 * info["seam"], "seamless off keeps the raw seam (so the option really does something)")
for sz in (16, 24, 48, 64):
    s_, _ = T.tile_post(texture(512, 3), sz, 16); ok(s_.size == (sz, sz), f"tile size {sz} (also non-divisors of the render size)")

# fake SDXL (positional signature of gen.generate)
tmp = tmpdir(); M.ROOT = tmp; M.CFG_PATH = tmp / "config.json"; md = tmp / "m"; (md / "checkpoints").mkdir(parents=True); (md / "loras").mkdir(); mock_sdxl_checkpoint(md / "checkpoints" / "sd_xl_base_1.0.safetensors")
M.CFG_PATH.write_text(json.dumps({"models_dir": str(md)})); calls = []
def fake_generate(*a, **k):
    calls.append(a); kind = a[17]
    if kind == "tile": img = texture(1024, a[8])
    else:
        img = Image.new("RGB", (1024, 1024), (255, 255, 255)); from PIL import ImageDraw; ImageDraw.Draw(img).ellipse([300, 300, 700, 700], fill=(200, 40, 40))
    return [(img, a[8] + i) for i in range(a[13])]
M.gen.generate = fake_generate; CK = "sd_xl_base_1.0.safetensors"
r = M._do_generate(M.GenParams(prompt="mossy cobblestone", checkpoint=CK, kind="tile", size=32, colors=10, n=2, seed=4))
ok(calls[-1][17] == "tile" and len(r["results"]) == 2 and from_url(r["results"][0]["sprite"]).size == (32, 32) and r["results"][0]["info"]["seam"] < r["results"][0]["info"]["seam_raw"], "kind=tile generates seamless size x size tiles")
r = M._do_generate(M.GenParams(prompt="mossy", checkpoint=CK, kind="tile", size=32, seamless=False, n=1, seed=4)); ok(r["results"][0]["info"]["seam"] > 2, "seamless=false is honoured by the endpoint")
r = M._do_generate(M.GenParams(prompt="health potion", checkpoint=CK, kind="icon", size=32, n=1, seed=1)); sz = from_url(r["results"][0]["sprite"]).size
ok(calls[-1][17] == "icon" and max(sz) <= 32 and min(sz) >= 8, f"kind=icon: normal pixel pipeline, cropped to the object ({sz})")
M._do_generate(M.GenParams(prompt="x", checkpoint=CK, kind="bogus", size=32)); ok(calls[-1][17] == "sprite", "unknown kind falls back to sprite")
ok("seamless" in G.build_prompt("grass", "white", "tile") and "icon" in G.build_prompt("sword", "white", "icon") and "user interface" in G.build_prompt("health bar", "white", "ui") and "prop" in G.build_prompt("barrel", "white", "prop"), "prompt templates per kind")
ok(G.negative_for("sprite") == G.NEGATIVE and G.negative_for("portrait") == G.NEGATIVE_PORTRAIT and "single object" in G.negative_for("tile") and "multiple objects" in G.negative_for("prop"), "negative prompts per kind (sprite and portrait unchanged)")

# ---------------- export ----------------
def tile(c, n=16): return Image.new("RGBA", (n, n), (*c, 255))
tl = [tile((200, 30, 30)), tile((30, 200, 30)), tile((30, 30, 200)), tile((200, 200, 30)), tile((9, 9, 9))]
e = T.export_tileset(tl, ["grass", "grass", "", "dirt/../x", "water"], dict(columns=3, spacing=2, margin=1, godot=True, godot_path="res://art/tiles", tiled=True), "My Tiles!", tmp)
d = Path(e["dir"]); sheet = Image.open(d / "My_Tiles.png").convert("RGBA"); meta = json.loads((d / "tileset.json").read_text())
ok(e["mode"] == "tileset" and sheet.size == (1 * 2 + 3 * 16 + 2 * 2, 1 * 2 + 2 * 16 + 1 * 2) == tuple(meta["sheet"]) and e["columns"] == 3 and e["rows"] == 2, "grid sheet size accounts for margin and spacing")
ok(all(sheet.getpixel((m["x"] + 3, m["y"] + 3))[:3] == tl[m["index"]].getpixel((3, 3))[:3] for m in meta["tiles"]), "every tile sits exactly in its json region")
ok(e["names"] == ["grass", "grass_2", "tile_02", "dirt_x", "water"] and ".." not in "".join(e["names"]), "names are unique and sanitised")
tres = (d / "My_Tiles.tres").read_text()
ok('path="res://art/tiles/My_Tiles.png"' in tres and "texture_region_size = Vector2i(16, 16)" in tres and "margins = Vector2i(1, 1)" in tres and "separation = Vector2i(2, 2)" in tres
   and "0:0/0 = 0" in tres and "2:0/0 = 0" in tres and "1:1/0 = 0" in tres and "2:1/0 = 0" not in tres and tres.count("/0 = 0") == 5 and "load_steps=3" in tres, "Godot 4 TileSet resource: atlas source, size, margins, one entry per tile")
tsx = (d / "My_Tiles.tsx").read_text(); ok('tilecount="5"' in tsx and 'columns="3"' in tsx and 'spacing="2"' in tsx and 'margin="1"' in tsx and f'width="{sheet.width}"' in tsx and 'source="My_Tiles.png"' in tsx, "Tiled .tsx")
import xml.dom.minidom as X; X.parseString(tsx); ok(True, "the .tsx is well-formed XML")
e2 = T.export_tileset(tl[:2], [], dict(columns=8, godot=False, tiled=False), "plain", tmp); ok(e2["files"] == ["plain.png", "tileset.json", "README.txt"] and e2["sheet"] == [32, 16], "Godot/Tiled files are optional; columns are clamped to the tile count")
mixed = [Image.new("RGBA", (16, 24), (255, 0, 0, 255)), Image.new("RGBA", (40, 10), (0, 255, 0, 255)), Image.new("RGBA", (8, 8), (0, 0, 255, 255)), Image.new("RGBA", (30, 30), (255, 255, 0, 255))]
e3 = T.export_tileset(mixed, ["tree", "bench", "gem", "crate"], {}, "props", tmp); at = json.loads((Path(e3["dir"]) / "atlas.json").read_text()); sh = Image.open(Path(e3["dir"]) / "props.png").convert("RGBA")
rects = [(f["frame"]["x"], f["frame"]["y"], f["frame"]["w"], f["frame"]["h"]) for f in at["frames"].values()]
inside = all(x >= 0 and y >= 0 and x + w <= sh.width and y + h <= sh.height for x, y, w, h in rects)
overlap = any(a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3] for i, a in enumerate(rects) for b in rects[i + 1:])
ok(e3["mode"] == "atlas" and inside and not overlap and sh.getpixel((at["frames"]["gem"]["frame"]["x"] + 2, at["frames"]["gem"]["frame"]["y"] + 2)) == (0, 0, 255, 255), "different sizes -> packed atlas: no overlaps, all inside, pixels in place")
for bad in ([], ):
    try: T.export_tileset(bad, [], {}, "x", tmp); ok(False, "empty")
    except T.TileError: ok(True, "exporting nothing -> TileError")
ok(Path(T.export_tileset(tl[:1], [], {}, "../../evil", tmp)["dir"]).resolve().parent == (tmp / "exports").resolve(), "a hostile tileset name cannot leave exports/")

# ---------------- endpoints ----------------
up = Up(pixel_tile()); r = M.tiles_seamless(up); ok(from_url(r["sprite"]).size == (32, 32) and r["info"]["seam"] < r["info"]["seam_before"], "seamless endpoint")
try: M.tiles_seamless(Up(Image.new("RGBA", (900, 900)))); ok(False, "too big")
except HTTPException as ex: ok(ex.status_code == 400, "oversized tile -> 400")
r = M.tiles_offset(Up(pixel_tile()), -1, -1); ok(np.array_equal(np.asarray(from_url(r["sprite"])), np.asarray(T.wrap_offset(pixel_tile()))), "offset endpoint (default = half)")
body = M.TileSetBody(name="town", tiles=[{"name": "a", "image": data_url(tl[0])}, {"name": "b", "image": data_url(tl[1])}], columns=2)
r = M.tiles_export(body); ok(r["count"] == 2 and (Path(r["dir"]) / "town.png").exists(), "export endpoint writes the files")
try: M.tiles_export(M.TileSetBody(name="x", tiles=[{"name": "bad", "image": "nonsense"}])); ok(False, "bad tile")
except HTTPException as ex: ok(ex.status_code == 400 and "tile 1" in ex.detail, "a broken tile image -> readable 400")
try: M.tiles_export(M.TileSetBody(name="x", tiles=[])); ok(False, "none")
except HTTPException as ex: ok(ex.status_code == 400, "no tiles -> 400")

# ---------------- projects + queue ----------------
data = {"images": {"tile": data_url(tl[0])}, "tileset": {"tiles": [{"name": "grass", "image": data_url(tl[0])}, {"name": "dirt", "image": data_url(tl[3])}]}}
projects.save(tmp, "World", data); doc = projects.load(tmp, "World")
ok([t["name"] for t in doc["tileset"]["tiles"]] == ["grass", "dirt"] and from_url(doc["tileset"]["tiles"][1]["image"]).getpixel((0, 0)) == (200, 200, 30, 255) and doc["images"]["tile"], "the tileset and the workbench tile are saved with the project")
projects.save(tmp, "World", {}); doc = projects.load(tmp, "World"); ok(doc["tileset"] is None and doc["images"]["tile"] is None, "saving an empty tileset removes the old files")
j = M.queue_add(dict(kind="generate", params=dict(prompt="lava", checkpoint=CK, kind="tile", size=16, n=1, seed=2))); M._jobmgr().wait_idle(20)
h = M.history_list()["jobs"][0]; ok(h["sub"] == "tile" and from_url(M.job_get(j["id"])["results"][0]["sprite"]).size == (16, 16), "tile jobs go through the queue and are labelled in the history")
M._jobmgr().shutdown()
done("test_tiles")
