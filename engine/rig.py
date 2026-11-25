"""Rig-based sprite animation: assign pixels to bones, move bones with procedural clips, re-render.
Identity is perfect because every output pixel is an original sprite pixel."""
import json, math, re
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from . import pixelize as px, softmesh

JOINTS = ["head", "neck", "pelvis", "l_shoulder", "l_elbow", "l_wrist", "r_shoulder", "r_elbow", "r_wrist",
          "l_hip", "l_knee", "l_ankle", "r_hip", "r_knee", "r_ankle"]
# name, pivot joint, tip joint, parent, extends past the tip (hand/sword, foot, hair), assignment weight (thicker = bigger)
BONES = [
    ("torso", "pelvis", "neck", None, False, 2.4),
    ("head", "neck", "head", "torso", True, 2.2),
    ("l_arm_u", "l_shoulder", "l_elbow", "torso", False, 1.0),
    ("l_arm_l", "l_elbow", "l_wrist", "l_arm_u", True, 1.0),
    ("r_arm_u", "r_shoulder", "r_elbow", "torso", False, 1.0),
    ("r_arm_l", "r_elbow", "r_wrist", "r_arm_u", True, 1.0),
    ("l_leg_u", "l_hip", "l_knee", None, False, 1.3),
    ("l_leg_l", "l_knee", "l_ankle", "l_leg_u", True, 1.1),
    ("r_leg_u", "r_hip", "r_knee", None, False, 1.3),
    ("r_leg_l", "r_knee", "r_ankle", "r_leg_u", True, 1.1),
]
BONE_NAMES = [b[0] for b in BONES]
BONE_IDX = {n: i for i, n in enumerate(BONE_NAMES)}
BONE_RGB = [(255, 99, 99), (255, 214, 102), (102, 217, 102), (80, 200, 200), (102, 153, 255), (190, 120, 255),
            (255, 150, 60), (200, 200, 120), (255, 120, 200), (150, 255, 200)]
# Secondary motion: pixels painted as cape / hair / tail become spring-driven chains that lag behind the body.
BONE_RGB += [(120, 70, 200), (240, 170, 60), (60, 200, 140)]
SEC_PARTS = [("cape", "torso"), ("hair", "head"), ("tail", None)]  # (name, body bone it hangs from; None = whole body)
SEC_LABEL = {n: len(BONES) + i for i, (n, _) in enumerate(SEC_PARTS)}
SEC_DEFAULTS = {"cape": dict(omega=.75, grav=.45, gain=3.0, segments=3), "hair": dict(omega=1.0, grav=.30, gain=3.5, segments=2),
                "tail": dict(omega=.8, grav=.20, gain=3.0, segments=3)}
WIND_SPEED = {"walk": 1.5, "run": 6.0, "climb": 0.0}  # pseudo air-speed blowing backwards (normalised px/frame)
BREEZE = {"idle": 3.0}                                 # degrees of gentle periodic sway for looping clips
CLIPS = ["idle", "walk", "run", "attack", "jump", "hurt", "death", "cast", "climb", "block", "cheer"]
ONE_SHOT = {"custom", "attack", "jump", "hurt", "death", "cast", "block"}  # play once; the rest loop (written to the atlas as "loop")
CLIP_PAD = {"death": .8, "jump": .3, "attack": .28, "cast": .28}  # canvas margin as a fraction of sprite size


def autoplace(sprite):
    """Rough humanoid joint layout from the sprite's bounding box. The user fine-tunes it in the UI."""
    a = np.asarray(sprite.convert("RGBA"))[..., 3] >= 128
    ys, xs = np.where(a)
    if not len(ys):
        raise ValueError("sprite is empty")
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    W, H, cx = x1 - x0, y1 - y0, (x0 + x1) / 2

    def P(fx, fy):
        return [round(float(cx + fx * W), 1), round(float(y0 + fy * H), 1)]
    return {"head": P(0, .05), "neck": P(0, .30), "pelvis": P(0, .56),
            "l_shoulder": P(-.17, .34), "l_elbow": P(-.22, .46), "l_wrist": P(-.22, .58),
            "r_shoulder": P(.17, .34), "r_elbow": P(.22, .46), "r_wrist": P(.22, .58),
            "l_hip": P(-.07, .58), "l_knee": P(-.08, .78), "l_ankle": P(-.08, .95),
            "r_hip": P(.07, .58), "r_knee": P(.08, .78), "r_ankle": P(.08, .95)}


def is_hd(sprite):
    return max(sprite.size) > 160


