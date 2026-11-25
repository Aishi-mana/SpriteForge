"""Autotile / terrain sets: from one seamless tile (terrain A, e.g. grass) and optionally a second one (ground B, e.g. dirt)
generate a complete transition set that a tile engine can place automatically.

  blob47  : 47 tiles, every combination of the 8 neighbours (corners only count when both touching edges are set)
  edge16  : 16 tiles, only the 4 edge neighbours matter (convex corners rounded, inner corners square-ish)

How a tile is made (geometry is exact, not drawn by hand)
  1. The neighbourhood is a 3x3 block of cells; the centre cell and every neighbour that is "terrain A" are filled.
  2. The filled shape is pulled back from the empty cells by `inset` pixels (erosion), then its convex corners are rounded by `round`
     pixels (a dilation by that radius): A = dilate(erode(F, inset + round), round).   Concave corners come out round automatically.
  3. The centre cell of that mask is cut out.  Because every tile is the crop of ONE global mask, neighbouring tiles join exactly.
     (tests/test_terrain.py checks this against a mask computed for a whole random map.)
  4. Pixels inside the mask show terrain A's texture, the rest terrain B's (or are transparent), optionally with a 1-2 px rim colour
     (darkest / lightest colour of A) along the border.  A and B are seamless tiles, so every tile keeps the texture phase and no
     seam shows between tiles.

Neighbour bits (clockwise from north): N=1 NE=2 E=4 SE=8 S=16 SW=32 W=64 NW=128.
"""
import json, re
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from . import tiles as T

KINDS = ("blob47", "edge16")
OFF = {1: (0, -1), 2: (1, -1), 4: (1, 0), 8: (1, 1), 16: (0, 1), 32: (-1, 1), 64: (-1, 0), 128: (-1, -1)}
EDGE_BITS = 1 | 4 | 16 | 64
NAMES = {1: "N", 2: "NE", 4: "E", 8: "SE", 16: "S", 32: "SW", 64: "W", 128: "NW"}
# Godot 4 peering bit names
GODOT_BITS = {4: "right_side", 8: "bottom_right_corner", 16: "bottom_side", 32: "bottom_left_corner",
              64: "left_side", 128: "top_left_corner", 1: "top_side", 2: "top_right_corner"}


class TerrainError(ValueError):
    pass


def canon_blob(m):
    """A corner bit only counts when both edges that touch it are set (that is what reduces 256 cases to 47)."""
    m &= 255
    for corner, (e1, e2) in {2: (1, 4), 8: (4, 16), 32: (16, 64), 128: (64, 1)}.items():
        if m & corner and not (m & e1 and m & e2):
            m &= ~corner
    return m


def canon_edge(m):
    return m & EDGE_BITS


def canon_for(kind):
    if kind not in KINDS:
        raise TerrainError(f"unknown set type '{kind}' (use blob47 or edge16)")
    return canon_blob if kind == "blob47" else canon_edge


def canonical_masks(kind):
    f = canon_for(kind)
    return sorted({f(m) for m in range(256)})


def lookup_table(kind):
    """raw 8-bit neighbour mask -> index of the tile to use (the order of the set)."""
    masks = canonical_masks(kind)
    pos = {m: i for i, m in enumerate(masks)}
    f = canon_for(kind)
    return [pos[f(m)] for m in range(256)]


def neighbor_mask(grid, x, y):
    """Raw mask of cell (x, y) in a 2-D list/array of 0/1 (outside the grid counts as empty)."""
    h, w = len(grid), len(grid[0])
    m = 0
    for bit, (dx, dy) in OFF.items():
        xx, yy = x + dx, y + dy
        if 0 <= xx < w and 0 <= yy < h and grid[yy][xx]:
            m |= bit
    return m


# ---------------------------------------------------------------- geometry
def _field(mask, kind, R):
    F = np.zeros((3 * R, 3 * R), bool)
    F[R:2 * R, R:2 * R] = True
    for bit, (dx, dy) in OFF.items():
        filled = bool(mask & bit)
        if kind == "edge16" and bit not in (1, 4, 16, 64):
            filled = True  # edge sets ignore diagonals: assume filled
        if filled:
            F[(1 + dy) * R:(2 + dy) * R, (1 + dx) * R:(2 + dx) * R] = True
    return F


