# Phase 21 - autotile / terrain sets
Unzip over your spriteforge folder. New: engine/terrain.py, tests/test_terrain.py. Changed: engine/main.py, engine/projects.py, ui/index.html, tests/js/queue_test.js, docs.
No packages, no rebuild: restart the engine / relaunch spriteforge.bat.

## What it does
On the **Tiles & props** tab, a new **Terrain set (autotile)** card turns two seamless tiles into a complete transition set:
- **Terrain A** = the thing that gets borders (grass, water, snow...). **Ground B** = what shows around it (dirt, sand...). Both are normal seamless tiles from this tab:
  put one on the workbench and press **Use workbench tile as A / B**. B is optional (without it the tiles are transparent outside A, to lay over any ground layer).
- **Generate set** makes **47 tiles** (blob: every combination of the 8 neighbours) or **16 tiles** (sides only), plus the plain ground tile.
- **Autotile map preview** paints a random blob-shaped map with the set, using the same neighbour lookup your engine will use: every join must look continuous.
- **Export terrain set** writes `exports/<name>_terrain/`: the sheet, `terrain.json` (every tile's neighbour mask + the **256-entry lookup** raw-mask -> tile), a **Godot 4 TileSet `.tres` with the terrain already set up**
  (terrain set 0, peering bits on every tile), a **Tiled `.tsx` with a wang set**, README. Unity: slice by grid + use the lookup.
- Options (sidebar): set type, border **inset** (px, 0 = auto), corner **rounding** (px, empty = auto), **rim** (dark outline / light rim / none: one extra colour taken from A), ground **baked in or transparent**, names.

## How the tiles are made (so you can trust the joins)
Each tile is the centre cell of ONE global shape: the 3x3 neighbourhood is filled, the shape is pulled back from empty cells by `inset` and its convex corners rounded by `rounding`
(erosion + dilation with true Euclidean distances at 2-8x supersampling, then reduced to your pixel grid). Inner corners come out round by themselves, and the 256 neighbour patterns collapse to exactly 47 shapes (checked).
The texture comes from your A and B tiles in tile coordinates, so the pattern continues across tiles with no seam. Colours used = A's + B's + at most one rim colour.
The inset is capped at 30 % and the rounding at 20 % of the tile so that no tile depends on anything beyond its 3x3 neighbourhood: tests compare every tile of random maps (16 and 32 px, rim included) with a mask computed for the whole map: zero differing pixels.

## Limits / honest notes
- A gets the borders; B is plain. For a second border (B over A) generate another set with the roles swapped.
- One terrain per set; Tiled gets one wang colour and Godot one terrain (add more in the editors).
- The texture is one repeated tile, so large areas show the pattern repeating; use several variants in Godot if that bothers you.
- Borders are geometric (round blobs with a rim), not hand-drawn art: for a different style, edit tiles in the pixel editor after export, or use `inset`, `rounding` and `rim` to change the look.
- Not verified here (no Godot / Tiled / browser): that Godot 4 and Tiled accept the files (they follow the formats those tools write: peering-bit names, terrain_set_0/mode, wangid order) and how the card looks.
- A 16-tile *corner* wang set (2x2 corner bits) is not included.

## Technical
- `engine/terrain.py`: `canon_blob/canon_edge`, `lookup_table`, `neighbor_mask`, `tile_masks`, `generate_set`, `export_terrain`. Routes `/api/terrain/generate` and `/api/terrain/export`.
- Projects save terrain A and B (`terra.png`, `terrb.png`); the set is regenerated on demand (deterministic).
- Tests: `tests/test_terrain.py` (61 checks) + 16 JS checks (same neighbour-bit fixtures as Python, map preview, request bodies). 353 checks in total.