def assign_parts(sprite, joints, overrides=None):
    """Label every opaque pixel with a bone index (-1 = transparent): nearest weighted bone segment, then manual paint."""
    arr = np.asarray(sprite.convert("RGBA"))
    opaque = arr[..., 3] >= (1 if is_hd(sprite) else 128)
    H, W = opaque.shape
    ys, xs = np.mgrid[0:H, 0:W]
    P = np.stack([xs + .5, ys + .5], -1).astype(np.float32)
    best = np.full((H, W), 1e9, np.float32)
    lab = np.full((H, W), -1, np.int16)
    for i, (_, a, b, _, ext, w) in enumerate(BONES):
        A, B = np.array(joints[a], np.float32), np.array(joints[b], np.float32)
        d = B - A
        t = ((P - A) @ d) / max(float(d @ d), 1e-6)
        t = np.maximum(t, 0) if ext else np.clip(t, 0, 1)
        dist = np.linalg.norm(P - (A + t[..., None] * d), axis=-1) / w
        m = dist < best
        best[m], lab[m] = dist[m], i
    lab[~opaque] = -1
    for x, y, b in (overrides or []):
        x, y, b = int(x), int(y), int(b)
        if 0 <= x < W and 0 <= y < H and opaque[y, x] and 0 <= b < len(BONES) + len(SEC_PARTS):
            lab[y, x] = b
    return lab


def overlay_image(lab):
    out = np.zeros(lab.shape + (4,), np.uint8)
    for i, c in enumerate(BONE_RGB):
        out[lab == i] = (*c, 255)
    return Image.fromarray(out, "RGBA")


# ---------------- animation clips ----------------
def _ease(x):
    return .5 - .5 * math.cos(math.pi * x)


def _kf(keys, t):
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, a), (t1, b) in zip(keys, keys[1:]):
        if t <= t1:
            u = _ease((t - t0) / (t1 - t0))
            return {k: a.get(k, 0) * (1 - u) + b.get(k, 0) * u for k in set(a) | set(b)}
    return keys[-1][1]


# Walk / run seen from other directions: (thigh swing, knee bend, arm swing, body bob, lean, sideways sway).
# Seen from the front or back, legs cannot swing sideways like in a side view, so the walk becomes a small step-and-bob.
VIEW_SCALE = {"side": (1, 1, 1, 1, 1, 0), "diag": (.65, .9, .6, 1.1, .6, 0), "front": (.28, .4, .25, 1.7, 0, .012)}


