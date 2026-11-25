"""Export animation packs: one sprite sheet + atlas for any number of clips, with engine-ready files.
Every frame shares a feet-anchored pivot, so clips line up in the engine without per-clip offsets."""
import json, math, re
from pathlib import Path
import numpy as np
from PIL import Image


def _safe(s, default="sprite"):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", str(s)).strip("_")[:60] or default


def _pot(n):
    p = 1
    while p < n:
        p *= 2
    return p


def _floor_half(x):
    return int(math.floor(x + 0.5))  # deterministic rounding (Python's round() is banker's rounding)


def _align_and_crop(group, crop):
    """group: entries sharing one cell size. Pads every frame onto one canvas around the feet pivot, then crops to the
    union of visible pixels (optional). Mutates entries: frames, pivot."""
    for e in group:
        e["pv"] = (_floor_half(e["pivot"][0]), _floor_half(e["pivot"][1]))
    L = max(e["pv"][0] for e in group)
    U = max(e["pv"][1] for e in group)
    R = max(e["frames"][0].width - e["pv"][0] for e in group)
    D = max(e["frames"][0].height - e["pv"][1] for e in group)
    for e in group:
        out = []
        for f in e["frames"]:
            c = Image.new("RGBA", (L + R, U + D), (0, 0, 0, 0))
            c.paste(f, (L - e["pv"][0], U - e["pv"][1]))
            out.append(c)
        e["frames"], e["pivot"] = out, (L, U)
    if crop:
        x0 = y0 = 10 ** 9
        x1 = y1 = -1
        for e in group:
            for f in e["frames"]:
                bb = f.getchannel("A").getbbox()
                if bb:
                    x0, y0, x1, y1 = min(x0, bb[0]), min(y0, bb[1]), max(x1, bb[2]), max(y1, bb[3])
        if x1 > 0:
            W, H = L + R, U + D
            # keep the pivot inside the box so it stays a valid feet anchor
            x0, y0 = max(0, min(x0 - 1, L)), max(0, min(y0 - 1, U))
            x1, y1 = min(W, max(x1 + 1, L + 1)), min(H, max(y1 + 1, U + 1))
            for e in group:
                e["frames"] = [f.crop((x0, y0, x1, y1)) for f in e["frames"]]
                e["pivot"] = (L - x0, U - y0)


def _plan(entries, o):
    pad = o["padding"]
    pos, W, H = [], 0, 0
    items = [(ai, fi, im) for ai, e in enumerate(entries) for fi, im in enumerate(e["frames"])]
    if o["layout"] == "rows":
        y = 0
        for ai, e in enumerate(entries):
            x, rh = 0, max(im.height for im in e["frames"])
            for fi, im in enumerate(e["frames"]):
                pos.append((ai, fi, x, y))
                x += im.width + pad
            W, y = max(W, x - pad), y + rh + pad
        H = y - pad
    elif o["layout"] == "column":
        W, y = max(im.width for _, _, im in items), 0
        for ai, fi, im in items:
            pos.append((ai, fi, 0, y))
            y += im.height + pad
        H = y - pad
    else:  # grid
        sw, sh = max(im.width for _, _, im in items), max(im.height for _, _, im in items)
        cols = max(1, min(o["columns"], len(items)))
        for k, (ai, fi, _) in enumerate(items):
            r, c = divmod(k, cols)
            pos.append((ai, fi, c * (sw + pad), r * (sh + pad)))
        W, H = cols * (sw + pad) - pad, math.ceil(len(items) / cols) * (sh + pad) - pad
    if o["pot"]:
        W, H = _pot(W), _pot(H)
    return pos, W, H


def _gif(frames, fps, path, scale=4):
    g = []
    for im in frames:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        p = im.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
        p.paste(255, Image.eval(im.getchannel("A"), lambda v: 255 if v < 128 else 0))
        g.append(p)
    g[0].save(path, save_all=True, append_images=g[1:], duration=int(1000 / fps), loop=0, transparency=255, disposal=2)


def _godot_path(p):
    p = re.sub(r"[^A-Za-z0-9_./:-]", "", p or "")
    if not p.startswith("res://"):
        p = "res://" + p.lstrip("/")
    return p if p.endswith("/") else p + "/"


