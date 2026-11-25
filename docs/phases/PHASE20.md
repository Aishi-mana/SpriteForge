# Phase 20 - tiles and props
Unzip over your spriteforge folder. New: engine/tiles.py, tests/test_tiles.py. Changed: engine/main.py, engine/generate.py, engine/projects.py, engine/jobs.py, ui/index.html, tests/js/queue_test.js, docs.
No packages, no rebuild: restart the engine / relaunch spriteforge.bat.

## New tab: Tiles & props
**Sidebar**: *What to make* - **Seamless tile**, **Prop**, **Item icon**, **UI element** - prompt (an example is filled in for each kind; your own text is never overwritten),
size (16-128 px; for tiles it is the tile side, for the others the long side), colours, variations, fixed palette, *Make seamless*, outline (props/icons/UI only),
plus the usual checkpoint / LoRA / seed / steps / sampler block. **Generate** and **+ Add to queue** work like on the Generate tab (history, re-run, fork, compare included; the history labels them Tile / Prop / Icon / UI).

**Seamless tiles.** SDXL draws a flat top-down texture; the picture is made seamless *before* it is turned into pixels (shifted by half, the original blended back in the middle with a weight that is exactly 0 on all four borders),
then reduced onto an exact size x size grid. No background removal, crop, outline or despeckle on tiles, because each of those would break the wrap-around join.
The card shows a **seam score** (about 1 = as smooth as the inside of the tile, much more = visible join). Switch *Make seamless* off to see the raw difference.

**Workbench** (card at the top; press **To tileset** under any result, or load an image):
- the tile repeated 2x2 / 3x3 / 4x4 at your zoom, to judge the pattern;
- **Offset 1/2 (show seams)**: shifts with wrap-around so the old edges sit in the middle (press again to undo); **Edit** opens the pixel editor so you can paint over a join;
- **Make seamless** for any pixel tile (also hand-painted or uploaded ones): every pixel is *picked* from the tile or its half-shifted copy through an ordered-dither mask, so **no new colours** appear and the palette stays exactly the same.
- **Add to tileset** (with a name).

**Tileset**: thumbnails (click one to edit it again, < > reorder, x remove, rename), **Random map preview** (a 14x8 map from random tiles: joins show up immediately), **Export tileset**.
Export writes `exports/<name>_tileset/`:
- equal-sized tiles -> one grid sheet (`columns`, `spacing`, `margin`) + `tileset.json` + **Godot 4 TileSet `.tres`** (atlas source with every tile registered) + **Tiled `.tsx`** + README (Unity: Slice > Grid By Cell Size, with the numbers);
- different sizes (props, icons, UI) -> a packed **atlas** + `atlas.json` (regions per name).
The tileset and the workbench tile are saved with the project.

## Limits / honest notes
- Seamlessness is a blend of the AI picture with its shifted copy: it guarantees a continuous join, but the middle of a tile can show a faint "ghost" where the two copies mix. Large-scale patterns (bricks, planks) suffer more than noisy ones (grass, sand, stone). Edit / Offset helps for the last bit.
- No autotile / terrain (47-tile blob) generation yet: you get free-standing seamless tiles; combine them yourself in Godot / Tiled.
- The AI has no layout control for props; "single object" depends on the prompt. Icons and UI elements are the same pipeline as sprites with different prompt templates.
- Not verified here (no GPU / browser): real SDXL tile quality, how the tab looks, the `.tres` / `.tsx` opened in Godot 4 / Tiled (the files follow the formats those tools write, and are structure-tested).

## Technical
- `engine/tiles.py`: `make_seamless`, `seamless_pixels`, `seam_score`, `wrap_offset`, `tile_post`, `export_tileset` (+ shelf packer).
- `generate.py`: prompt templates and negatives for `tile / prop / icon / ui` (`negative_for(kind)`; sprite and portrait behaviour unchanged).
- `main.py`: `GenParams.kind / seamless`, routes `/api/tiles/seamless`, `/api/tiles/offset`, `/api/tiles/export`. `projects.py`: `tileset/` folder + `tile.png`. `jobs.py`: summary `sub` (generate-job kind).
- Tests: `tests/test_tiles.py` (46 checks: seam maths on realistic textures, no-new-colours, odd sizes, border continuity, generation with a fake SDXL, Godot/Tiled/atlas output, hostile names, projects, queue) and 16 more JS checks. 292 checks in total.