def _sem(anim, i, n, amp, weapon, view="side"):
    """Semantic pose in 'forward' degrees (so it works facing either way). dx/dy are fractions of sprite height."""
    s = {}
    if anim in ("idle", "walk", "run"):
        ph = 2 * math.pi * i / n
        sn, cs = math.sin(ph), math.cos(ph)
        if anim == "idle":
            s = dict(dy=-.012 * (.5 - .5 * math.cos(ph)), torso=.8 * sn, head=-1.2 * math.sin(ph - .6),
                     au_L=1.5 * math.sin(ph - .3), au_R=-1.5 * math.sin(ph - .3), al_L=8, al_R=8)
        else:
            A, K, Aa, bend, lean, bob = (28, 38, 22, 14, 3, .022) if anim == "walk" else (48, 78, 45, 65, 10, .05)
            vs = VIEW_SCALE.get(view, VIEW_SCALE["side"])
            A, K, Aa, bob, lean = A * amp * vs[0], K * amp * vs[1], Aa * amp * vs[2], bob * vs[3], lean * vs[4]
            s = dict(lu_L=A * sn, lu_R=-A * sn, ll_L=K * max(0, cs), ll_R=K * max(0, -cs),
                     au_L=-Aa * sn, au_R=Aa * sn, al_L=bend, al_R=bend,
                     torso=lean + 1.5 * cs, head=-1.5 * cs, dy=-bob * abs(cs if anim == "walk" else sn))
            if vs[5]:
                s["dx"] = vs[5] * sn
    elif anim == "attack":
        t = i / max(n - 1, 1)
        base = dict(wu=10, wl=40, ou=-5, ol=15)
        K = lambda tt, **kw: (tt, {**base, **kw})
        keys = [K(0), K(.25, torso=-8, head=-4, wu=135, wl=35, ou=-25, ol=20, dx=-.04, legF=5, legB=-10),
                K(.42, torso=14, head=6, wu=15, wl=10, ou=10, ol=25, dx=.06, legF=25, kF=25, legB=-25, kB=10),
                K(.60, torso=18, head=8, wu=-5, wl=5, ou=10, ol=25, dx=.07, legF=25, kF=25, legB=-28, kB=10), K(1.0)]
        k = _kf(keys, t)
        s = dict(k)
        s["__attack"] = weapon
    elif anim == "jump":
        t = i / max(n - 1, 1)
        keys = [(0, {}), (.2, dict(dy=.06, torso=10, th=28, kn=55, au=-25, al=20)),
                (.4, dict(dy=-.08, torso=-4, th=10, kn=30, au=120, al=15)),
                (.55, dict(dy=-.2, th=20, kn=60, au=140, al=10)), (.7, dict(dy=-.1, th=5, kn=20, au=80)),
                (.85, dict(dy=.05, torso=8, th=25, kn=50, au=-15, al=20)), (1, {})]
        k = _kf(keys, t)
        s = dict(dy=k.get("dy", 0), torso=k.get("torso", 0), lu_L=k.get("th", 0), lu_R=k.get("th", 0),
                 ll_L=k.get("kn", 0), ll_R=k.get("kn", 0), au_L=k.get("au", 0), au_R=k.get("au", 0),
                 al_L=k.get("al", 0), al_R=k.get("al", 0))
    elif anim == "hurt":
        t = i / max(n - 1, 1)
        keys = [(0, {}),
                (.2, dict(torso=-14, head=-10, dx=-.05, dy=.012, au_L=-30, au_R=-35, al_L=25, al_R=20, lu_L=10, lu_R=-8, ll_L=10, ll_R=8)),
                (.5, dict(torso=-8, head=-6, dx=-.04, au_L=-15, au_R=-20, al_L=20, al_R=18, lu_L=6, lu_R=-5, ll_L=6, ll_R=5)),
                (1, {})]
        s = dict(_kf(keys, t))
    elif anim == "death":
        t = i / max(n - 1, 1)
        legs = lambda lu, ll: dict(lu_L=lu, lu_R=lu * .75, ll_L=ll, ll_R=ll * .9)
        keys = [(0, {}),
                (.12, dict(torso=-12, head=-8, dx=-.03, au_L=-40, au_R=-40, al_L=25, al_R=25)),
                (.35, dict(rot=-25, dy=.07, torso=-8, au_L=-50, au_R=-60, al_L=30, al_R=30, **legs(30, 60))),
                (.65, dict(rot=-70, dy=.04, torso=-5, au_L=-70, au_R=-80, al_L=20, al_R=20, **legs(15, 35))),
                (.85, dict(rot=-86, torso=0, au_L=-60, au_R=-75, al_L=10, al_R=10, **legs(5, 10))),
                (1, dict(rot=-90, au_L=-60, au_R=-75, al_L=10, al_R=10, **legs(4, 8)))]
        s = dict(_kf(keys, t))
    elif anim == "cast":
        t = i / max(n - 1, 1)
        base = dict(wu=8, wl=25, ou=-3, ol=15, legF=8, legB=-8)
        K = lambda tt, **kw: (tt, {**base, **kw})
        keys = [K(0), K(.3, torso=-6, head=-5, wu=160, wl=20, ou=140, ol=25, dy=-.015),
                K(.55, torso=10, head=4, wu=85, wl=5, ou=80, ol=10, dx=.03),
                K(.75, torso=10, head=4, wu=85, wl=5, ou=80, ol=10, dx=.03), K(1)]
        s = dict(_kf(keys, t))
        s["__attack"] = weapon
    elif anim == "block":
        t = i / max(n - 1, 1)
        base = dict(wu=10, wl=40, ou=-5, ol=15)
        K = lambda tt, **kw: (tt, {**base, **kw})
        guard = dict(torso=8, head=3, wu=60, wl=70, ou=40, ol=80, dy=.025, legF=20, kF=25, legB=-15, kB=30)
        keys = [K(0), K(.3, **guard), K(.7, **{**guard, "dy": .03, "torso": 10}), K(1)]
        s = dict(_kf(keys, t))
        s["__attack"] = weapon
    elif anim == "cheer":
        ph = 2 * math.pi * i / n
        sn = math.sin(ph)
        land = 1 - abs(sn)
        s = dict(au_L=150 + 15 * sn, au_R=150 - 15 * sn, al_L=15, al_R=15, dy=-.04 * abs(sn), torso=-2,
                 ll_L=15 * land, ll_R=15 * land, lu_L=6 * land, lu_R=6 * land)
    elif anim == "climb":
        ph = 2 * math.pi * i / n
        sn, cs = math.sin(ph), math.cos(ph)
        s = dict(au_L=120 + 30 * sn, au_R=120 - 30 * sn, al_L=25, al_R=25,
                 lu_L=40 * max(0, sn), ll_L=75 * max(0, sn), lu_R=40 * max(0, -sn), ll_R=75 * max(0, -sn),
                 torso=4, head=-5, dy=-.02 * abs(cs))
    return s


