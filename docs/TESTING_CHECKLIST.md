# Manual test checklist (needs the real GPU)

Automated tests (`python tests/run_all.py`) cannot run SDXL. This list is ordered fast -> slow. For any failure send: a screenshot, the red status line, `engine.log` (tail), and the **Diagnostics > Copy report** text.

| # | Test | Expected | If it fails |
|---|---|---|---|
| 0 | Update to the latest build, relaunch, open **🩺 Diagnostics > Run checks** | no FAIL rows; models tagged correctly (sd_xl_base_1.0 and the pixel LoRA have no warning tag) | send the report |
| 1 | Diagnostics **GPU test** | finishes in ~1-2 min, peak VRAM < your total | send the result row |
| 2 | **Generate**, default prompt, Variations 1 | a sprite appears; try again with the same seed: *Crisp conversion* on vs off, sampler Euler a vs DPM++ | screenshot of both |
| 3 | **Edit** a result: pencil, fill, recolor, undo, Apply | pixels change; Apply updates the card | screenshot |
| 4 | **Palette**: From image, import a Lospec `.hex`, Save, Remap with Bayer 4x4, Make variants | variants keep shading; saved palette appears in *Fixed palette* | screenshot |
| 5 | **Animate**: Animate button on a sprite, drag joints, Preview walk / run / attack / death | clean frames, no gaps at joints | screenshot of the frame strip |
| 6 | **Secondary motion**: paint a cape or hair, Preview run | it trails and settles; idle sways gently | screenshot |
| 7 | **Export current animation** and **pack** (idle + walk) | files in `exports/`; open the `.tscn` in **Godot 4**; run the importer in **Unity** | the engine's import error text |
| 8 | **AI joint cleanup** on a short walk (4-6 frames) | takes minutes; review, untick, Redo, Export | status line + `engine.log` |
| 9 | **Reference pose** with skeleton, 1 variation | OOM-free; pose roughly followed (identity may drift: known limit) | the status line |
| 10 | **Portrait**: base, then 4 expressions | only the face area changes | screenshot |
| 11 | **Template**: Make dummy (64, normal, front), set a reference image, Generate | same size as the dummy; silhouette respected; **Animate (template rig)** opens with the rig | screenshot of result + raw |
| 12 | **Directions**: Generate all views (5 calls, several minutes), Preview walk, Export | 8 directions in a compass; sheet with rows; names `walk_s` ... | which view looks wrong |
| 13 | **Assistant**: Scan, pick model, ask for a prompt, press Apply | reply streams; Apply fills the field | `llm.log` |
| 14 | **Projects**: Save, close the app, relaunch | last project reopens with settings, rig, results, directions | what is missing |
| 15 | **Queue**: press **＋ Add to queue** 3 times with different prompts (Variations 2), open the **Queue** tab | jobs run in order, progress "image 1 of 2"; finished ones appear in History; Pause / Cancel work | screenshot of the Queue tab; the status line on any error |
| 16 | **History**: open a card, **Use these settings**, **Fork**, ★, tick two cards and **Compare** | settings come back (also the skeleton for a Reference job); fork gives a new variation | what is wrong or missing |
| 17 | **Tiles & props**: kind = Seamless tile, size 32, 4 variations; on a good one press **To tileset**, look at the 3x3 repeat, **Offset 1/2**, then **Make seamless**; add 3-4 tiles, **Random map preview**, **Export tileset** | tile is exactly 32x32, repeats without a visible join; files appear in `exports/<name>_tileset/`; open the `.tres` in **Godot 4** and the `.tsx` in **Tiled** | screenshot of the workbench + the engine's import error if any |
| 18 | **Props / icons / UI**: kind = Item icon (red health potion), then Prop, then UI element | one centred object, background removed, outline option works | screenshot |
| 19 | **Terrain set**: two seamless tiles (grass, dirt) -> **Use as A / B** -> **Generate set** -> **Autotile map preview** -> **Export terrain set** | 47 tiles, the preview map has no visible joins; open the `.tres` in **Godot 4**: TileSet > Terrains shows a terrain, painting with it picks the right tiles; the `.tsx` in **Tiled** shows the wang set | screenshot of the preview + any Godot/Tiled error |
| 20 | **Corner / multi sets**: set type *16-tile corners*, then *Multi-terrain* with grass, dirt, water; **Generate**, **map preview**, **Export**; open the `.tres` in **Godot 4** (Terrains tab) and the `.tsx` in **Tiled** | the preview map has no visible joins; painting in Godot / Tiled picks sensible tiles (multi in Godot is best effort: report what happens) | screenshot of the preview and of the Godot / Tiled painting |
| 21 | **Animated tile**: workbench tile -> Ripple, 8 frames -> **Make frames**, then **Export animated tile** | smooth loop; the `.tres` in Godot plays the animation, the `.tsx` in Tiled shows it | a screenshot / what Godot says |
| 22 | **AI repair seams** on a tile with a visible join; also tick **solid** on a tile and export the tileset | the join is gone after repair (press again for another seed); the solid tile has a collision square in Godot / Tiled | before / after screenshot |

