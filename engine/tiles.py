"""Tiles and props: seamless tiles, pixel-level seam repair, tile preview helpers and tileset / atlas export.

Seamless tiles
  A tile is seamless when its right edge continues into its left edge (and bottom into top). The classic trick, used here:
  shift the image by half its size (that moves the old seams to the middle and makes the old EDGES neighbours of each other),
  then bring the original back in the middle with a weight that is exactly 0 on all four borders.  The borders of the result
  come from the shifted copy, whose borders are continuous by construction.
    * `make_seamless`   blends (smooth, for the high-resolution AI image BEFORE it is converted to pixels)
    * `seamless_pixels` instead PICKS between the two copies with an ordered-dither threshold, so a pixel tile never gets a
                        new in-between colour (the palette stays exactly the same)
  `seam_score` measures the wrap-around join: ~1 = as smooth as the inside of the tile, much more than 1 = visible seam.

Export: `export_tileset` (equal-sized tiles -> one grid sheet + Godot 4 TileSet .tres + Tiled .tsx + json) or, for tiles of
different sizes (props, items), a packed atlas + json.
"""
import json, math, re
from pathlib import Path
import numpy as np
from PIL import Image

from . import pixelize as px


class TileError(ValueError):
    pass


def _safe(s, default="tiles"):
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", str(s or "")).strip("_")[:40]
    return s or default


# ---------------------------------------------------------------- seamless
def _smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def _weights(h, w, soft):
    """(h, w) weight of the ORIGINAL image: exactly 0 on all four borders, 1 in the middle (flat core, smooth ramp)."""
    def axis(n):
        if n < 2:
            return np.zeros(n)
        t = 1.0 - np.abs(np.arange(n) * 2.0 / (n - 1) - 1.0)  # 0 at both ends, 1 in the middle
        return _smoothstep(t / max(soft, 1e-3))
    return axis(h)[:, None] * axis(w)[None, :]


