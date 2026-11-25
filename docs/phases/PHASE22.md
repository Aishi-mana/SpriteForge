# Phase 22 - tile follow-ups
Unzip over your spriteforge folder. New: tests/test_tilefx.py. Changed: engine/terrain.py, engine/tiles.py, engine/main.py, engine/projects.py, ui/index.html, tests/js/queue_test.js, docs.
No packages, no rebuild: restart the engine / relaunch spriteforge.bat. All on the **Tiles & props** tab.

## 1. Corner sets and multi-terrain sets (Terrain set card)
Two new *Set types*:
- **16-tile corners (dual grid, A + B)**: a tile is chosen by the terrain at its four corners. B is optional (transparent without it).
- **Multi-terrain corners**: 3 or 4 terrains (A, B, C, optional D) with every combination: **81 or 256 tiles**, so any painting of grass / dirt / water / snow has a tile. Slots C and D appear when you choose it.
Terrain names go in one box ("Grass, Dirt, Water, Snow"). *Corner rounding* means edge softness for these sets (0 = hard edges).
Same exactness as before: every tile is the crop of one global result (finite Gaussian per terrain + "largest wins"), tested against whole random maps with 2 and 3 terrains (zero differing pixels, rim included).
The map preview paints a random corner map with the set. Export: sheet, `terrain.json` (the four corner terrains of every tile, index = ((nw*N+ne)*N+se)*N+sw), **Godot 4 `.tres`** (match-corners terrain set), **Tiled corner wang set** (all colours, all combinations).
- 16-tile: ONE Godot terrain (A) over any base, the standard setup; tiles keep bits only on A's corners.
- Multi-terrain in Godot: terrains are declared and every tile carries each corner's terrain; a mixed tile's own terrain is its most common corner terrain. How Godot 4 chooses among mixed tiles while painting is **best effort and untested**: please try the Terrains tab and tell me what happens. Tiled's wang sets are unambiguous.

## 2. Animated tiles (new card + sidebar "Animated tile")
From the workbench tile: **Scroll** (conveyor, flowing water: wraps by 1/frames of the size per frame), **Ripple** (water: rows shifted sideways by a sine), **Shimmer** (a share of pixels steps to the next lighter / darker colour of the tile and back: sparkle, lava).
2-32 frames, ms per frame, amount. All loops are exact and **no new colours** are created. Looping preview in the card. **Export animated tile** writes `exports/<name>_anim/`: horizontal strip, preview GIF, `animation.json`, Godot 4 `.tres` with the animated tile (frame durations), Tiled `.tsx` with an animation, README.

## 3. Collision shapes
Every tileset thumbnail has a **solid** tick. The tileset export then adds a full-tile collision polygon on physics layer 0 in the Godot `.tres` and a collision rectangle in the Tiled `.tsx` for those tiles (and `"solid"` in `tileset.json`). Saved with the project.

## 4. AI seam repair (workbench button)
For tiles with a visible join (including ghosting from Make seamless): the tile is shifted by half, the AI inpaints **only the middle cross** (width = *Cross width %*, strength = *Strength*, your prompt + the tile template), and everything outside the cross is kept pixel for pixel.
The borders of the shifted tile are untouched and already continuous, so the result is seamless whatever the AI paints; the AI output is snapped to the tile's own palette. Seam score before / after is shown. Press again for another seed.

## Limits / honest notes
- AI seam repair, like all SDXL steps, could only be tested with a fake model here (mask geometry, kept pixels, palette, seam improvement with a smoothing stand-in). Real quality depends on the checkpoint; GPU load is one inpaint (like the Portrait tool).
- Multi-terrain painting rules in Godot (see above) are best effort. Corner sets need an even tile size (8-128).
- Collision is a full square only (no polygons from the art, no navigation shapes). Terrain tiles have no collision.
- Not verified here (no Godot / Tiled / browser): the animation property names in the `.tres` (`animation_frame_N/duration`), the physics polygon lines, how the new cards look.

## Technical
- `terrain.py`: `generate_corner`, `export_corner`, `corner_index`, `corner_tile_classes`. `tiles.py`: `animate_tile`, `export_animated`, `repair_seams`, collision output. Routes: `/api/tiles/repair`, `/api/tiles/animate`, `/api/tiles/export_anim`; `/api/terrain/*` accept `kind = corner16 | multi`, `c`, `d`, `names`.
- Found while testing: `main.py` now imports numpy at module level (the repair endpoint used it for random seeds).
- Tests: `tests/test_tilefx.py` (82 checks) + 21 more JS checks. 435 checks in total.
