"""4 / 8 direction sets: mirroring, view-aware walks, ordering, aligned export."""
from _common import *
from engine import directions as D, templates as T

slots = {d: dict(zip(("sprite", "joints", "ovr"), T.make_dummy(64, "normal", D.DUMMY_VIEW[d]))) for d in D.UNIQUE}
clips = [{"anim": "walk", "count": 6, "fps": 10, "amp": 1, "pad": 0, "overlap": 1, "weapon": "r"}, {"anim": "idle", "count": 4, "fps": 6}]
ok(D.needed(D.DIRS8) == D.UNIQUE and D.needed(["S", "W", "N", "E"]) == ["S", "E", "N"] and D.needed(["W"]) == ["E"], "needed(): 8 dirs -> 5 views, 4 dirs -> 3 views, W -> E")
try: D.needed(["X"]); ok(False, "unknown")
except D.DirectionError: ok(True, "unknown direction rejected")
res = D.render_directions(slots, clips, D.DIRS8); ok(len(res) == 16 and all(len(v[0]) == (6 if k[0] == "walk" else 4) for k, v in res.items()), "2 clips x 8 directions, right frame counts")
for m_, s_ in D.MIRROR.items():
    a = [np.asarray(f) for f in res[("walk", m_)][0]]; b = [np.asarray(f)[:, ::-1] for f in res[("walk", s_)][0]]; w = res[("walk", s_)][1]["size"][0]
    ok(all((x == y).all() for x, y in zip(a, b)) and abs(res[("walk", m_)][1]["pivot"][0] - (w - res[("walk", s_)][1]["pivot"][0])) < 1e-6, f"{m_} = exact mirror of {s_}, pivot mirrored")
def spread(frames):
    out = []
    for f in frames:
        a = np.asarray(f)[..., 3] > 0; ys = np.nonzero(a.any(1))[0]; y0 = ys.min() + int(.6 * (ys.max() - ys.min())); xs = np.nonzero(a[y0:].any(0))[0]; out.append(xs.max() - xs.min() + 1)
    return max(out) - min(out)
sp = {d: spread(res[("walk", d)][0]) for d in ("S", "SE", "E", "N", "NE")}; ok(sp["S"] < sp["SE"] <= sp["E"] and sp["N"] < sp["NE"], f"front/back step in place, three-quarter swings less {sp}")
try: D.render_directions({k: v for k, v in slots.items() if k != "NE"}, clips, D.DIRS8); ok(False, "missing")
except D.DirectionError as e: ok("NE" in str(e), "missing view -> clear error")
sec = {"enabled": True, "parts": {"cape": {"segments": 3, "front": False}}}
ok(D._sec_for(sec, "N")["parts"]["hair"]["front"] is True and D._sec_for(sec, "S")["parts"]["cape"]["front"] is False and D._sec_for(None, "N") is None, "secondary parts go in front only from behind; partial settings fine")
root = tmpdir(); r = D.export_directions(slots, clips, D.DIRS8, "cw8", {"gif": False, "crop": True}, "Hero", None, root); d = Path(r["dir"]); at = json.load(open(d / "Hero_atlas.json"))
want = [f"{c}_{x.lower()}" for c in ("walk", "idle") for x in D.DIRS8]; ok([t["name"] for t in at["meta"]["frameTags"]] == want, "16 animations named <clip>_<dir> in clockwise row order")
ok(len({(f["frame"]["w"], f["frame"]["h"]) for f in at["frames"].values()}) == 1 and len({(f["pivotPx"]["x"], f["pivotPx"]["y"]) for f in at["frames"].values()}) == 1, "one shared cell size and one feet pivot for every direction")
sheet = np.asarray(Image.open(d / "Hero_sheet.png")); px_, py_ = list({(f["pivotPx"]["x"], f["pivotPx"]["y"]) for f in at["frames"].values()})[0]; bad = []
for nm, f in at["frames"].items():
    if nm.startswith("Hero_idle") and nm.endswith(" 0"):
        fr = f["frame"]; a = sheet[fr["y"]:fr["y"] + fr["h"], fr["x"]:fr["x"] + fr["w"]][..., 3] > 0; ys = np.nonzero(a.any(1))[0]; cx = np.nonzero(a[max(ys.max() - 2, 0):ys.max() + 1].any(0))[0].mean()
        if abs(cx - px_) > 3 or abs(ys.max() + 1 - py_) > 5: bad.append(nm)
ok(not bad, "in every direction the feet sit on the pivot (directions swap without a jump)")
meta = json.load(open(d / "directions.json")); ok(meta["directions"] == D.DIRS8 and meta["mirrored"] == D.MIRROR, "directions.json lists rows and mirrors")
rr = D.export_directions(slots, clips[:1], ["S", "W", "N", "E"], "rpg4", {"gif": False}, "Rpg", None, root); ok(rr["directions"] == ["S", "W", "E", "N"], "RPG Maker order: down, left, right, up")
done("test_directions")