def make_seamless(img, soft=0.5):
    """Smooth blend (for the high-resolution AI image). `soft` = width of the blend ramp as a fraction of half the image."""
    a = np.asarray(img.convert("RGB"), np.float32)
    h, w = a.shape[:2]
    o = np.roll(a, (h // 2, w // 2), axis=(0, 1))
    k = _weights(h, w, soft)[..., None]
    return Image.fromarray(np.clip(a * k + o * (1 - k) + 0.5, 0, 255).astype(np.uint8), "RGB")


_BAYER8 = np.array([[0, 32, 8, 40, 2, 34, 10, 42], [48, 16, 56, 24, 50, 18, 58, 26], [12, 44, 4, 36, 14, 46, 6, 38],
                    [60, 28, 52, 20, 62, 30, 54, 22], [3, 35, 11, 43, 1, 33, 9, 41], [51, 19, 59, 27, 49, 17, 57, 25],
                    [15, 47, 7, 39, 13, 45, 5, 37], [63, 31, 55, 23, 61, 29, 53, 21]])


def seamless_pixels(sprite, soft=0.5):
    """Make a PIXEL tile seamless without inventing colours: every pixel is taken from the original or from the half-shifted copy."""
    a = np.asarray(sprite.convert("RGBA"))
    h, w = a.shape[:2]
    o = np.roll(a, (h // 2, w // 2), axis=(0, 1))
    thr = (_BAYER8[np.arange(h)[:, None] % 8, np.arange(w)[None, :] % 8] + 0.5) / 64.0  # strictly inside (0, 1)
    use_a = (_weights(h, w, soft) > thr)[..., None]
    return Image.fromarray(np.where(use_a, a, o).astype(np.uint8), "RGBA")


def seam_score(img):
    """Wrap-around join vs the average neighbour step inside the image (~1 = invisible, >> 1 = visible seam). Mean over both axes."""
    a = np.asarray(img.convert("RGB"), np.float32)
    if min(a.shape[:2]) < 3:
        return 1.0
    sx = np.abs(a[:, 0] - a[:, -1]).mean()
    sy = np.abs(a[0] - a[-1]).mean()
    ix = np.abs(np.diff(a, axis=1)).mean()
    iy = np.abs(np.diff(a, axis=0)).mean()
    return round(float((sx + sy) / (ix + iy + 1e-3)), 3)


def wrap_offset(sprite, dx=None, dy=None):
    """Shift with wrap-around (default: half the size) so the seams show up in the middle: for inspecting and painting seams."""
    a = np.asarray(sprite.convert("RGBA"))
    h, w = a.shape[:2]
    dx = w // 2 if dx is None else int(dx) % w
    dy = h // 2 if dy is None else int(dy) % h
    return Image.fromarray(np.roll(a, (dy, dx), axis=(0, 1)), "RGBA")


def tile_post(raw, size, colors=16, palette="none", seamless=True, soft=0.5):
    """AI image -> pixel tile: (optionally) make the high-res image seamless, then reduce onto a size x size grid.
    No background removal / crop / outline / despeckle: all of them would break the wrap-around join."""
    img = raw.convert("RGB")
    raw_score = seam_score(img)
    if seamless:
        img = make_seamless(img, soft)
    sprite, info = px.pixelize(img, "canvas", size, colors, palette, False, 0, remove_shadow=False, crisp=True, clean=False, outline="none")
    info["seam"] = seam_score(sprite)
    info["seam_raw"] = raw_score
    info["label"] = f"seam {info['seam']}"
    return sprite, info


def tiled(sprite, cols=3, rows=3):
    """The tile repeated cols x rows times (for previews and tests)."""
    a = np.asarray(sprite.convert("RGBA"))
    return Image.fromarray(np.tile(a, (rows, cols, 1)), "RGBA")


# ---------------------------------------------------------------- tileset / atlas
def _grid_layout(n, tw, th, columns, spacing, margin):
    columns = max(1, min(int(columns), n))
    rows = math.ceil(n / columns)
    W = margin * 2 + columns * tw + (columns - 1) * spacing
    H = margin * 2 + rows * th + (rows - 1) * spacing
    regions = [(margin + (i % columns) * (tw + spacing), margin + (i // columns) * (th + spacing), tw, th) for i in range(n)]
    return columns, rows, (W, H), regions


def _shelf_pack(sizes, max_w=512, pad=1):
    """Pack rectangles on shelves (tallest first). Returns regions in input order and the sheet size."""
    order = sorted(range(len(sizes)), key=lambda i: (-sizes[i][1], -sizes[i][0]))
    max_w = max(max_w, max(s[0] for s in sizes) + 2 * pad)
    regions, x, y, rowh, sheet_w = [None] * len(sizes), pad, pad, 0, 0
    for i in order:
        w, h = sizes[i]
        if x + w + pad > max_w:
            x, y, rowh = pad, y + rowh + pad, 0
        regions[i] = (x, y, w, h)
        x += w + pad
        rowh = max(rowh, h)
        sheet_w = max(sheet_w, x)
    return regions, (sheet_w, y + rowh + pad)


def _num(v):
    return str(int(v)) if float(v) == int(v) else str(v)


def _tres(name, png, tw, th, n, columns, spacing, margin, gpath, solid=None):
    lines = ['[gd_resource type="TileSet" load_steps=3 format=3]', "",
             f'[ext_resource type="Texture2D" path="{gpath}{png}" id="1_tex"]', "",
             '[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_1"]', 'texture = ExtResource("1_tex")']
    if margin:
        lines.append(f"margins = Vector2i({margin}, {margin})")
    if spacing:
        lines.append(f"separation = Vector2i({spacing}, {spacing})")
    lines.append(f"texture_region_size = Vector2i({tw}, {th})")
    hw, hh = tw / 2, th / 2
    poly = f"PackedVector2Array({_num(-hw)}, {_num(-hh)}, {_num(hw)}, {_num(-hh)}, {_num(hw)}, {_num(hh)}, {_num(-hw)}, {_num(hh)})"
    for i in range(n):
        lines.append(f"{i % columns}:{i // columns}/0 = 0")
        if solid and i < len(solid) and solid[i]:
            lines.append(f"{i % columns}:{i // columns}/0/physics_layer_0/polygon_0/points = {poly}")
    lines += ["", "[resource]", f"tile_size = Vector2i({tw}, {th})"]
    if solid and any(solid):
        lines.append("physics_layer_0/collision_layer = 1")
    lines += ['sources/0 = SubResource("TileSetAtlasSource_1")', ""]
    return "\n".join(lines)


def _tsx(name, png, tw, th, n, columns, spacing, margin, size, names, solid=None):
    def coll(i):
        if solid and i < len(solid) and solid[i]:
            return f'<objectgroup draworder="index" id="2"><object id="1" x="0" y="0" width="{tw}" height="{th}"/></objectgroup>'
        return ""
    props = "".join(f'\n <tile id="{i}"><properties><property name="name" value="{re.sub(r"[^A-Za-z0-9_ -]", "", names[i])}"/></properties>{coll(i)}</tile>'
                    for i in range(n))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<tileset version="1.10" tiledversion="1.10.2" name="{name}" tilewidth="{tw}" tileheight="{th}" tilecount="{n}" columns="{columns}"'
            + (f' spacing="{spacing}"' if spacing else "") + (f' margin="{margin}"' if margin else "") + ">\n"
            f' <image source="{png}" width="{size[0]}" height="{size[1]}"/>{props}\n</tileset>\n')


def build_sheet(tiles, regions, size):
    sheet = Image.new("RGBA", size, (0, 0, 0, 0))
    for t, (x, y, w, h) in zip(tiles, regions):
        sheet.paste(t.convert("RGBA"), (x, y))
    return sheet


def export_tileset(tiles, names, opts, name, root):
    """tiles: list of RGBA images; names: one per tile. opts: columns, spacing, margin, godot, godot_path, tiled.
    Equal sizes -> grid sheet (+ Godot TileSet, Tiled .tsx). Mixed sizes -> packed atlas (+ json). Returns a summary dict."""
    from .exporter import _godot_path  # same path rules as the animation export
    if not tiles:
        raise TileError("add at least one tile first")
    if len(tiles) > 512:
        raise TileError("too many tiles (max 512)")
    names = [(names[i] if i < len(names) and str(names[i]).strip() else f"tile_{i:02d}") for i in range(len(tiles))]
    # names must be unique in the json / tsx
    seen, uniq = {}, []
    for nm in names:
        nm = _safe(nm, "tile")
        seen[nm] = seen.get(nm, 0) + 1
        uniq.append(nm if seen[nm] == 1 else f"{nm}_{seen[nm]}")
    name = _safe(name)
    d = Path(root) / "exports" / f"{name}_tileset"
    d.mkdir(parents=True, exist_ok=True)
    sizes = [t.size for t in tiles]
    uniform = len(set(sizes)) == 1
    files, readme = [], []
    solid = [bool(x) for x in (opts.get("solid") or [])][:len(tiles)]
    if uniform:
        tw, th = sizes[0]
        spacing, margin = max(0, min(int(opts.get("spacing", 0)), 16)), max(0, min(int(opts.get("margin", 0)), 16))
        columns, rows, size, regions = _grid_layout(len(tiles), tw, th, opts.get("columns", 8), spacing, margin)
        sheet = build_sheet(tiles, regions, size)
        png = f"{name}.png"
        sheet.save(d / png)
        files.append(png)
        meta = {"name": name, "type": "tileset", "tile_size": [tw, th], "columns": columns, "rows": rows, "spacing": spacing, "margin": margin,
                "sheet": list(size), "tiles": [{"index": i, "name": uniq[i], "x": r[0], "y": r[1], "w": tw, "h": th, "solid": bool(i < len(solid) and solid[i])} for i, r in enumerate(regions)]}
        (d / "tileset.json").write_text(json.dumps(meta, indent=1))
        files.append("tileset.json")
        gp = _godot_path(opts.get("godot_path", "res://tiles/"))
        if opts.get("godot", True):
            (d / f"{name}.tres").write_text(_tres(name, png, tw, th, len(tiles), columns, spacing, margin, gp, solid))
            files.append(f"{name}.tres")
            readme += ["GODOT 4", f"  Copy {png} and {name}.tres to {gp}  (or edit the path inside the .tres). Use the .tres as the TileSet of a TileMapLayer.",
                       "  Every tile is already registered." + (f" {sum(solid)} tile(s) marked solid have a full-tile collision shape on physics layer 0." if any(solid) else " Add collision / terrain in the TileSet editor.")]
        if opts.get("tiled", True):
            (d / f"{name}.tsx").write_text(_tsx(name, png, tw, th, len(tiles), columns, spacing, margin, size, uniq, solid))
            files.append(f"{name}.tsx")
            readme += ["TILED", f"  Keep {png} and {name}.tsx together, then Map > Add External Tileset." + (" Solid tiles have a full-tile collision rectangle." if any(solid) else "")]
        readme += ["UNITY", f"  Import {png}: Sprite Mode = Multiple, Filter Mode = Point, Compression = None, Sprite Editor > Slice > Grid By Cell Size {tw} x {th}"
                   + (f", Padding {spacing}, Offset {margin}." if spacing or margin else "."), "  Then create a Tile Palette from the sliced sprites."]
    else:
        regions, size = _shelf_pack(sizes)
        sheet = build_sheet(tiles, regions, size)
        png = f"{name}.png"
        sheet.save(d / png)
        files.append(png)
        meta = {"frames": {uniq[i]: {"frame": {"x": r[0], "y": r[1], "w": r[2], "h": r[3]}} for i, r in enumerate(regions)},
                "meta": {"image": png, "size": {"w": size[0], "h": size[1]}, "type": "atlas"}}
        (d / "atlas.json").write_text(json.dumps(meta, indent=1))
        files.append("atlas.json")
        columns, rows = 0, 0
        readme += ["The sprites have different sizes, so they are packed into an atlas (not a tile grid).",
                   "atlas.json lists every region (Aseprite / TexturePacker-style 'frames' hash). Godot: AtlasTexture per region; Unity: Sprite Editor > Slice > Automatic."]
    (d / "README.txt").write_text(f"{name}: {len(tiles)} {'tiles' if uniform else 'sprites'}\n\n" + "\n".join(readme) + "\n")
    files.append("README.txt")
    return {"dir": str(d), "files": files, "sheet": list(size), "count": len(tiles), "mode": "tileset" if uniform else "atlas",
            "columns": columns, "rows": rows, "names": uniq}


# ---------------------------------------------------------------- AI seam repair
def repair_seams(tile, inpaint_fn, prompt, negative, ckpt, lora, lora_w, lora_dir, strength=0.55, steps=22, cfg=7.0, seed=0, bg="white",
                 band=0.16, size=1024):
    """Let the AI redraw ONLY the seam cross of a tile.  The tile is shifted by half (the old edges become a cross in the middle),
    the cross is inpainted, and the pixels outside the cross are kept exactly.  The borders of the shifted image are untouched and
    already continuous, so the result is seamless whatever the AI paints inside the cross.  Output colours are snapped to the tile's own palette."""
    tile = tile.convert("RGBA")
    n = tile.width
    if tile.width != tile.height or not 8 <= n <= 256:
        raise TileError("the tile must be square, 8 to 256 px")
    shifted = wrap_offset(tile)
    bw = max(2, int(round(float(band) * n)))
    yy, xx = np.mgrid[0:n, 0:n]
    cross = (np.abs(xx - n // 2) < bw / 2 + 0.5) | (np.abs(yy - n // 2) < bw / 2 + 0.5)
    img = shifted.convert("RGB").resize((size, size), Image.NEAREST)
    mask = Image.fromarray((cross * 255).astype(np.uint8), "L").resize((size, size), Image.NEAREST)
    out = inpaint_fn(ckpt, lora, lora_w, lora_dir, prompt, negative, img, mask, strength, steps, cfg, seed, bg, "tile")
    cols = np.unique(np.asarray(tile.convert("RGB")).reshape(-1, 3), axis=0)
    if len(cols) > 64:
        cols = px.palette_from_sprite(tile, 64)
    S = size // n if size % n == 0 else 6
    fixed = px.crisp_reduce(out.convert("RGB"), n, n, S, np.asarray(cols, np.uint8))
    a, b = np.asarray(shifted), np.asarray(fixed)
    merged = np.where(cross[..., None], b, a).astype(np.uint8)
    res = Image.fromarray(merged, "RGBA")
    back = wrap_offset(res, n - n // 2, n - n // 2)   # exact inverse of the half shift (also for odd sizes)
    return back, {"seam_before": seam_score(tile), "seam": seam_score(back), "band": bw}


# ---------------------------------------------------------------- animated tiles
ANIM_MODES = ("scroll", "ripple", "shimmer")
_DIRS = {"right": (1, 0), "left": (-1, 0), "down": (0, 1), "up": (0, -1), "diag": (1, 1)}


def animate_tile(tile, mode="scroll", frames=8, direction="right", amount=0, density=0.25, seed=1):
    """Loop-perfect animation of a seamless tile, no new colours:
    scroll  = the tile wraps around by 1/frames of its size per frame;  ripple = every row shifted sideways by a sine (water);
    shimmer = a fraction of the pixels steps to the next lighter / darker colour of the tile and back (sparkle, lava)."""
    a = np.asarray(tile.convert("RGBA"))
    h, w = a.shape[:2]
    frames = max(2, min(int(frames), 32))
    if mode not in ANIM_MODES:
        raise TileError(f"unknown animation '{mode}' (scroll, ripple, shimmer)")
    out = []
    if mode == "scroll":
        if direction not in _DIRS:
            raise TileError("direction must be right, left, down, up or diag")
        dx, dy = _DIRS[direction]
        for i in range(frames):
            out.append(np.roll(a, (round(i * h / frames) * dy, round(i * w / frames) * dx), axis=(0, 1)))
    elif mode == "ripple":
        amp = float(amount) if amount and float(amount) > 0 else max(1.0, w / 16)
        ys = np.arange(h)
        for i in range(frames):
            sh = np.round(amp * np.sin(2 * np.pi * (2 * ys / h + i / frames))).astype(int)
            out.append(np.stack([np.roll(a[y], sh[y], axis=0) for y in range(h)]))
    else:
        rgb = a[..., :3].reshape(-1, 3)
        uniq, inv = np.unique(rgb, axis=0, return_inverse=True)
        inv = inv.reshape(-1)
        order = np.argsort(uniq @ np.array([0.299, 0.587, 0.114]), kind="stable")
        rank_of = np.empty(len(uniq), int)
        rank_of[order] = np.arange(len(uniq))
        r = rank_of[inv].reshape(h, w)
        cols = uniq[order]
        rng = np.random.RandomState(int(seed))
        phase, active = rng.rand(h, w), rng.rand(h, w) < float(density)
        amp = float(amount) if amount and float(amount) > 0 else 1.0
        for i in range(frames):
            d = np.round(amp * np.sin(2 * np.pi * (phase + i / frames))).astype(int) * active
            f = a.copy()
            f[..., :3] = cols[np.clip(r + d, 0, len(cols) - 1)]
            out.append(f)
    return [Image.fromarray(f.astype(np.uint8), "RGBA") for f in out]


def export_animated(frames, name, opts, root):
    """exports/<name>_anim/: horizontal strip, preview GIF, json, Godot 4 TileSet with an animated tile, Tiled .tsx with an animation."""
    from .exporter import _godot_path, _gif
    if len(frames) < 2:
        raise TileError("an animation needs at least 2 frames")
    name = _safe(name, "animated")
    ms = max(20, min(int(opts.get("ms", 120)), 2000))
    n, (tw, th) = len(frames), frames[0].size
    d = Path(root) / "exports" / f"{name}_anim"
    d.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGBA", (tw * n, th), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        sheet.paste(f, (i * tw, 0))
    png = f"{name}.png"
    sheet.save(d / png)
    files = [png]
    _gif(frames, 1000 / ms, str(d / f"{name}_preview.gif"), 4)
    files.append(f"{name}_preview.gif")
    (d / "animation.json").write_text(json.dumps({"name": name, "tile_size": [tw, th], "frames": n, "duration_ms": ms, "sheet": [tw * n, th], "layout": "horizontal strip"}, indent=1))
    files.append("animation.json")
    readme = [f"{name}: animated tile, {n} frames of {tw}x{th} px, {ms} ms per frame, as a horizontal strip.", ""]
    if opts.get("godot", True):
        gp = _godot_path(opts.get("godot_path", "res://tiles/"))
        L = ['[gd_resource type="TileSet" load_steps=3 format=3]', "", f'[ext_resource type="Texture2D" path="{gp}{png}" id="1_tex"]', "",
             '[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_1"]', 'texture = ExtResource("1_tex")', f"texture_region_size = Vector2i({tw}, {th})"]
        L += [f"0:0/animation_frame_{i}/duration = {ms / 1000:g}" for i in range(n)]
        L += ["0:0/0 = 0", "", "[resource]", f"tile_size = Vector2i({tw}, {th})", 'sources/0 = SubResource("TileSetAtlasSource_1")', ""]
        (d / f"{name}.tres").write_text("\n".join(L))
        files.append(f"{name}.tres")
        readme += ["GODOT 4", f"  Copy {png} and {name}.tres to {gp}. The first tile of the TileSet is animated (the strip holds its frames)."]
    if opts.get("tiled", True):
        fr = "".join(f'<frame tileid="{i}" duration="{ms}"/>' for i in range(n))
        (d / f"{name}.tsx").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                       f'<tileset version="1.10" tiledversion="1.10.2" name="{name}" tilewidth="{tw}" tileheight="{th}" tilecount="{n}" columns="{n}">\n'
                                       f' <image source="{png}" width="{tw * n}" height="{th}"/>\n <tile id="0"><animation>{fr}</animation></tile>\n</tileset>\n')
        files.append(f"{name}.tsx")
        readme += ["TILED", f"  Keep {png} and {name}.tsx together; tile 0 is the animated tile (frames 0-{n - 1})."]
    readme += ["UNITY", f"  Slice {png} by cell size {tw} x {th} and use the frames in an Animation / Tile animation."]
    (d / "README.txt").write_text("\n".join(readme) + "\n")
    files.append("README.txt")
    return {"dir": str(d), "files": files, "frames": n, "ms": ms, "sheet": [tw * n, th]}