def _angles(sem, F, facing_front_side):
    """semantic -> bone angles in degrees (clockwise-positive on screen). F=-1 faces right, +1 faces left."""
    g = lambda k: sem.get(k, 0)
    if "__attack" in sem:  # map weapon/other arm and front/back leg onto screen sides
        w, o = sem["__attack"], ("l" if sem["__attack"] == "r" else "r")
        fs, bs = facing_front_side, ("l" if facing_front_side == "r" else "r")
        m = {f"au_{w.upper()}": g("wu"), f"al_{w.upper()}": g("wl"), f"au_{o.upper()}": g("ou"), f"al_{o.upper()}": g("ol"),
             f"lu_{fs.upper()}": g("legF"), f"ll_{fs.upper()}": g("kF"), f"lu_{bs.upper()}": g("legB"), f"ll_{bs.upper()}": g("kB"),
             "torso": g("torso"), "head": g("head"), "dx": g("dx"), "dy": g("dy"), "rot": g("rot")}
        sem = m
        g = lambda k: sem.get(k, 0)
    a = {"torso": -F * g("torso"), "head": -F * g("head")}
    for side in ("l", "r"):
        S = side.upper()
        a[f"{side}_arm_u"], a[f"{side}_arm_l"] = F * g(f"au_{S}"), F * g(f"al_{S}")
        a[f"{side}_leg_u"], a[f"{side}_leg_l"] = F * g(f"lu_{S}"), -F * g(f"ll_{S}")
    return a, g("dx"), g("dy"), g("rot")


def z_order(near):
    if near == "both":
        return ["l_leg_u", "l_leg_l", "r_leg_u", "r_leg_l", "torso", "head", "l_arm_u", "l_arm_l", "r_arm_u", "r_arm_l"]
    far = "r" if near == "l" else "l"
    return [f"{far}_arm_u", f"{far}_arm_l", f"{far}_leg_u", f"{far}_leg_l", "torso", "head",
            f"{near}_leg_u", f"{near}_leg_l", f"{near}_arm_u", f"{near}_arm_l"]


def _rot(px_, py_, deg):
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return np.array([[c, -s, px_ - c * px_ + s * py_], [s, c, py_ - s * px_ - c * py_], [0, 0, 1]])