def _godot(name, sheet_name, entries, regions, gpath, cell_pivot):
    subs, anims = [], []
    for ai, e in enumerate(entries):
        frames = []
        for fi in range(len(e["frames"])):
            x, y, w, h = regions[(ai, fi)]
            sid = f"AtlasTexture_{e['name']}_{fi}"
            subs.append(f'[sub_resource type="AtlasTexture" id="{sid}"]\natlas = ExtResource("1_sheet")\n'
                        f'region = Rect2({x}, {y}, {w}, {h})\nfilter_clip = true\n')
            frames.append('{\n"duration": 1.0,\n"texture": SubResource("%s")\n}' % sid)
        anims.append('{\n"frames": [%s],\n"loop": %s,\n"name": &"%s",\n"speed": %s\n}'
                     % (", ".join(frames), "true" if e["loop"] else "false", e["name"], float(e["fps"])))
    head = f'[gd_resource type="SpriteFrames" load_steps={len(subs) + 2} format=3]\n\n'
    head += f'[ext_resource type="Texture2D" path="{gpath}{sheet_name}" id="1_sheet"]\n\n'
    tres = head + "\n".join(subs) + "\n[resource]\nanimations = [" + ", ".join(anims) + "]\n"
    first = entries[0]["name"]
    px, py = cell_pivot
    tscn = (f'[gd_scene load_steps=2 format=3]\n\n[ext_resource type="SpriteFrames" path="{gpath}{name}.tres" id="1_frames"]\n\n'
            f'[node name="{name}" type="AnimatedSprite2D"]\ntexture_filter = 1\ncentered = false\n'
            f'offset = Vector2({-px}, {-py})\nsprite_frames = ExtResource("1_frames")\nanimation = &"{first}"\nautoplay = "{first}"\n')
    return tres, tscn


UNITY_CS = '''// SpriteForge importer. Select the *_unity.json file in the Project window, then
// Assets > SpriteForge > Import Sprite Sheet. It slices the sheet and creates one AnimationClip per animation.
#if UNITY_EDITOR
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

public static class SpriteForgeImporter
{
    [System.Serializable] class Frame { public string name; public int x, y, w, h; }
    [System.Serializable] class Anim { public string name; public int fps; public bool loop; public List<Frame> frames; }
    [System.Serializable] class Data { public string image; public int width, height; public float pivotX, pivotY; public int ppu; public List<Anim> animations; }

    [MenuItem("Assets/SpriteForge/Import Sprite Sheet", true)]
    static bool Validate()
    {
        var o = Selection.activeObject as TextAsset;
        return o != null && AssetDatabase.GetAssetPath(o).EndsWith("_unity.json");
    }

    [MenuItem("Assets/SpriteForge/Import Sprite Sheet")]
    static void Import()
    {
        var jsonPath = AssetDatabase.GetAssetPath(Selection.activeObject);
        var dir = Path.GetDirectoryName(jsonPath).Replace('\\\\', '/');
        var data = JsonUtility.FromJson<Data>(File.ReadAllText(jsonPath));
        var texPath = dir + "/" + data.image;
        var imp = AssetImporter.GetAtPath(texPath) as TextureImporter;
        if (imp == null) { Debug.LogError("SpriteForge: texture not found next to the JSON: " + texPath); return; }

        imp.textureType = TextureImporterType.Sprite;
        imp.spriteImportMode = SpriteImportMode.Multiple;
        imp.spritePixelsPerUnit = data.ppu;
        imp.filterMode = FilterMode.Point;
        imp.mipmapEnabled = false;
        imp.textureCompression = TextureImporterCompression.Uncompressed;

        var metas = new List<SpriteMetaData>();
        foreach (var a in data.animations)
            foreach (var f in a.frames)
                metas.Add(new SpriteMetaData {
                    name = f.name, rect = new Rect(f.x, f.y, f.w, f.h),
                    alignment = (int)SpriteAlignment.Custom, pivot = new Vector2(data.pivotX, data.pivotY) });
#pragma warning disable 618
        imp.spritesheet = metas.ToArray();
#pragma warning restore 618
        EditorUtility.SetDirty(imp);
        imp.SaveAndReimport();

        var sprites = new Dictionary<string, Sprite>();
        foreach (var o in AssetDatabase.LoadAllAssetRepresentationsAtPath(texPath))
        {
            var s = o as Sprite;
            if (s != null) sprites[s.name] = s;
        }

        foreach (var a in data.animations)
        {
            var clip = new AnimationClip { frameRate = a.fps };
            var binding = EditorCurveBinding.PPtrCurve("", typeof(SpriteRenderer), "m_Sprite");
            var keys = new ObjectReferenceKeyframe[a.frames.Count + 1];
            for (int i = 0; i < a.frames.Count; i++)
                keys[i] = new ObjectReferenceKeyframe { time = i / (float)a.fps, value = sprites[a.frames[i].name] };
            keys[a.frames.Count] = new ObjectReferenceKeyframe { time = a.frames.Count / (float)a.fps, value = sprites[a.frames[a.frames.Count - 1].name] };
            AnimationUtility.SetObjectReferenceCurve(clip, binding, keys);
            var settings = AnimationUtility.GetAnimationClipSettings(clip);
            settings.loopTime = a.loop;
            AnimationUtility.SetAnimationClipSettings(clip, settings);
            var clipPath = dir + "/" + a.name + ".anim";
            AssetDatabase.DeleteAsset(clipPath);
            AssetDatabase.CreateAsset(clip, clipPath);
        }
        AssetDatabase.SaveAssets();
        Debug.Log("SpriteForge: imported " + metas.Count + " sprites and " + data.animations.Count + " clips from " + jsonPath);
    }
}
#endif
'''


