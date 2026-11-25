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
