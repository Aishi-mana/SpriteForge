"""Rig animation, secondary motion, view-aware walks."""
import math
from _common import *
from engine import rig, templates as T

sp, J, OV = synth_sprite(); n0 = int((np.asarray(sp)[..., 3] > 0).sum())
for facing in ("right", "left"):
    bad = []
    for c in rig.CLIPS:
        fr, meta = rig.render(sp, J, OV, c, 6, facing, "r", "r", 1.0, 0, 1, 4)
        if len(fr) != 6 or min(int((np.asarray(f)[..., 3] > 0).sum()) for f in fr) < .55 * n0: bad.append(c)
    ok(not bad, f"all 11 clips render facing {facing} without losing the character" + (f" (bad: {bad})" if bad else ""))
fr, meta = rig.render(sp, J, OV, "walk", 1, "right", "r", "r", 1, 0, 1, 4); ok(len(fr) == 1, "a single-frame animation works")
dw = rig.render(sp, J, OV, "death", 4, "right", "r", "r", 1, 0, 1, 4)[1]["size"][0]; wk = rig.render(sp, J, OV, "walk", 4, "right", "r", "r", 1, 0, 1, 4)[1]["size"][0]
ok(dw > wk + 20, f"death auto-pads a much wider canvas ({dw} vs {wk}) so the body can fall over")
fr, meta = rig.render(sp, J, OV, "walk", 4, "right", "r", "r", 1, 0, 1, 4); ok(len(meta["joints"]) == 4 and "r_elbow" in meta["joints"][0], "meta carries per-frame joint positions (used by AI cleanup)")
lab = rig.assign_parts(sp, J, OV); ok((lab >= 0).sum() == n0 and lab[10, 30] == rig.BONE_IDX["r_arm_l"], "every opaque pixel is assigned; painted overrides win")
j2 = rig.autoplace(sp); ok(set(j2) == set(rig.JOINTS), "autoplace returns all 15 joints")

def spread(frames):
    out = []
    for f in frames:
        a = np.asarray(f)[..., 3] > 0; ys = np.nonzero(a.any(1))[0]; y0 = ys.min() + int(.6 * (ys.max() - ys.min())); xs = np.nonzero(a[y0:].any(0))[0]; out.append(xs.max() - xs.min() + 1)
    return max(out) - min(out)
spf, jf, ovf = T.make_dummy(64, "normal", "front")
s = {v: spread(rig.render(spf, jf, ovf, "walk", 8, "right", "both", "r", 1, 0, 1, 4, view=v)[0]) for v in ("side", "diag", "front")}
ok(s["front"] < s["diag"] < s["side"], f"leg scissoring shrinks side > diag > front {s}")
a = rig.render(sp, J, OV, "run", 4, "right", "r", "r", 1, 0, 1, 4)[0]; b = rig.render(sp, J, OV, "run", 4, "right", "r", "r", 1, 0, 1, 4, view="side")[0]
ok(all((np.asarray(x) == np.asarray(y)).all() for x, y in zip(a, b)), "default view equals view='side'")

hero, JH, OH = hero_sprite(); hn = int((np.asarray(hero)[..., 3] > 0).sum())
lab = rig.assign_parts(hero, JH, OH); ok((lab == 10).sum() == 279 and (lab == 11).sum() == 42, "cape / hair labels accepted by painting")
parts = rig._prep_secondary(lab, JH, {"parts": {}}); ok([p["name"] for p in parts] == ["cape", "hair"] and parts[0]["u"][1] > .9, "only painted parts become chains; the cape hangs downward from the neck")
sec = {"enabled": True, "flutter": 1, "stiffness": 1, "damping": .35, "parts": {}}
for anim in ("idle", "walk", "run"):
    pt = rig._prep_secondary(lab, JH, sec)[0]; pa = np.array([(0, 3 * math.sin(2 * math.pi * i / 8)) for i in range(8)]); psi = np.zeros(8)
    r1 = rig._simulate(pt, psi, pa, anim, True, -1, 64, sec, cycles=10); r2 = rig._simulate(pt, psi, pa, anim, True, -1, 64, sec, cycles=16)
    ok(np.abs(r1 - r2).max() < .3, f"{anim}: looping simulation is steady, so the loop is seamless (drift {np.abs(r1 - r2).max():.3f} deg)")
def cape_x(frames): return np.mean([np.nonzero((np.asarray(f)[..., 3] > 0) & (np.asarray(f)[..., 0] > 100) & (np.asarray(f)[..., 1] < 60))[1].mean() for f in frames])
xi = cape_x(rig.render(hero, JH, OH, "idle", 8, "right", "r", "r", 1, 0, 1, 4, secondary=sec)[0]); xw = cape_x(rig.render(hero, JH, OH, "walk", 8, "right", "r", "r", 1, 0, 1, 4, secondary=sec)[0]); xr = cape_x(rig.render(hero, JH, OH, "run", 8, "right", "r", "r", 1, 0, 1, 4, secondary=sec)[0])
ok(xr < xw < xi + .2, "the cape trails further behind when walking, and further when running")
xil = cape_x(rig.render(hero, JH, OH, "idle", 8, "left", "r", "r", 1, 0, 1, 4, secondary=sec)[0]); xrl = cape_x(rig.render(hero, JH, OH, "run", 8, "left", "r", "r", 1, 0, 1, 4, secondary=sec)[0])
ok(xrl > xil and xr < xi, "facing left mirrors the lag")
for label, s_ in (("off", {"enabled": False}), ("None", None)):
    fr = rig.render(hero, JH, OH, "idle", 4, "right", "r", "r", 1, 0, 1, 4, secondary=s_)[0]
    ok(int(((np.asarray(fr[0])[..., 0] > 120) & (np.asarray(fr[0])[..., 1] < 50)).sum()) > 150, f"secondary {label}: painted cape/hair stay attached to the body (never vanish)")
few = [[5, 20, 10], [6, 20, 10], [7, 20, 10]]; fr = rig.render(hero, JH, few, "walk", 4, "right", "r", "r", 1, 0, 1, 4, secondary={"enabled": True})[0]; ok(int((np.asarray(fr[0])[..., 3] > 0).sum()) > .8 * hn, "a tiny painted part falls back to the body")
for label, s_ in (("flutter 0", {**sec, "flutter": 0}), ("stiff", {**sec, "stiffness": 2, "damping": .9}), ("soft", {**sec, "stiffness": .4, "damping": .1}), ("1 seg", {**sec, "parts": {"cape": {"segments": 1}}}), ("6 seg", {**sec, "parts": {"cape": {"segments": 6}}}), ("front", {**sec, "parts": {"cape": {"front": True}}})):
    fr = rig.render(hero, JH, OH, "run", 6, "right", "r", "r", 1, 0, 1, 4, secondary=s_)[0]; ok(all((np.asarray(f)[..., 3] > 0).sum() > .75 * hn for f in fr), f"secondary settings '{label}' render fine")
fr, meta = rig.render(hero, JH, OH, "walk", 4, "right", "r", "r", 1, 0, 1, 4, secondary=sec); ok("cape_1" in meta["joints"][0] and meta["secondary"] == ["cape", "hair"], "cloth joints are reported so AI cleanup can treat them too")
done("test_rig")
