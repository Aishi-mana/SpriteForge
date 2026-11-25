"""Sprite-sheet export (layouts, pivots, Godot / Unity data) and project storage."""
import re
from _common import *
from engine import exporter as X, rig, projects

sp, J, OV = synth_sprite()
def entries(clips=("idle", "walk", "jump", "death"), n=4):
    out = []
    for c in clips:
        fr, meta = rig.render(sp, J, OV, c, n, "right", "r", "r", 1, 0, 1, 2)
        out.append({"name": c, "fps": 8, "loop": c not in rig.ONE_SHOT, "frames": fr, "pivot": meta["pivot"]})
    return out
root = tmpdir()
for opts in ({"layout": "rows"}, {"layout": "grid", "columns": 6, "padding": 2, "pot": True}, {"layout": "column", "uniform": False, "crop": False}):
    r = X.export_pack(entries(), {**opts, "gif": False}, "K", root); d = Path(r["dir"]); sheet = Image.open(d / "K_sheet.png"); at = json.load(open(d / "K_atlas.json"))
    rects = [(f["frame"]["x"], f["frame"]["y"], f["frame"]["w"], f["frame"]["h"]) for f in at["frames"].values()]
    occ = np.zeros((sheet.height, sheet.width), int)
    for x, y, w, h in rects: occ[y:y + h, x:x + w] += 1
    ok(all(x + w <= sheet.width and y + h <= sheet.height for x, y, w, h in rects) and not (occ > 1).any(), f"layout {opts['layout']}: every frame inside the sheet, no overlaps")
    if opts.get("pot"): ok((sheet.width & (sheet.width - 1)) == 0 and (sheet.height & (sheet.height - 1)) == 0, "power-of-two sheet")
r = X.export_pack(entries(("idle", "jump", "hurt", "death")), {"layout": "rows", "gif": False}, "K2", root); d = Path(r["dir"]); at = json.load(open(d / "K2_atlas.json")); sheet = Image.open(d / "K2_sheet.png")
for nm in ("idle", "jump", "hurt"):
    fr = at["frames"][f"K2_{nm} 0"]["frame"]; a = np.asarray(sheet.crop((fr["x"], fr["y"], fr["x"] + fr["w"], fr["y"] + fr["h"])))[..., 3] > 0
    ok(abs(np.nonzero(a.any(1))[0].max() - r["pivot"][1]) <= 4, f"{nm}: neutral frame's feet sit on the shared pivot (all clips line up)")
t = (d / "K2.tres").read_text(); subs = re.findall(r"\[sub_resource", t); ls = int(re.search(r"load_steps=(\d+)", t).group(1))
ok(ls == len(subs) + 2 and len(subs) == r["frames"], "Godot .tres: load_steps and sub-resource count agree")
reg = {tuple(map(int, m)) for m in re.findall(r"region = Rect2\((\d+), (\d+), (\d+), (\d+)\)", t)}
ok(reg == {(f["frame"]["x"], f["frame"]["y"], f["frame"]["w"], f["frame"]["h"]) for f in at["frames"].values()}, "Godot regions equal the atlas regions")
ok(all(f'&"{n}"' in t for n in ("idle", "jump", "hurt", "death")) and '"loop": false' in t and '"loop": true' in t, "Godot animations carry names and loop flags")
u = json.load(open(d / "K2_unity.json")); f0 = u["animations"][0]["frames"][0]; a0 = at["frames"]["K2_idle 0"]["frame"]
ok(f0["y"] == u["height"] - a0["y"] - a0["h"] and (d / "SpriteForgeImporter.cs").exists() and (d / "README.txt").exists(), "Unity data: Y is flipped to bottom-left origin; importer script and README written")
one = X.export_pack(entries(("walk",)), {"gif": True, "frames": True}, "One", root); ok(Path(one["dir"]).name == "One_walk" and (Path(one["dir"]) / "One_walk.gif").exists() and (Path(one["dir"]) / "frames" / "walk").exists(), "single clip -> <name>_<clip> folder with GIF and frames")
evil = X.export_pack([{**entries(("walk",))[0], "name": "../../evil"}], {"gif": False}, "n/../x", root); ok(str(root / "exports") in str(Path(evil["dir"]).resolve()), "names are sanitised: nothing is written outside exports/")
fr, meta = rig.render(sp, J, OV, "walk", 2, "right", "r", "r", 1, 0, 1, 2); e2 = rig.export(fr, meta, 10, "../../evil", "n/../x", root); ok(str(root / "exports") in str(Path(e2).resolve()), "legacy single-clip export is sanitised too")