def export_pack(entries, opts, name, root):
    """entries: [{name, fps, loop, frames:[RGBA PIL], pivot:(x,y)}]. opts keys: layout, columns, padding, pot, crop, uniform,
    godot, godot_path, unity, ppu, gif, frames."""
    o = {"layout": "rows", "columns": 8, "padding": 0, "pot": False, "crop": True, "uniform": True, "godot": True,
         "godot_path": "res://sprites/", "unity": True, "ppu": 32, "gif": True, "frames": False}
    o.update({k: v for k, v in (opts or {}).items() if k in o})
    o["layout"] = o["layout"] if o["layout"] in ("rows", "grid", "column") else "rows"
    o["padding"] = max(0, min(int(o["padding"]), 16))
    o["columns"] = max(1, min(int(o["columns"]), 64))
    name = _safe(name)
    entries = [dict(e, name=_safe(e["name"], "anim"), frames=list(e["frames"])) for e in entries]
    if o["uniform"]:
        _align_and_crop(entries, o["crop"])
    else:
        for e in entries:
            _align_and_crop([e], o["crop"])
    pos, W, H = _plan(entries, o)
    d = Path(root) / "exports" / (f"{name}_pack" if len(entries) > 1 else f"{name}_{entries[0]['name']}")
    d.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    regions, gi_of = {}, {}
    for gi, (ai, fi, x, y) in enumerate(pos):
        im = entries[ai]["frames"][fi]
        sheet.paste(im, (x, y))
        regions[(ai, fi)] = (x, y, im.width, im.height)
        gi_of[(ai, fi)] = gi
    sheet_name = f"{name}_sheet.png"
    sheet.save(d / sheet_name)
    files = [sheet_name]
    # ---- Aseprite / Phaser compatible JSON (hash) ----
    atlas = {"frames": {}, "meta": {"app": "SpriteForge", "image": sheet_name, "format": "RGBA8888", "scale": "1",
             "size": {"w": W, "h": H}, "frameTags": []}}
    for ai, e in enumerate(entries):
        px, py = e["pivot"]
        for fi, im in enumerate(e["frames"]):
            x, y, w, h = regions[(ai, fi)]
            atlas["frames"][f"{name}_{e['name']} {fi}"] = {
                "frame": {"x": x, "y": y, "w": w, "h": h}, "rotated": False, "trimmed": False,
                "spriteSourceSize": {"x": 0, "y": 0, "w": w, "h": h}, "sourceSize": {"w": w, "h": h},
                "pivot": {"x": round(px / w, 4), "y": round(py / h, 4)}, "pivotPx": {"x": px, "y": py},
                "duration": int(1000 / e["fps"])}
        n = len(e["frames"])
        atlas["meta"]["frameTags"].append({"name": e["name"], "from": gi_of[(ai, 0)], "to": gi_of[(ai, n - 1)],
                                           "direction": "forward", "loop": bool(e["loop"]), "fps": e["fps"]})
    atlas["meta"]["pivot"] = {"x": entries[0]["pivot"][0], "y": entries[0]["pivot"][1]}
    (d / f"{name}_atlas.json").write_text(json.dumps(atlas, indent=2))
    files.append(f"{name}_atlas.json")
    # ---- Godot 4 ----
    if o["godot"]:
        gp = _godot_path(o["godot_path"])
        tres, tscn = _godot(name, sheet_name, entries, regions, gp, entries[0]["pivot"])
        (d / f"{name}.tres").write_text(tres)
        (d / f"{name}.tscn").write_text(tscn)
        files += [f"{name}.tres", f"{name}.tscn"]
    # ---- Unity ----
    if o["unity"]:
        anims = []
        for ai, e in enumerate(entries):
            fr = []
            for fi in range(len(e["frames"])):
                x, y, w, h = regions[(ai, fi)]
                fr.append({"name": f"{e['name']}_{fi}", "x": x, "y": H - y - h, "w": w, "h": h})  # Unity's Y starts at the bottom
            anims.append({"name": e["name"], "fps": e["fps"], "loop": bool(e["loop"]), "frames": fr})
        px, py = entries[0]["pivot"]
        cw, ch = entries[0]["frames"][0].size
        u = {"image": sheet_name, "width": W, "height": H, "pivotX": round(px / cw, 5), "pivotY": round((ch - py) / ch, 5),
             "ppu": int(o["ppu"]), "animations": anims}
        (d / f"{name}_unity.json").write_text(json.dumps(u, indent=2))
        (d / "SpriteForgeImporter.cs").write_text(UNITY_CS)
        files += [f"{name}_unity.json", "SpriteForgeImporter.cs"]
    # ---- previews / frames ----
    for e in entries:
        if o["gif"]:
            _gif(e["frames"], e["fps"], d / f"{name}_{e['name']}.gif")
            files.append(f"{name}_{e['name']}.gif")
        if o["frames"]:
            fd = d / "frames" / e["name"]
            fd.mkdir(parents=True, exist_ok=True)
            for i, f in enumerate(e["frames"]):
                f.save(fd / f"{name}_{e['name']}_{i:02d}.png")
    px, py = entries[0]["pivot"]
    cw, ch = entries[0]["frames"][0].size
    readme = [f"SpriteForge export: {name}", "",
              f"Sheet {W}x{H}px, {len(pos)} frames, cell {cw}x{ch}px, feet pivot at ({px}, {py}) px from the cell's top-left.", ""]
    if o["godot"]:
        readme += ["GODOT 4", f"  Copy {sheet_name}, {name}.tres and {name}.tscn into your project at {_godot_path(o['godot_path'])}",
                   f"  (or edit the paths inside the .tres/.tscn). Open {name}.tscn: an AnimatedSprite2D with all animations;",
                   f"  its origin is the character's feet (centered = off, offset = ({-px}, {-py})). Pixel filter is set to Nearest.", ""]
    if o["unity"]:
        readme += ["UNITY", f"  Copy {sheet_name}, {name}_unity.json and SpriteForgeImporter.cs into Assets/ (script into an Editor folder or anywhere).",
                   f"  Select {name}_unity.json, then Assets > SpriteForge > Import Sprite Sheet. It slices the sprites (pivot = feet,",
                   f"  {o['ppu']} pixels per unit) and creates one .anim clip per animation next to the sheet.", ""]
    readme += ["ASEPRITE / PHASER / OTHERS", f"  {name}_atlas.json is an Aseprite-style JSON hash (frames, frameTags with loop and fps, pivot)."]
    (d / "README.txt").write_text("\n".join(readme))
    files.append("README.txt")
    return {"dir": str(d), "files": files, "sheet": [W, H], "cell": [cw, ch], "pivot": [px, py], "frames": len(pos)}