Things worth judging by eye (quality, not bugs): the crisp converter vs the old one; three-quarter dummies/views; how consistent the generated directions are; cape physics feel (Flutter / Stiffness / Damping).


## Phase 61K-G — reference editing acceptance (not yet performed on hardware)

For each installed Qwen Rapid, NetaYume and compatible SDXL checkpoint, start with one candidate at 640 or 768 resolution using the backend defaults. Record model, resolution, elapsed time, peak device memory if measured, and visible quality. Test outfit replacement, wing addition, regional removal, protected RGBA comparison and contrasting background cleanup. Verify undo/redo, discard, staging and explicit approval in Studio and Modular. Save and reload the project; approved assets must persist, staged history must not. Verify a failed or OOM edit leaves the source untouched and a smaller retry works. Compare resource status before/after; no claim of peak VRAM savings without measurement. Confirm existing rig source is retained until explicitly replaced. Test brush drag at 1024 px and inspect responsiveness and seams.

## Phase 61L-G — alpha cleanup desktop acceptance (pending)

Use pixel sprites at 64–160 px and HD artwork at 512–1024 px. Test white, green, gray and transparent backgrounds, enclosed gaps, opaque/translucent ground shadows, white clothing and dark boots. Paint protection, run automatic cleanup, refine the current preview, wand/erase/restore, undo and reset. Verify overlay never appears in PNG; compare protected server RGBA, inspect partial-alpha browser round trips. Test fast pointer strokes, cancellation, repeated previews and history eviction on 1024 px. Record elapsed preview time and process memory if measured; compare before/after on identical input. Verify staged approval, stale source guards, project reload and same-size modular replacement retains position and settings. No GPU inference expected. Do not treat CPU CI as desktop acceptance.

## Phase 61M-G — exact-fit modular acceptance (not yet performed on hardware)

For Qwen Rapid, NetaYume and compatible SDXL, use the same non-square body canvas and seed where applicable. Test pixel and HD body bases, front/side/back/three-quarter and asymmetric poses. Generate fringe, rear hair, coat, armor, boots, left/right weapon, wings and cape using both isolated fitting and supported extraction. Start with one candidate at 640; repeat at 768/1024 when supported. Record model, settings, elapsed time, peak RAM/VRAM if measured, and actual fit quality. Inspect unchanged body, leaked anatomy, missed same-color fabric, shadow and hidden rear portions. Verify guide overlay, depth, attachments, cleanup cancel/apply, alignment preview, reset, stale candidate rejection, independent and registered PNG dimensions, category replacement toggle, save/reload and rig motion. Test off-canvas warning, budget rejection, concurrent edit and failed inference recovery; confirm source recipe unchanged. No automatic inference fallback. Record desktop and GPU outcomes separately from CPU CI.

## Phase 61N-D — Generate acceptance (hardware/desktop not yet verified)

Start with a new project and verify neutral empty Generate, Character Studio and template subject defaults. On an existing project, inspect saved user prompts and remove unwanted legacy example text manually. Select each of the 13 styles; verify the prompt inspector contains only intended style wording, separate subject and mode guidance, expected background and negatives. For SDXL, NetaYume and Qwen, test a clothed adult character and a non-explicit featureless mannequin body base in pixel and HD styles; compare fixed seed/settings with and without a compatible LoRA. Check armor/cape leaks and unwanted equipment visually, not just prompt text. Test all six head-height styles on adult stylized figures or featureless mannequins; measure approximate standing height/head height and record actual ratio, not a pass guarantee. Inspect prompt after style, background, model, LoRA and subject changes; load a different saved project during preview; verify history restore, queue retry, batch capture, old settings defaults, and HD output. Record model, LoRA, seed, settings, actual output and failures. CPU mocked routing does not establish real model compliance or quality.

## Phase 61O — WebP export

Choose WebP in Image download format and download a generated sprite, editor selection (1x/8x), character master, modular layer/registered asset/composite, and a map image. Confirm actual .webp files open, dimensions, alpha and crisp nearest-neighbor scaling match PNG. Compare file sizes on representative pixel and HD art; WebP may be larger for tiny palettes. Switch to PNG and verify the existing filenames and image content. Save/reopen project to verify selection; old projects use PNG. Export game-engine packs and confirm PNG/GIF paths are unchanged. Test unavailable encoder error if applicable. Desktop acceptance pending.

## Phase 61P-A — Standalone VFX Studio

Open VFX Studio without a model or actor. Select each built-in effect, change color/radius/FPS/duration/seed, render, scrub, play and stop; compare pixel and smooth sampling. Confirm changing fields invalidates stale previews; leaving the workspace stops playback. Save/load/delete a custom preset, reload the app, export/import a recipe JSON and reject malformed inputs. Download one frame in PNG and WebP. Export a fixed-canvas sprite sheet, individual PNGs, GIF and metadata; check transparent alpha and playback. Insert into a scene with sufficient duration; verify insufficient duration is reported and scene data remains unchanged. CPU and desktop acceptance pending; automated Actions paused.