def _shape(F, r, rho):
    """dilate(erode(F, r + rho), rho) with Euclidean distances (supersampled pixels). Pixel centres: boundary at distance d - 0.5."""
    d = ndi.distance_transform_edt(F)
    core = d >= (r + rho) + 0.5
    if not core.any():
        return np.zeros_like(F)
    if rho <= 0:
        return core
    return ndi.distance_transform_edt(~core) <= rho + 0.5


def _pipeline(F, T_, ss, r, rho, rimw):
    """Whole-canvas mask at final resolution + rim mask. F is at supersample resolution (cells of T_*ss px)."""
    A = _shape(F, r * ss, rho * ss)
    h, w = A.shape
    small = A.reshape(h // ss, ss, w // ss, ss).mean((1, 3)) >= 0.5
    rim = np.zeros_like(small)
    if rimw > 0:
        rim = small & (ndi.distance_transform_edt(small) <= rimw + 0.5)
    return small, rim


def _params(T_, inset, rnd):
    inset = int(inset) if inset and int(inset) > 0 else max(1, round(T_ * 0.2))
    rnd = int(rnd) if rnd is not None and int(rnd) >= 0 and rnd != "" else max(1, round(T_ * 0.15))
    inset = min(inset, int(T_ * 0.3))
    rnd = min(rnd, int(T_ * 0.2))
    return max(inset, 1), max(rnd, 0)


def _supersample(T_):
    return max(2, 128 // T_)


def tile_masks(mask, kind, T_, inset=0, rnd=None, rimw=1):
    """(A, rim) boolean T_xT_ arrays of one tile for a raw neighbour mask."""
    r, rho = _params(T_, inset, rnd)
    ss = _supersample(T_)
    small, rim = _pipeline(_field(mask, kind, T_ * ss), T_, ss, r, rho, rimw)
    return small[T_:2 * T_, T_:2 * T_], rim[T_:2 * T_, T_:2 * T_]


# ---------------------------------------------------------------- colours / compose
def _opaque(img, what):
    img = img.convert("RGBA")
    if (np.asarray(img)[..., 3] < 255).any():
        raise TerrainError(f"{what} has transparent pixels: use a full (seamless) tile")
    return img


def rim_color(a_tex, mode):
    """Darkest (or lightest) colour of A that covers a meaningful share of it, darkened (or lightened) a little."""
    arr = np.asarray(a_tex.convert("RGB")).reshape(-1, 3)
    cols, counts = np.unique(arr, axis=0, return_counts=True)
    keep = counts >= max(2, 0.02 * len(arr))
    cols = cols[keep] if keep.any() else cols
    lum = cols @ np.array([0.299, 0.587, 0.114])
    if mode == "light":
        c = cols[lum.argmax()].astype(float)
        c = c + (255 - c) * 0.35
    else:
        c = cols[lum.argmin()].astype(float) * 0.65
    return tuple(int(round(v)) for v in np.clip(c, 0, 255)) + (255,)


def average_color(a_tex):
    return tuple(int(v) for v in np.asarray(a_tex.convert("RGB")).reshape(-1, 3).mean(0))


def generate_set(a, b=None, kind="blob47", inset=0, rnd=None, rim="dark", base="bake", ground=True):
    """a: terrain A tile, b: ground tile (optional), kind blob47 / edge16, rim none|dark|light, base bake|transparent.
    Returns {"tiles": [{index, mask, image}], "ground": image|None, "lookup": [...], ...}."""
    canon_for(kind)
    if rim not in ("none", "dark", "light"):
        raise TerrainError("rim must be none, dark or light")
    if base not in ("bake", "transparent"):
        raise TerrainError("base must be bake or transparent")
    a = _opaque(a, "terrain tile A")
    T_ = a.width
    if a.width != a.height:
        raise TerrainError("terrain tiles must be square")
    if not 8 <= T_ <= 128:
        raise TerrainError("tile size must be between 8 and 128 px")
    if b is not None:
        b = _opaque(b, "ground tile B")
        if b.size != a.size:
            raise TerrainError(f"A is {a.width}x{a.height} but B is {b.width}x{b.height}: both tiles must have the same size")
    if base == "bake" and b is None:
        base = "transparent"  # nothing to put underneath
    r, rho = _params(T_, inset, rnd)
    rimw = 0 if rim == "none" else (2 if T_ >= 48 else 1)
    rc = rim_color(a, rim) if rimw else None
    A_arr = np.asarray(a)
    B_arr = np.asarray(b) if b is not None else np.zeros_like(A_arr)
    masks = canonical_masks(kind)
    tiles = []
    for i, m in enumerate(masks):
        A, R_ = tile_masks(m, kind, T_, inset, rnd, rimw)
        out = np.where(A[..., None], A_arr, B_arr if base == "bake" else np.zeros_like(A_arr))
        if rimw:
            out = np.where((R_ & A)[..., None], np.array(rc, np.uint8), out)
        tiles.append({"index": i, "mask": m, "image": Image.fromarray(out.astype(np.uint8), "RGBA")})
    return {"tiles": tiles, "ground": b if (b is not None and ground and base == "bake") else None, "lookup": lookup_table(kind), "kind": kind,
            "tile_size": T_, "inset": r, "round": rho, "rim": rim, "base": base, "color": average_color(a),
            "rim_color": rc if rimw else None}


# ---------------------------------------------------------------- export
def _slug(s):
    return re.sub(r"[^A-Za-z0-9_ -]", "", str(s))[:40] or "terrain"


def _tres_terrain(name, png, tw, th, entries, kind, gpath, color, tname):
    mode = 0 if kind == "blob47" else 2
    L = ['[gd_resource type="TileSet" load_steps=3 format=3]', "", f'[ext_resource type="Texture2D" path="{gpath}{png}" id="1_tex"]', "",
         '[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_1"]', 'texture = ExtResource("1_tex")', f"texture_region_size = Vector2i({tw}, {th})"]
    for e in entries:
        cx, cy = e["col"], e["row"]
        L.append(f"{cx}:{cy}/0 = 0")
        if e["mask"] is None:   # the plain ground tile: not part of the terrain
            continue
        L += [f"{cx}:{cy}/0/terrain_set = 0", f"{cx}:{cy}/0/terrain = 0"]
        for bit, nm in GODOT_BITS.items():
            if e["mask"] & bit and (kind == "blob47" or bit in (1, 4, 16, 64)):
                L.append(f"{cx}:{cy}/0/terrains_peering_bit/{nm} = 0")
    r, g, b = (c / 255 for c in color[:3])
    L += ["", "[resource]", f"tile_size = Vector2i({tw}, {th})", f"terrain_set_0/mode = {mode}", f'terrain_set_0/terrain_0/name = "{tname}"',
          f"terrain_set_0/terrain_0/color = Color({r:.3f}, {g:.3f}, {b:.3f}, 1)", 'sources/0 = SubResource("TileSetAtlasSource_1")', ""]
    return "\n".join(L)


def _tsx_terrain(name, png, tw, th, count, columns, size, entries, kind, color, tname):
    hexc = "#%02x%02x%02x" % tuple(color[:3])
    wt = []
    for e in entries:
        if e["mask"] is None:
            continue
        m = e["mask"]
        if kind == "blob47":
            ids = [1 if m & bit else 0 for bit in (1, 2, 4, 8, 16, 32, 64, 128)]       # top, topright, right, bottomright, bottom, bottomleft, left, topleft
        else:
            ids = [1 if m & 1 else 0, 0, 1 if m & 4 else 0, 0, 1 if m & 16 else 0, 0, 1 if m & 64 else 0, 0]
        wt.append(f'   <wangtile tileid="{e["index"]}" wangid="{",".join(map(str, ids))}"/>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<tileset version="1.10" tiledversion="1.10.2" name="{name}" tilewidth="{tw}" tileheight="{th}" tilecount="{count}" columns="{columns}">\n'
            f' <image source="{png}" width="{size[0]}" height="{size[1]}"/>\n <wangsets>\n'
            f'  <wangset name="{tname}" type="{"mixed" if kind == "blob47" else "edge"}" tile="-1">\n'
            f'   <wangcolor name="{tname}" color="{hexc}" tile="-1" probability="1"/>\n' + "\n".join(wt) + "\n  </wangset>\n </wangsets>\n</tileset>\n")


def export_terrain(res, name, opts, root, terrain_name="Terrain"):
    """Write exports/<name>_terrain/: sheet png, terrain.json (incl. the 256-entry lookup), Godot 4 .tres, Tiled .tsx, README."""
    from .exporter import _godot_path
    name = T._safe(name, "terrain")
    tname = _slug(terrain_name)
    d = Path(root) / "exports" / f"{name}_terrain"
    d.mkdir(parents=True, exist_ok=True)
    kind, T_ = res["kind"], res["tile_size"]
    images = [t["image"] for t in res["tiles"]] + ([res["ground"].convert("RGBA")] if res["ground"] is not None else [])
    columns, rows, size, regions = T._grid_layout(len(images), T_, T_, opts.get("columns", 8), 0, 0)
    sheet = T.build_sheet(images, regions, size)
    png = f"{name}.png"
    sheet.save(d / png)
    entries = []
    for i, (reg, im) in enumerate(zip(regions, images)):
        is_tile = i < len(res["tiles"])
        entries.append({"index": i, "mask": res["tiles"][i]["mask"] if is_tile else None, "col": i % columns, "row": i // columns, "x": reg[0], "y": reg[1]})
    meta = {"name": name, "terrain": tname, "kind": kind, "tile_size": [T_, T_], "columns": columns, "rows": rows, "sheet": list(size),
            "bits": "N=1 NE=2 E=4 SE=8 S=16 SW=32 W=64 NW=128 (clockwise from north)", "base": res["base"],
            "tiles": [{"index": e["index"], "mask": e["mask"], "x": e["x"], "y": e["y"], "neighbors": [NAMES[b] for b in NAMES if e["mask"] & b]}
                      for e in entries if e["mask"] is not None],
            "ground": next(({"index": e["index"], "x": e["x"], "y": e["y"]} for e in entries if e["mask"] is None), None),
            "lookup": res["lookup"]}
    (d / "terrain.json").write_text(json.dumps(meta, indent=1))
    files = [png, "terrain.json"]
    readme = [f"{tname}: {kind} autotile set, {len(res['tiles'])} tiles of {T_}x{T_} px" + (" + a plain ground tile" if meta["ground"] else ""), "",
              "terrain.json: 'lookup' maps the 8-bit neighbour mask of a cell to the tile index (use it in your own engine / rule tile).",
              "Bits clockwise from north: N=1 NE=2 E=4 SE=8 S=16 SW=32 W=64 NW=128."]
    gp = _godot_path(opts.get("godot_path", "res://tiles/"))
    if opts.get("godot", True):
        (d / f"{name}.tres").write_text(_tres_terrain(name, png, T_, T_, entries, kind, gp, res["color"], tname))
        files.append(f"{name}.tres")
        readme += ["", "GODOT 4", f"  Copy {png} and {name}.tres to {gp} (or edit the path in the .tres). Use it as the TileSet of a TileMapLayer,",
                   "  then paint with the Terrains tab: terrain set 0 (" + ("match corners and sides" if kind == "blob47" else "match sides") + ")."]
    if opts.get("tiled", True):
        (d / f"{name}.tsx").write_text(_tsx_terrain(name, png, T_, T_, len(images), columns, size, entries, kind, res["color"], tname))
        files.append(f"{name}.tsx")
        readme += ["", "TILED", f"  Keep {png} and {name}.tsx together: Map > Add External Tileset; the Terrain Sets view has the wang set '{tname}'."]
    readme += ["", "UNITY", f"  Slice {png} by grid cell size {T_} x {T_}; use terrain.json's lookup for a Rule Tile / script."]
    (d / "README.txt").write_text("\n".join(readme) + "\n")
    files.append("README.txt")
    return {"dir": str(d), "files": files, "sheet": list(size), "count": len(res["tiles"]), "columns": columns, "rows": rows,
            "kind": kind, "ground": bool(meta["ground"])}


# =================================================================== corner sets (dual grid): 16 tiles for 2 terrains, N^4 for 2-4
"""A corner tile is defined by the terrain at its four CORNERS (nw, ne, se, sw), each one of N terrains:
   index = ((nw * N + ne) * N + se) * N + sw          (N = 2 -> 16 tiles, 3 -> 81, 4 -> 256)
 The terrain of every corner is a square 'dual cell' centred on that corner; the tile is the junction of four of them.
 Each terrain's indicator is smoothed with a finite Gaussian (radius <= 45 % of half a cell, so a tile depends on its own four
 corners only) and every pixel takes the terrain with the largest value: round blobs, clean partition, exact joins between tiles."""
from itertools import product

CORNER_KINDS = ("corner16", "multi")
CORNER_NAMES = ("nw", "ne", "se", "sw")


def corner_index(c, N):
    i = 0
    for v in c:
        i = i * N + int(v)
    return i


def corner_tuples(N):
    return list(product(range(N), repeat=4))      # lexicographic = index order


def _css(T_):
    """supersample for corner sets: even, cell of about 64 px"""
    return max(2, (64 // T_) // 2 * 2)


def _sigma(T_, rnd):
    s = 0.12 * T_ if rnd is None or rnd < 0 else float(rnd)
    return max(0.0, min(s, 0.15 * T_))


def _cfield(c, N, C):
    g = np.pad(np.array([[c[0], c[1]], [c[3], c[2]]]), 1, mode="edge")     # 4x4 dual cells, the middle 2x2 are the corners
    return np.kron(g, np.ones((C, C), np.int32))


def _classes(L, ss, sigma, N):
    """label field (supersampled) -> label map at final resolution (blur per terrain, argmax, majority per block)."""
    sig = sigma * ss
    cls = L
    if sig >= 0.5:
        g = np.stack([ndi.gaussian_filter((L == k).astype(np.float32), sig, truncate=3.0, mode="nearest") for k in range(N)])
        cls = g.argmax(0)
    h, w = cls.shape
    cnt = np.stack([(cls == k).reshape(h // ss, ss, w // ss, ss).sum((1, 3)) for k in range(N)])
    return cnt.argmax(0)


def _rim_mask(cls):
    """pixels that have a 4-neighbour with a LOWER terrain index (a 1 px line on the higher terrain's side)."""
    p = np.pad(cls, 1, mode="edge")
    low = np.zeros(cls.shape, bool)
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        low |= p[1 + dy:1 + dy + cls.shape[0], 1 + dx:1 + dx + cls.shape[1]] < cls
    return low


def corner_tile_classes(c, N, T_, rnd=None, rim=True):
    """(class map T_xT_, rim mask T_xT_) of one corner tile."""
    ss = _css(T_)
    C = T_ * ss
    cls = _classes(_cfield(c, N, C), ss, _sigma(T_, rnd), N)          # 4T x 4T
    o = int(1.5 * T_)
    crop = (slice(o, o + T_), slice(o, o + T_))
    return cls[crop], (_rim_mask(cls)[crop] if rim else np.zeros((T_, T_), bool))


def generate_corner(textures, rnd=None, rim="dark"):
    """textures: [A, B] (B may be None = transparent) for the 16-tile set, or [A, B, C(, D)] for a multi-terrain set.
    Returns {"tiles": [{index, corners, image}], "kind", "n", "tile_size", ...}."""
    N = len(textures)
    if not 2 <= N <= 4:
        raise TerrainError("a corner set needs 2 to 4 terrains")
    if textures[0] is None or any(t is None for t in textures[2:]) or (N > 2 and textures[1] is None):
        raise TerrainError("every terrain tile must be set (only the ground B of the 16-tile set may be empty)")
    if rim not in ("none", "dark", "light"):
        raise TerrainError("rim must be none, dark or light")
    texs = [_opaque(t, f"terrain tile {'ABCD'[i]}") if t is not None else None for i, t in enumerate(textures)]
    T_ = texs[0].width
    if texs[0].width != texs[0].height:
        raise TerrainError("terrain tiles must be square")
    if not 8 <= T_ <= 128 or T_ % 2:
        raise TerrainError("corner sets need an even tile size between 8 and 128 px")
    for i, t in enumerate(texs):
        if t is not None and t.size != texs[0].size:
            raise TerrainError(f"terrain {'ABCD'[i]} is {t.width}x{t.height} but A is {T_}x{T_}: all tiles must have the same size")
    arrs = [np.asarray(t) if t is not None else np.zeros((T_, T_, 4), np.uint8) for t in texs]
    rc = rim_color(texs[0], rim) if rim != "none" else None
    tiles = []
    for idx, c in enumerate(corner_tuples(N)):
        cls, rm = corner_tile_classes(c, N, T_, rnd, rim != "none")
        out = np.zeros((T_, T_, 4), np.uint8)
        for k in range(N):
            out[cls == k] = arrs[k][cls == k]
        if rc:
            out[rm] = np.array(rc, np.uint8)
        tiles.append({"index": idx, "corners": list(c), "image": Image.fromarray(out, "RGBA")})
    return {"tiles": tiles, "kind": "corner16" if N == 2 else "multi", "n": N, "tile_size": T_, "sigma": round(_sigma(T_, rnd), 2), "rim": rim,
            "rim_color": rc, "colors": [average_color(t) for t in texs if t is not None], "transparent_b": N == 2 and texs[1] is None}


def _tres_corner(name, png, T_, entries, res, gpath, names):
    N = res["n"]
    L = ['[gd_resource type="TileSet" load_steps=3 format=3]', "", f'[ext_resource type="Texture2D" path="{gpath}{png}" id="1_tex"]', "",
         '[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_1"]', 'texture = ExtResource("1_tex")', f"texture_region_size = Vector2i({T_}, {T_})"]
    gname = {0: "top_left_corner", 1: "top_right_corner", 2: "bottom_right_corner", 3: "bottom_left_corner"}
    for e in entries:
        cx, cy, c = e["col"], e["row"], e["corners"]
        L += [f"{cx}:{cy}/0 = 0", f"{cx}:{cy}/0/terrain_set = 0"]
        if N == 2:   # one terrain (A); corners that are not A simply have no bit
            L.append(f"{cx}:{cy}/0/terrain = 0")
            L += [f"{cx}:{cy}/0/terrains_peering_bit/{gname[i]} = 0" for i in range(4) if c[i] == 0]
        else:        # tile terrain = the most common corner terrain (lowest index on ties)
            main = max(range(N), key=lambda k: (c.count(k), -k))
            L.append(f"{cx}:{cy}/0/terrain = {main}")
            L += [f"{cx}:{cy}/0/terrains_peering_bit/{gname[i]} = {c[i]}" for i in range(4)]
    L += ["", "[resource]", f"tile_size = Vector2i({T_}, {T_})", "terrain_set_0/mode = 1"]
    for k in range(1 if N == 2 else N):
        r, g, b = (v / 255 for v in res["colors"][k][:3])
        L += [f'terrain_set_0/terrain_{k}/name = "{names[k]}"', f"terrain_set_0/terrain_{k}/color = Color({r:.3f}, {g:.3f}, {b:.3f}, 1)"]
    L += ['sources/0 = SubResource("TileSetAtlasSource_1")', ""]
    return "\n".join(L)


def _tsx_corner(name, png, T_, count, columns, size, entries, res, names):
    N = res["n"]
    cols = []
    for k in range(N):
        v = res["colors"][k] if k < len(res["colors"]) else (128, 128, 128)
        cols.append(f'   <wangcolor name="{names[k]}" color="#%02x%02x%02x" tile="-1" probability="1"/>' % tuple(v[:3]))
    wt = []
    for e in entries:
        c = e["corners"]      # wangid: top, topright, right, bottomright, bottom, bottomleft, left, topleft (corners only)
        wt.append(f'   <wangtile tileid="{e["index"]}" wangid="0,{c[1] + 1},0,{c[2] + 1},0,{c[3] + 1},0,{c[0] + 1}"/>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<tileset version="1.10" tiledversion="1.10.2" name="{name}" tilewidth="{T_}" tileheight="{T_}" tilecount="{count}" columns="{columns}">\n'
            f' <image source="{png}" width="{size[0]}" height="{size[1]}"/>\n <wangsets>\n'
            f'  <wangset name="{names[0]}" type="corner" tile="-1">\n' + "\n".join(cols) + "\n" + "\n".join(wt) + "\n  </wangset>\n </wangsets>\n</tileset>\n")


def export_corner(res, name, opts, root, names=None):
    """exports/<name>_terrain/ for corner16 / multi sets: sheet, terrain.json, Godot 4 .tres (match corners), Tiled corner wang set."""
    from .exporter import _godot_path
    name = T._safe(name, "terrain")
    N, T_ = res["n"], res["tile_size"]
    names = [_slug(n) for n in (names or [])] + [f"Terrain {'ABCD'[i]}" for i in range(4)]
    names = [names[i] if names[i].strip() else f"Terrain {'ABCD'[i]}" for i in range(4)]
    d = Path(root) / "exports" / f"{name}_terrain"
    d.mkdir(parents=True, exist_ok=True)
    images = [t["image"] for t in res["tiles"]]
    columns, rows, size, regions = T._grid_layout(len(images), T_, T_, opts.get("columns", 8 if N == 2 else 9), 0, 0)
    T.build_sheet(images, regions, size).save(d / f"{name}.png")
    png = f"{name}.png"
    entries = [{"index": t["index"], "corners": t["corners"], "col": i % columns, "row": i // columns, "x": regions[i][0], "y": regions[i][1]}
               for i, t in enumerate(res["tiles"])]
    meta = {"name": name, "kind": res["kind"], "terrains": names[:N], "tile_size": [T_, T_], "columns": columns, "rows": rows, "sheet": list(size),
            "index": "index = ((nw * N + ne) * N + se) * N + sw", "n": N, "transparent_b": res["transparent_b"],
            "tiles": [{"index": e["index"], "corners": dict(zip(CORNER_NAMES, e["corners"])), "x": e["x"], "y": e["y"]} for e in entries]}
    (d / "terrain.json").write_text(json.dumps(meta, indent=1))
    files = [png, "terrain.json"]
    readme = [f"{'/'.join(names[:N])}: {res['kind']} corner set, {len(images)} tiles of {T_}x{T_} px", "",
              "A tile is chosen by the terrain at its four corners (nw, ne, se, sw): index = ((nw*N + ne)*N + se)*N + sw."]
    gp = _godot_path(opts.get("godot_path", "res://tiles/"))
    if opts.get("godot", True):
        (d / f"{name}.tres").write_text(_tres_corner(name, png, T_, entries, res, gp, names))
        files.append(f"{name}.tres")
        readme += ["", "GODOT 4", f"  Copy {png} and {name}.tres to {gp}. TileSet terrain set 0 uses 'match corners'.",
                   "  " + ("One terrain (" + names[0] + "): paint with it over any base; tiles whose corners are not that terrain have no bit." if N == 2
                           else "Several terrains: each tile's terrain is its most common corner terrain. Painting rules for mixed tiles are best effort: please test in the Terrains tab.")]
    if opts.get("tiled", True):
        (d / f"{name}.tsx").write_text(_tsx_corner(name, png, T_, len(images), columns, size, entries, res, names))
        files.append(f"{name}.tsx")
        readme += ["", "TILED", f"  Keep {png} and {name}.tsx together; the wang set '{names[0]}' (type corner) has {N} colours and every combination."]
    readme += ["", "UNITY", f"  Slice {png} by grid cell size {T_} x {T_}; terrain.json maps every index to its corner terrains."]
    (d / "README.txt").write_text("\n".join(readme) + "\n")
    files.append("README.txt")
    return {"dir": str(d), "files": files, "sheet": list(size), "count": len(images), "columns": columns, "rows": rows, "kind": res["kind"], "ground": False}