root = tmpdir()
img = data_url(Image.new("RGBA", (8, 8), (200, 30, 30, 255)))
doc = {"settings": {"prompt": "knight", "afr": "8", "refine": True}, "rig": {"joints": J, "overrides": [[1, 2, 3]]}, "skeleton": {"pts": [[.5, .5]] * 18}, "anim_params": {"walk": {"afr": "8"}}, "tab": 4,
       "images": {"ref": img, "anim": img, "tpl": img, "tplref": img}, "palette": {"work": ["#ff0000"], "prot": ["#ff0000"]}, "template": {"joints": J, "ovr": [[1, 1, 1]]},
       "directions": {"slots": {"S": {"src": img, "joints": J, "ovr": []}}},
       "results": {"walk": {"anim": "walk", "fps": 10, "size": [8, 8], "pivot": [4, 8], "info": {"seed": 5}, "accept": [True, False], "frames": [img, img], "raw": [img, img]}},
       "portrait": {"base": img, "mask": {"cx": .5, "cy": .5, "rx": .2, "ry": .2}, "exprs": [{"name": "happy", "image": img}]}}
projects.save(root, "My Knight", doc); L = projects.load(root, "My Knight")
ok(L["settings"] == doc["settings"] and L["rig"] == doc["rig"] and L["tab"] == 4 and L["palette"] == doc["palette"] and L["template"] == doc["template"] and L["directions"]["slots"]["S"]["joints"] == J, "settings, rig, tab, palette, template and directions round-trip")
ok(all(L["images"][k] for k in ("ref", "anim", "tpl", "tplref")), "four project images round-trip")
rw = L["results"]["walk"]; ok(len(rw["frames"]) == 2 and len(rw["raw"]) == 2 and rw["accept"] == [True, False] and rw["fps"] == 10, "AI-cleanup results (frames, raw, accept flags) round-trip")
ok(L["portrait"]["mask"] == doc["portrait"]["mask"] and [e["name"] for e in L["portrait"]["exprs"]] == ["happy"], "portrait base, mask and expressions round-trip")
sid = projects.add_sprite(root, "My Knight", img); ok([s["id"] for s in projects.list_sprites(root, "My Knight")] == [sid], "saved sprites: add and list"); projects.delete_sprite(root, "My Knight", sid); ok(projects.list_sprites(root, "My Knight") == [], "...and delete")
projects.save(root, "My Knight", {"images": {}}); L = projects.load(root, "My Knight"); ok(L["results"] == {} and L["portrait"] is None and L["images"]["ref"] is None, "saving without them clears results, portrait and images")
for bad in ("", "   ", ".."):
    try: projects.safe_name(bad); ok(False, f"name {bad!r}")
    except projects.ProjectError: ok(True, f"project name {bad!r} rejected")
ok(projects._dir(root, "../../etc").parent.name == "projects", "path traversal in names cannot escape the projects folder")
try: projects.save(root, "x", {"images": {"ref": "data:image/png;base64,AAAA"}}); ok(False, "bad image")
except Exception: ok(True, "a corrupt image is rejected, never written")
ok(projects.list_projects(root)[0]["name"] == "My Knight", "listing works"); projects.delete(root, "My Knight"); ok(projects.list_projects(root) == [], "delete works")
done("test_export_projects")