def _prep_secondary(lab, joints, sec):
    """For every painted part: attach point (painted pixels nearest the body anchor), tip, axis, and per-pixel chain segment."""
    out, H, W = [], *lab.shape
    cfgs = (sec or {}).get("parts") or {}
    for k, (name, parent) in enumerate(SEC_PARTS):
        m = lab == len(BONES) + k
        if m.sum() < 6:
            continue
        d, cfg = SEC_DEFAULTS[name], cfgs.get(name, {})
        ys, xs = np.nonzero(m)
        P = np.stack([xs + .5, ys + .5], 1).astype(np.float64)
        nj = np.array(joints["neck"], float)
        anchor = {"cape": nj, "hair": (nj + np.array(joints["head"], float)) / 2, "tail": np.array(joints["pelvis"], float)}[name]
        kk = max(3, int(np.ceil(.12 * len(P))))
        A = P[np.argsort(np.linalg.norm(P - anchor, axis=1))[:kk]].mean(0)
        T = P[np.argsort(-np.linalg.norm(P - A, axis=1))[:kk]].mean(0)
        L = float(np.linalg.norm(T - A))
        if L < 2:
            continue
        u = (T - A) / L
        nseg = max(1, min(int(np.clip(cfg.get("segments", d["segments"]), 1, 6)), int(L // 2) or 1))
        si = np.clip(np.floor(((P - A) @ u) / L * nseg), 0, nseg - 1).astype(np.int32)
        seg = np.full((H, W), -1, np.int32)
        seg[ys, xs] = si
        out.append(dict(name=name, parent=parent, A=A, u=u, L=L, nseg=nseg, seg=seg, mask=m,
                        pivots=[A + u * L * (i / nseg) for i in range(nseg)], front=bool(cfg.get("front", False)),
                        omega=d["omega"], grav=d["grav"], gain=d["gain"]))
    return out


def _simulate(pt, psi, pa, anim, cyclic, F, H0, sec, cycles=None):
    """Spring chain: every segment is pulled toward its parent's world angle (and a little toward hanging straight), pushed
    opposite to the attach point's velocity, and blown backwards by 'wind' while running. Looping clips are simulated for
    several cycles first so the recorded cycle loops seamlessly. Returns relative angles (frames, segments) in degrees."""
    n, nseg = len(psi), pt["nseg"]
    if n < 2:
        return np.zeros((n, nseg))
    flutter, stiff, zeta = float(sec.get("flutter", 1)), float(sec.get("stiffness", 1)), float(sec.get("damping", .35))
    sc = H0 / 64.0
    vel = np.array([(pa[i] - (pa[i - 1] if (i > 0 or cyclic) else pa[0])) / sc for i in range(n)])
    wind = np.array([-F * WIND_SPEED.get(anim, 0.0) * flutter, 0.0])
    breeze = BREEZE.get(anim, 2.0 if cyclic else 0.0) * flutter
    omega, grav, gain = pt["omega"] * stiff, pt["grav"], pt["gain"] * flutter
    u0, sub = pt["u"], 10
    dt = 1.0 / sub
    cycles = cycles if cycles is not None else (10 if cyclic else 1)
    phi, w = np.full(nseg, float(psi[0])), np.zeros(nseg)
    rec = np.zeros((n, nseg))
    for step in range(cycles * n * sub):
        tc = step * dt
        fi = int(tc) % n if cyclic else min(int(tc), n - 1)
        i1 = (fi + 1) % n if cyclic else min(fi + 1, n - 1)
        fr = tc - int(tc)
        psi_t = psi[fi] + (psi[i1] - psi[fi]) * fr
        v = vel[fi] + (vel[i1] - vel[fi]) * fr + wind
        if step % sub == 0 and step >= (cycles - 1) * n * sub:
            rec[(step // sub) - (cycles - 1) * n] = phi
        for i in range(nseg):
            parent = psi_t if i == 0 else phi[i - 1]
            c, s = math.cos(math.radians(phi[i])), math.sin(math.radians(phi[i]))
            ux, uy = c * u0[0] - s * u0[1], s * u0[0] + c * u0[1]
            off = float(np.clip(gain * (1 + .3 * i) * (v[0] * uy - v[1] * ux), -50, 50))
            target = (1 - grav) * parent + off + breeze * math.sin(2 * math.pi * tc / n - .8 * i)
            om = omega * (1 - .1 * i)
            w[i] += (-om * om * (phi[i] - target) - 2 * zeta * om * w[i]) * dt
            phi[i] += w[i] * dt
            if abs(phi[i] - parent) > 75:
                phi[i] = parent + math.copysign(75, phi[i] - parent)
                w[i] *= .5
    rel = rec.copy()
    rel[:, 0] -= psi
    rel[:, 1:] -= rec[:, :-1]
    return rel


def custom_keys(keys):
    """Validate a normalized timeline of target joint positions."""
    if not isinstance(keys, list) or not 2 <= len(keys) <= 16:
        raise ValueError("Custom clip needs 2-16 keyframes")
    out = []
    for k in keys:
        try:
            t = float(k["t"])
            j = {name: [float(v) for v in k["joints"][name]] for name in JOINTS}
        except (KeyError, TypeError, ValueError):
            raise ValueError("Invalid keyframe joints or time")
        if not math.isfinite(t) or not 0 <= t <= 1 or any(len(v) != 2 or not all(math.isfinite(x) and -4096 <= x <= 4096 for x in v) for v in j.values()):
            raise ValueError("Invalid keyframe coordinates")
        out.append((t, j))
    out.sort(key=lambda k: k[0])
    if out[0][0] != 0 or out[-1][0] != 1 or any(a[0] >= b[0] for a,b in zip(out,out[1:])):
        raise ValueError("Keyframes need unique times including 0 and 1")
    return out


def _custom_pose(keys, t, rest, pad, ss):
    """Ease target joints; retain source bone lengths and artwork."""
    target = keys[-1][1]
    for (a, ja), (b, jb) in zip(keys, keys[1:]):
        if t <= b:
            u = _ease(max(0, min(1, (t-a)/(b-a))))
            target = {n: (1-u)*np.array(ja[n])+u*np.array(jb[n]) for n in JOINTS}
            break
    mats = {}
    for name, a, b, _, _, _ in BONES:
        A, B = np.array(rest[a]), np.array(rest[b])
        C, D = np.array(target[a]), np.array(target[b])
        v, w = B-A, D-C
        angle = math.degrees(math.atan2(w[1],w[0])-math.atan2(v[1],v[0])) if np.linalg.norm(v)>1e-6 and np.linalg.norm(w)>1e-6 else 0
        R = _rot((A[0]+pad)*ss,(A[1]+pad)*ss,angle)
        R[:2,2] += (C-A)*ss
        mats[name] = R
    return np.eye(3), mats


def render(sprite, joints, overrides, anim="walk", frames=8, facing="right", near="r", weapon="r", amp=1.0,
           pad=0, overlap=1, ss=4, secondary=None, view="side", keyframes=None, softness=0):
    sprite = sprite.convert("RGBA")
    W0, H0 = sprite.size
    hd = is_hd(sprite)
    softness = float(softness)
    if not math.isfinite(softness) or not 0 <= softness <= 100:
        raise ValueError("Joint softness must be 0-100")
    keys_custom = custom_keys(keyframes) if anim == "custom" else None
    if hd:
        if max(W0, H0) > 1024:
            raise ValueError('HD rig source must be at most 1024 px')
        ss = 1  # avoid allocating 16x full-resolution layers
        overlap = min(12, overlap * max(1, round(max(W0, H0) / 128)))
    pad = pad if pad > 0 else int(round(CLIP_PAD.get(anim, .25) * max(W0, H0)))
    if hd and (W0 + 2 * pad) * (H0 + 2 * pad) * max(1, frames) > 48_000_000:
        raise ValueError('HD clip exceeds pixel budget; reduce frames, source size or padding')
    lab = assign_parts(sprite, joints, overrides)
    arr = np.asarray(sprite).copy()
    if not hd:
        arr[arr[..., 3] < 128] = 0
        arr[..., 3] = np.where(arr[..., 3] >= 128, 255, 0)
    opaque = arr[..., 3] > 0
    use_sec = bool(secondary) and secondary.get("enabled", True)
    parts = _prep_secondary(lab, joints, secondary) if use_sec else []
    active = {SEC_LABEL[pt["name"]] for pt in parts}
    for name, parent in SEC_PARTS:  # painted but not simulated (switch off, too small...): stays attached to the body, never disappears
        lbl = SEC_LABEL[name]
        if lbl not in active and (lab == lbl).any():
            lab[lab == lbl] = BONE_IDX[parent or "torso"]
    secmask = np.isin(lab, list(active)) if active else np.zeros(lab.shape, bool)
    CW, CH = W0 + 2 * pad, H0 + 2 * pad
    gy, gx = np.mgrid[0:H0, 0:W0]
    rad = max(3.0, .1 * H0) + overlap

    def layer(m):
        l = np.zeros((CH, CW, 4), np.uint8)
        l[pad:pad + H0, pad:pad + W0][m] = arr[m]
        return Image.fromarray(l, "RGBA") if hd else Image.fromarray(l, "RGBA").resize((CW * ss, CH * ss), Image.NEAREST)

    layers, masks, meshes, mesh_children = {}, {}, {}, set()
    for i in range(len(BONES)):
        m = lab == i
        if overlap > 0 and m.any():  # overlap only near the bone's pivot, where rotation opens gaps
            jx, jy = joints[BONES[i][1]]
            near_pivot = (gx + .5 - jx) ** 2 + (gy + .5 - jy) ** 2 <= rad ** 2
            m = m | (ndi.binary_dilation(m, iterations=overlap) & opaque & ~secmask & near_pivot)
        masks[i] = m
    if softness:
        if CW * CH * ss * ss > 16_000_000:
            raise ValueError("Soft mesh canvas exceeds memory budget; reduce padding or size")
        radius = max(1., max(W0,H0)*.14*softness/100)
        for side in ("l","r"):
            for limb in ("arm","leg"):
                a,b = (BONE_IDX[f"{side}_{limb}_{part}"] for part in ("u","l"))
                mesh = softmesh.prepare(arr,lab==a,lab==b,masks[a]|masks[b],radius,hd)
                if mesh is not None:
                    meshes[("b",a)] = (("b",b),mesh)
                    mesh_children.add(("b",b))
    for i,m in masks.items():
        key = ("b",i)
        if key not in meshes and key not in mesh_children:
            layers[key] = layer(m)
    for pt in parts:
        for i in range(pt["nseg"]):
            m = pt["seg"] == i
            if overlap > 0 and m.any():  # cloth stays continuous where segments bend
                px_, py_ = pt["pivots"][i]
                m = m | (ndi.binary_dilation(m, iterations=overlap) & pt["mask"] & ((gx + .5 - px_) ** 2 + (gy + .5 - py_) ** 2 <= rad ** 2))
            layers[("s", pt["name"], i)] = layer(m)
    piv = {n: (joints[n][0] + pad) * ss for n in JOINTS}, {n: (joints[n][1] + pad) * ss for n in JOINTS}
    cols = np.unique(arr[opaque][:, :3], axis=0) if not hd and opaque.any() else np.zeros((0, 3), np.uint8)  # palette for crisp 'mode' downsampling
    use_pal = 0 < len(cols) <= 64
    keys = ((cols[:, 0].astype(np.int64) << 16) | (cols[:, 1].astype(np.int64) << 8) | cols[:, 2].astype(np.int64)) if use_pal else None
    F = -1 if facing == "right" else 1
    feet = ((piv[0]["l_ankle"] + piv[0]["r_ankle"]) / 2, max(piv[1]["l_ankle"], piv[1]["r_ankle"]))
    body_keys = [("b", BONE_IDX[nm]) for nm in z_order(near)]
    sec_keys = lambda front: [("s", pt["name"], i) for pt in parts if pt["front"] == front for i in range(pt["nseg"])]
    order = sec_keys(False) + body_keys + sec_keys(True)  # cape / hair / tail behind the body unless set to "in front"
    n = max(1, frames)
    pivot_bone = {b[1]: b[0] for b in BONES}
    poses = []  # pass 1: body pose of every frame
    for fi in range(n):
        if keys_custom is not None:
            poses.append(_custom_pose(keys_custom, fi/max(1,n-1), joints, pad, ss))
            continue
        sem = _sem(anim, fi, n, amp, weapon, view)
        ang, dx, dy, rot = _angles(sem, F, "r" if facing == "right" else "l")
        T = np.array([[1, 0, dx * H0 * ss], [0, 1, dy * H0 * ss], [0, 0, 1]]) @ _rot(feet[0], feet[1], -F * rot)  # tilt about the feet, then translate
        Wm = {}
        for i, (name, a_, _, parent, _, _) in enumerate(BONES):
            Wm[name] = (Wm[parent] if parent else np.eye(3)) @ _rot(piv[0][a_], piv[1][a_], ang.get(name, 0))
        poses.append((T, Wm))
    rels = {}  # pass 2: secondary chains react to how the parent moved
    for pt in parts:
        base = [T @ (Wm[pt["parent"]] if pt["parent"] else np.eye(3)) for T, Wm in poses]
        A_hi = np.array([(pt["A"][0] + pad) * ss, (pt["A"][1] + pad) * ss, 1.0])
        psi = np.degrees(np.unwrap([math.atan2(M[1, 0], M[0, 0]) for M in base]))
        pa = np.array([(M @ A_hi)[:2] / ss for M in base])
        rels[pt["name"]] = _simulate(pt, psi, pa, anim, anim not in ONE_SHOT, F, H0, secondary)
    out, jframes = [], []
    for fi in range(n):  # pass 3: draw
        T, Wm = poses[fi]
        mats, jp = {}, {}
        for jn, bn in pivot_bone.items():  # where each moving joint ended up this frame (low-res canvas coords)
            v = (T @ Wm[bn]) @ np.array([piv[0][jn], piv[1][jn], 1.0])
            jp[jn] = (float(v[0] / ss), float(v[1] / ss))
        for bi in range(len(BONES)):
            mats[("b", bi)] = T @ Wm[BONE_NAMES[bi]]
        for pt in parts:
            M = T @ (Wm[pt["parent"]] if pt["parent"] else np.eye(3))
            for i in range(pt["nseg"]):
                p_hi = np.array([(pt["pivots"][i][0] + pad) * ss, (pt["pivots"][i][1] + pad) * ss, 1.0])
                M = M @ _rot(p_hi[0], p_hi[1], rels[pt["name"]][fi, i])
                mats[("s", pt["name"], i)] = M
                v = M @ p_hi
                jp[f"{pt['name']}_{i}"] = (float(v[0] / ss), float(v[1] / ss))  # lets AI cleanup treat cloth joints too
        jframes.append(jp)
        canvas = Image.new("RGBA", (CW * ss, CH * ss), (0, 0, 0, 0))
        for key in order:
            if key in meshes:
                child,mesh = meshes[key]
                tl = softmesh.deform(mesh,mats[key],mats[child],pad,ss,canvas.size,hd)
                canvas = Image.alpha_composite(canvas,tl)
                continue
            if key not in layers:
                continue
            inv = np.linalg.inv(mats[key])
            tl = layers[key].transform(layers[key].size, Image.AFFINE, tuple(inv[:2].flatten()), resample=Image.Resampling.BICUBIC if hd else Image.NEAREST)
            canvas = Image.alpha_composite(canvas, tl)
        out.append(canvas if hd else _downsample(canvas, ss, keys, cols, use_pal))
    ank = ((joints["l_ankle"][0] + joints["r_ankle"][0]) / 2 + pad, max(joints["l_ankle"][1], joints["r_ankle"][1]) + pad)
    return out, {"size": (CW, CH), "pad": pad, "pivot": [round(ank[0], 1), round(ank[1], 1)], "joints": jframes,
                 "secondary": [pt["name"] for pt in parts], "render_mode": "hd" if hd else "pixel", "softness": softness}


def _downsample(img, ss, keys, cols, use_pal):
    a = np.asarray(img)
    Hh, Wh = a.shape[:2]
    H, W = Hh // ss, Wh // ss
    if not use_pal:
        small = img.resize((W, H), Image.BOX)
        s = np.asarray(small).copy()
        s[..., 3] = np.where(s[..., 3] >= 128, 255, 0)
        return Image.fromarray(s, "RGBA")
    alpha = a[..., 3] > 0
    k = (a[..., 0].astype(np.int64) << 16) | (a[..., 1].astype(np.int64) << 8) | a[..., 2].astype(np.int64)
    idx = np.where(alpha, np.searchsorted(keys, k).clip(0, len(keys) - 1), -1)
    blocks = idx.reshape(H, ss, W, ss).transpose(0, 2, 1, 3).reshape(H, W, ss * ss)
    counts = np.stack([(blocks == c).sum(-1) for c in range(len(keys))], -1)
    winner = counts.argmax(-1)
    opaque_cnt = (blocks >= 0).sum(-1)
    out = np.zeros((H, W, 4), np.uint8)
    m = opaque_cnt * 2 >= ss * ss
    out[m, :3] = cols[winner[m]]
    out[m, 3] = 255
    return Image.fromarray(out, "RGBA")


# ---------------- export ----------------
def export(frames, meta, fps, anim, name, root):
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name) or "sprite"
    anim = re.sub(r"[^A-Za-z0-9_-]+", "_", anim) or "anim"
    d = Path(root) / "exports" / f"{safe}_{anim}"
    d.mkdir(parents=True, exist_ok=True)
    w, h = frames[0].size
    if w * len(frames) > 32768 or w * h * len(frames) > 64_000_000:
        raise ValueError('Animation sheet exceeds size budget; use a smaller clip or grid export')
    sheet = Image.new("RGBA", (w * len(frames), h), (0, 0, 0, 0))
    atlas = {"frames": {}, "meta": {"app": "SpriteForge", "image": f"{safe}_{anim}_sheet.png", "format": "RGBA8888",
             "size": {"w": w * len(frames), "h": h}, "scale": "1", "pivot": {"x": meta["pivot"][0], "y": meta["pivot"][1]},
             "loop": anim not in ONE_SHOT,
             "frameTags": [{"name": anim, "from": 0, "to": len(frames) - 1, "direction": "forward"}]}}
    for i, f in enumerate(frames):
        sheet.paste(f, (i * w, 0))
        f.save(d / f"{safe}_{anim}_{i:02d}.png")
        atlas["frames"][f"{safe}_{anim} {i}"] = {"frame": {"x": i * w, "y": 0, "w": w, "h": h}, "rotated": False,
            "trimmed": False, "spriteSourceSize": {"x": 0, "y": 0, "w": w, "h": h}, "sourceSize": {"w": w, "h": h},
            "duration": int(1000 / fps)}
    sheet.save(d / f"{safe}_{anim}_sheet.png")
    (d / f"{safe}_{anim}_atlas.json").write_text(json.dumps(atlas, indent=2))
    g = []
    for im in frames:
        scale = 1 if max(w, h) > 256 else 4
        im = im.resize((w * scale, h * scale), Image.NEAREST)
        p = im.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
        p.paste(255, Image.eval(im.getchannel("A"), lambda v: 255 if v < 128 else 0))
        g.append(p)
    g[0].save(d / f"{safe}_{anim}.gif", save_all=True, append_images=g[1:], duration=int(1000 / fps), loop=0,
              transparency=255, disposal=2)
    return str(d)
