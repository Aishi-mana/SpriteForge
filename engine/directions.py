"""4 / 8 direction characters. Only five views are needed (south, south-east, east, north-east, north): west, south-west and
north-west are mirror images of east, south-east and north-east. Every animation is rendered for every direction with a
view-aware walk (front/back = step-and-bob, three-quarter = reduced swing), and exported as one aligned sheet."""
import json
from pathlib import Path
from PIL import ImageOps
from . import exporter, rig

DIRS8 = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]  # clockwise from south
UNIQUE = ["S", "SE", "E", "NE", "N"]
MIRROR = {"SW": "SE", "W": "E", "NW": "NE"}
ORDERS = {"cw8": DIRS8, "cw4": ["S", "W", "N", "E"], "rpg4": ["S", "W", "E", "N"]}  # rpg4 = RPG Maker: down, left, right, up
VIEW = {"S": "front", "N": "front", "E": "side", "SE": "diag", "NE": "diag"}  # which walk/run variant to use
NEAR = {"S": "both", "N": "both", "E": "r", "SE": "r", "NE": "r"}
DUMMY_VIEW = {"S": "front", "N": "back", "E": "side", "SE": "diag", "NE": "diag_back"}
HINT = {"S": "front view, facing the camera", "N": "back view, seen from behind, facing away",
        "E": "side view, facing right", "SE": "three-quarter view, facing right and toward the camera",
        "NE": "three-quarter back view, facing right and away from the camera"}


class DirectionError(ValueError):
    pass


def needed(dirs):
    """The unique views required to produce the requested output directions."""
    seen = []
    for d in dirs:
        if d not in DIRS8:
            raise DirectionError(f"unknown direction: {d}")
        s = MIRROR.get(d, d)
        if s not in seen:
            seen.append(s)
    return [u for u in UNIQUE if u in seen]


def mirror(frames, meta):
    """Left-right flipped copies of the frames, with the feet pivot mirrored too."""
    w = meta["size"][0]
    px, py = meta["pivot"]
    return [ImageOps.mirror(f) for f in frames], {**meta, "pivot": [round(w - px, 1), py]}


def _sec_for(sec, d):
    """From behind, a cape / hair / tail is in front of the body; from every other direction it follows your setting."""
    if not sec:
        return sec
    parts = {k: dict(v) for k, v in (sec.get("parts") or {}).items()}
    for name in ("cape", "hair", "tail"):
        p = parts.setdefault(name, {})
        p["front"] = (d == "N") or bool(p.get("front", False))
    return {**sec, "parts": parts}


def render_directions(slots, clips, dirs, secondary=None, ss=4):
    """slots: {dir: {"sprite": PIL, "joints": {...}, "ovr": [[x, y, bone]...]}} for the needed unique views.
    clips: [{"anim", "count", "fps", "amp", "pad", "overlap", "weapon"}]. Returns {(anim, dir): (frames, meta)}."""
    for u in needed(dirs):
        if u not in slots or slots[u].get("sprite") is None:
            raise DirectionError(f"the {u} view has no sprite yet")
    if any(rig.is_hd(slots[u]["sprite"]) for u in needed(dirs)):
        pixels=0
        for c in clips:
            for direction in dirs:
                im=slots[MIRROR.get(direction,direction)]["sprite"]
                pad=c.get("pad",0) or round(rig.CLIP_PAD.get(c["anim"],.25)*max(im.size))
                pixels+=(im.width+2*pad)*(im.height+2*pad)*c["count"]
        if pixels>48_000_000: raise DirectionError("HD direction set exceeds memory budget; reduce clips, frames or directions")
    out, cache = {}, {}
    for c in clips:
        for d in dirs:
            src = MIRROR.get(d, d)
            key = (c["anim"], src)
            if key not in cache:
                s = slots[src]
                cache[key] = rig.render(s["sprite"], s["joints"], s.get("ovr") or [], c["anim"], c["count"], "right", NEAR[src],
                                        c.get("weapon", "r"), c.get("amp", 1.0), c.get("pad", 0), c.get("overlap", 1), ss,
                                        secondary=_sec_for(secondary, src), view=VIEW[src], softness=c.get("softness",0))
            frames, meta = cache[key]
            out[(c["anim"], d)] = mirror(frames, meta) if d in MIRROR else (frames, meta)
    return out


def export_directions(slots, clips, dirs, order, options, name, secondary, root):
    """One animation per (clip, direction), named like walk_s / walk_sw ..., laid out one row each, in `order`."""
    rows = [d for d in ORDERS.get(order, DIRS8) if d in dirs] or list(dirs)
    res = render_directions(slots, clips, rows, secondary)
    entries = []
    for c in clips:
        for d in rows:
            frames, meta = res[(c["anim"], d)]
            entries.append({"name": f"{c['anim']}_{d.lower()}", "fps": c["fps"], "loop": c["anim"] not in rig.ONE_SHOT,
                            "frames": frames, "pivot": tuple(meta["pivot"])})
    out = exporter.export_pack(entries, dict(options,smooth=any(rig.is_hd(s["sprite"]) for s in slots.values())), name, root)
    (Path(out["dir"]) / "directions.json").write_text(json.dumps({
        "directions": rows, "clips": [c["anim"] for c in clips], "animations": [e["name"] for e in entries],
        "mirrored": {k: v for k, v in MIRROR.items() if k in rows},
        "note": "animation names are <clip>_<direction>; directions are compass points seen from above (S = facing the camera)"}, indent=2))
    out["directions"] = rows
    out["animations"] = len(entries)
    return out
