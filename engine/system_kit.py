"""Shared art direction and independently generated UI kit artwork."""
from . import system_assets as S, world_style, world, world_blockout

KITS = {"starter": ("panel", "button", "icon", "slot", "bar_track", "bar_fill"),
        "menu": ("panel", "frame", "button", "tab", "toggle", "slider"),
        "hud": ("frame", "bar_track", "bar_fill", "portrait", "marker", "icon")}
DESCRIPTIONS = {
    "panel": "empty rectangular panel with readable interior",
    "frame": "decorative rectangular frame with transparent center",
    "button": "one empty horizontal button with no label",
    "icon": "one simple ornamental game icon",
    "slot": "one empty square inventory slot",
    "bar_track": "empty horizontal resource bar track",
    "bar_fill": "horizontal resource bar fill, without track",
    "tab": "one empty menu tab", "toggle": "one unlabeled toggle control",
    "slider": "one unlabeled slider control", "portrait": "empty portrait frame",
    "marker": "one game navigation marker"}
STYLES = {"anime": "modern anime game UI, refined linework",
          "hd2d": "HD-2D inspired JRPG UI, ornate readable details",
          "painted": "hand-painted game UI", "pixel": "crisp pixel art game UI", "custom": ""}

def plan(theme, kit):
    d = S.validate(theme)
    if not isinstance(kit, str) or kit not in KITS:
        raise ValueError("Invalid UI kit")
    if not d["prompt"]:
        raise ValueError("Enter a theme prompt")
    roles = KITS[kit]
    if len(d["assets"]) + len(roles) > S.MAX_ASSETS:
        raise ValueError("Not enough artwork slots for kit")
    return d, roles

def prompt(theme, kit, role):
    d, roles = plan(theme, kit)
    if role not in roles:
        raise ValueError("Invalid kit role")
    p = d.get("style_profile")
    guide = world_style.guidance(p).replace("retain natural environment material colors", "retain readable UI material colors")
    parts = [STYLES[d["style"]], d["prompt"], guide,
             "optional palette accents " + ", ".join(d["palette"]) if d["palette"] else "",
             DESCRIPTIONS[role], "one isolated complete game UI asset, front-facing flat view, generous empty margins, consistent upper-left lighting, no lettering, no text, no numbers, no characters, no mockup, no other objects"]
    return ", ".join(x for x in parts if x)

def normalize(raw, bg, tol, pixel):
    return world_blockout.normalize(raw, "rock", bg, tol, pixel)

def assemble(theme, kit, assets):
    d, roles = plan(theme, kit)
    if not isinstance(assets, dict) or set(assets) != set(roles):
        raise ValueError("Missing or unexpected kit artwork")
    if any(not isinstance(v, str) for v in assets.values()) or sum(map(len, assets.values())) > S.MAX_ENCODED:
        raise ValueError("Kit artwork exceeds budget")
    used = {a["id"] for a in d["assets"]}
    for role in roles:
        im = world.image(assets[role])
        if not im.getchannel("A").getbbox() or im.getchannel("A").getextrema()[0] == 255:
            raise ValueError("Expected transparent kit artwork")
        i = 1
        while "kit_" + str(i) in used:
            i += 1
        aid = "kit_" + str(i)
        used.add(aid)
        d["assets"].append(dict(id=aid, role=role, name=role.replace("_", " ").title(), image=assets[role]))
    return S.validate(d)
