# Architecture

## Processes

```
Tauri window (src-tauri/, Rust, v2)  --spawns-->  python -m engine.main  (FastAPI + uvicorn, 127.0.0.1:8765, log: engine.log)
   shows http://127.0.0.1:8765  (GET / -> ui/index.html, /ui/* static)         |
browser mode (run.bat) = same engine, you open the URL yourself               +--spawns on demand--> llama-server (port 8766, log: llm.log)
```
`spriteforge.bat` sets up `.venv` (PyTorch cu128 + requirements), builds the Tauri shell once (falls back to browser mode without Rust), launches.
The Tauri app only starts/stops the engine (kills it on exit); all logic is in Python/JS. No CORS: the UI is served by the engine itself.

## Python modules (`engine/`)

| file | lines | summary (module docstring) |
|---|---|---|
| `engine/__init__.py` | 0 |  |
| `engine/diag.py` | 398 | Diagnostics: environment, GPU, model files, downloads, assistant, built-in self-tests and recent errors, |
| `engine/directions.py` | 93 | 4 / 8 direction characters. Only five views are needed (south, south-east, east, north-east, north): west, south-west and |
| `engine/exporter.py` | 305 | Export animation packs: one sprite sheet + atlas for any number of clips, with engine-ready files. |
| `engine/jobs.py` | 300 | Generation queue + history: one worker, jobs stored in history/<id>/ (settings, inputs, results), re-run / fork, pruning. |
| `engine/tiles.py` | 230 | Tiles and props: seamless tiles, pixel-level seam repair, tileset / atlas export (Godot 4 TileSet, Tiled .tsx). |
| `engine/terrain.py` | 250 | Autotile / terrain sets: 47-blob and 16-edge masks from one global shape, tile composition, lookup table, Godot 4 terrain `.tres` and Tiled wang-set export. |
| `engine/generate.py` | 223 | SDXL + pixel-art LoRA, optional IP-Adapter reference conditioning. Tuned for 8 GB VRAM. |
| `engine/llm.py` | 273 | Local assistant: loads a GGUF by running llama.cpp's llama-server (found in e.g. C:/AI) on demand, |
| `engine/main.py` | 918 |  |
| `engine/palettes.py` | 359 | Palette tools: import (.hex .gpl .pal / swatch PNG), your own palette library, remap with optional dithering, |
| `engine/pixelize.py` | 385 | Turn blurry AI 'pixel style' images into real pixel-grid sprites. No model dependency. |
| `engine/portrait.py` | 132 | Portrait expressions: repaint only a face-area mask of a pixel portrait (SDXL inpaint), keep everything else |
| `engine/projects.py` | 187 | Project save/load: one folder per character under <app>/projects/<name>/ |
| `engine/refine.py` | 94 | AI cleanup of rig-animated frames: repaint only small areas around moving joints (SDXL inpaint at low strength), |
| `engine/rig.py` | 458 | Rig-based sprite animation: assign pixels to bones, move bones with procedural clips, re-render. |
| `engine/templates.py` | 214 | Sprite templates: a neutral mannequin ("dummy") with a matching rig, and generation of a sprite that keeps the template's |

Dependency direction (no cycles): `main` imports everything; `generate`, `pixelize`, `palettes`, `rig`, `exporter`, `projects`, `diag`, `llm` are leaves or near-leaves;
`refine`, `portrait`, `templates`, `directions` build on `generate` / `pixelize` / `rig` / `exporter`.

## Conventions you must know

**Pixel coordinates are continuous**: pixel *i* spans [i, i+1); its centre is i+0.5. A joint at `x=12.4` lies in pixel `floor(12.4)=12`. Tests that use `round()` are wrong.
**Transparency**: alpha < 128 = transparent; every converter outputs alpha 0 or 255.
**Joints** (`rig.JOINTS`, 15): `head neck pelvis l_/r_shoulder l_/r_elbow l_/r_wrist l_/r_hip l_/r_knee l_/r_ankle`, each `[x, y]`. `l_`/`r_` are **screen** sides (screen-left/right at a front view), not anatomical.
**Bones** (`rig.BONES`, label index 0-9): `torso head l_arm_u l_arm_l r_arm_u r_arm_l l_leg_u l_leg_l r_leg_u r_leg_l`, each `(name, pivot joint, tip joint, parent, extends-past-tip, weight)`.
Pixel -> bone = nearest weighted bone segment (`assign_parts`), then **overrides** `[[x, y, label], ...]` (painted by the user, or exact from a dummy). Labels 10-12 = secondary parts `cape hair tail` (`rig.SEC_PARTS`).
**Rotation**: angles are clockwise-positive on screen (y down). Poses are written in *forward degrees*; `F = -1` when the sprite faces right, `+1` left (`_angles` converts). `dx/dy` are fractions of sprite height.
**Clips**: `rig.CLIPS` (11); `rig.ONE_SHOT` = play-once set (the rest loop: cyclic sim, seamless). `CLIP_PAD` = canvas margin (death is wide). `VIEW_SCALE` = walk/run variants for `side / diag / front` views.
**Render pipeline** (`rig.render`): per-bone layers upscaled x`ss` (nearest) -> pass 1 body poses (FK matrices) -> pass 2 secondary spring chains -> pass 3 affine-transform each layer, alpha-composite in z-order
(secondary parts behind the body unless "front") -> `_downsample`: palette index per hi-res pixel, **majority vote per cell** (no blended colours). Returns `(frames, meta)`; `meta = size, pad, pivot (feet), joints (per-frame moving-joint positions), secondary`.
**Exports** share a feet **pivot** and cell size (`exporter._align_and_crop`): frames from different clips/directions are padded around the integer-rounded pivot, optionally cropped to the union of visible pixels.
**Palettes**: `pixelize.PALETTES` (name -> (N,3) uint8) is the single registry; `palettes.load_into_px(root)` adds your saved palettes at startup and after save/delete. Anywhere a `palette` *name* is accepted, yours work.
**Models**: only **SDXL** single-file checkpoints work. `diag.inspect_file` classifies a `.safetensors` by header tensor names: checkpoints `sdxl / sd15 / dit / unknown / broken`, LoRAs `sdxl / unknown / other / broken`
(real SDXL files contain `transformer_blocks`; classify SDXL markers first!). The UI blocks `dit / sd15 / broken` checkpoints and `other / broken` LoRAs; `unknown` is allowed.

## Image generation (`generate.py`)

One pipeline is cached (key = checkpoint, LoRA, weight, mode flags); loading another rebuilds it. fp16, VAE tiling, scheduler swappable (`euler_a / dpmpp_2m_karras / euler`).
- txt2img: `StableDiffusionXLPipeline` + LoRA, **model CPU offload** (fits 8 GB). With a reference: + IP-Adapter (`h94/IP-Adapter`, downloaded once).
- Skeleton mode: `StableDiffusionXLControlNetPipeline` (OpenPose; local `controlnet/*openpose*xl*` else `xinsir/controlnet-openpose-sdxl-1.0`) with **sequential CPU offload** (UNet + ControlNet do not fit together in 8 GB).
- Inpaint: `StableDiffusionXLInpaintPipeline` (+ optional IP-Adapter) for AI joint cleanup, portrait expressions, template generation.
- Prompts: `build_prompt(kind)` for `sprite / portrait / expression`; negative prompts per kind. Failed runs drop the cached pipeline so retries start clean. All GPU work holds `_lock`.

## Pixel conversion (`pixelize.py`)

`pixelize(img, mode, size, colors, palette, ..., crisp=True, clean=True, outline="none")`, modes `fixed / auto / canvas`.
Crisp pipeline: remove background (border flood) -> crop -> `detect_grid` (edge-energy periodicity with a sub-harmonic check) -> palette (`smart_palette`: OKLab k-means whose entries are real colours of the image, or a given palette) ->
`crisp_reduce`: sample with nearest (never average), snap to palette in OKLab, **dominant colour per cell** -> ground-shadow removal -> `despeckle` -> optional outline -> blob clean-up. `crisp=False` = the old average-then-quantise converter (kept for comparison).

## Features by module

- **rig/refine**: AI joint cleanup masks discs around the *moving joints of each frame* (`meta["joints"]`), inpaints at low strength with a fixed seed, snaps to the sprite palette, **reverts** a frame whose silhouette changed too much; `redo_frames` redoes chosen frames from the cached raw frames.
- **portrait**: upscale the portrait with nearest onto 1024, inpaint only an ellipse mask, snap to the base palette (+ up to N *extra* colours found inside the mask), downsample with majority vote, paste only inside the mask. Streams one SSE event per expression.
- **templates**: `make_dummy(height, style, view)` draws neutral mannequins (`front back side diag diag_back`) and returns `(sprite, joints, overrides)` with an **exact** pixel->bone map. `generate_from_template` inpaints inside the silhouette (+`freedom` px ring) with the reference through IP-Adapter, picks a background colour far from the palette, keeps the template's exact size.
- **directions**: 5 unique views, `MIRROR` map for the rest, `VIEW`/`NEAR`/`DUMMY_VIEW`/`HINT` tables, `render_directions`, `export_directions` (names `<clip>_<dir>`).
- **palettes**: parsers (.hex .gpl .pal, swatch PNG), library, `remap` (none/bayer2/bayer4/floyd, OKLab), `merge_similar`, `variants` (OKLCH hue rotation with gamut-aware chroma reduction), `ramp`, `sort_colors`, exports.
- **exporter**: `export_pack(entries, opts, name, root)`; layouts rows/grid/column; Aseprite-style JSON; Godot 4 `SpriteFrames` `.tres` + `.tscn`; Unity JSON (Y flipped to bottom-left) + `SpriteForgeImporter.cs`; GIF/frames; README.
- **llm**: `Manager` starts `llama-server -m MODEL -c CTX -ngl N --host 127.0.0.1 --port P` on demand, waits for `/health`, streams `/v1/chat/completions`, idle-unloads. Security: only a file named `llama-server` and a `.gguf` can be configured.
  Assistant output protocol: `<set field="NAME">VALUE</set>` tags; the UI whitelists fields and shows Apply buttons.
- **diag**: structured checks (system, GPU incl. architecture-in-build test, models, downloads, assistant, config) + CPU self-tests + `ERRORS` ring buffer; `run_checks` also writes `diagnostics.txt`. `smoke_test` (in generate) and `Manager.selftest` back the two optional test buttons.

## Storage layout

```
projects/<name>/project.json    version, name, saved_at, settings{id: value}, rig, skeleton, anim_params, tab, palette, template, directions, has_ref, has_anim
                ref.png anim.png tpl.png tplref.png   reference sprite, rig source, template, template reference
                sprites/<timestamp>.png               "Save" on result cards
                results/<clip>/f_00.png r_00.png meta.json   reviewed AI-cleanup / edited frames (final, rig-only, accept flags)
                portrait/base.png e_<name>.png portrait.json
exports/<name>_pack/  or  <name>_<clip>/   sheet, atlas json, .tres/.tscn, _unity.json, importer .cs, gifs, frames/, README.txt, directions.json
history/<job>/job.json         queue + history: kind, params, ui snapshot, status, timings, results[{info}], fav, note; in_ref.png in_pose.png r<i>.png raw<i>.png
palettes/<name>.json            {"name","colors":["#rrggbb"...]}
config.json                     models_dir, port, llm_* (see config.example.json); a broken file is repaired (backslashes) rather than fatal
```
Project names are sanitised (letters, digits, space, `-`, `_`); every path is resolved and checked to stay inside `projects/` / `exports/` / `palettes/`. Saves are atomic (temp file + replace).

## The web UI (`ui/index.html`, one file, vanilla JS, no build step)

- Layout: `<aside>` sidebar (panels `p-*` shown per tab by `tab(n)`), `<main>` (cards: `rigcard portcard palcard tpcard dircard` + `#out` results), overlays (`#chat`, `#diag`, `#ped` pixel editor).
- **Settings persistence is automatic**: every `<input>/<select>/<textarea>` inside `<aside>` with an `id` (except file inputs, `pname`, `mdir`) is saved/restored by `collect()` / `applySettings()`. New controls inside the sidebar are saved for free; give them unique ids.
- Global state: `mode` (tab), `refURL`, `aSrc`+`joints`+`ovr` (rig source), `cur`/`ares` (animation results), `pts` (skeleton), `ED` (editor), `PL` (palette), `TP` (template), `DR` (directions), `ptBase/ptRes` (portrait), `modelKinds`.
- Helpers: `api(url, opt)` (throws with the server's `detail`), `plCall(fn)` (status + error wrapper), `render(results)` (result cards), `openEditor(url, {label, apply, onion})`, `checkModel()`, `markDirty()`, `loadImgs`, `clipParams(anim)`, `secObj()`, `xopts()`, `setAnim(url, {joints, ovr})`, `dl`, `saveSprite`.
- Streaming (chat, expressions) uses `fetch` + `ReadableStream` parsing `data: {json}\n\n` events.
- The pure pixel engine of the editor is the block between `/*PXE-START*/` and `/*PXE-END*/`; tests extract it from the file.

## HTTP API

All endpoints are plain `def` functions in `engine/main.py` (FastAPI, JSON or multipart). Errors: `400` = user/input error with a readable `detail`, `500` = internal/model error (OOM gets a hint).
HTTP errors are recorded in `diag.ERRORS` for the diagnostics report.

| method | path | function | summary |
|---|---|---|---|
| `GET` | `/` | `index` |  |
| `POST` | `/api/config` | `set_cfg` |  |
| `GET` | `/api/diag` | `diag_run` |  |
| `POST` | `/api/diag/gpu_test` | `diag_gpu_test` |  |
| `POST` | `/api/diag/llm_test` | `diag_llm_test` |  |
| `POST` | `/api/dirs/export` | `dirs_export` |  |
| `POST` | `/api/dirs/generate` | `dirs_generate` | Generate the needed views from view-specific dummies with ONE reference, seed and palette, so they match each other. |
| `POST` | `/api/dirs/render` | `dirs_render` | Preview: one clip for every direction (west / south-west / north-west are mirrors of their east views). |
| `POST` | `/api/generate` | `generate_ep` |  |
| `POST` | `/api/llm/chat` | `llm_chat` |  |
| `POST` | `/api/llm/config` | `llm_config` |  |
| `POST` | `/api/llm/start` | `llm_start` |  |
| `GET` | `/api/llm/state` | `llm_state` |  |
| `POST` | `/api/llm/stop` | `llm_stop` |  |
| `GET` | `/api/palettes` | `pal_list` |  |
| `POST` | `/api/palettes/export` | `pal_export` |  |
| `POST` | `/api/palettes/extract` | `pal_extract` |  |
| `POST` | `/api/palettes/merge` | `pal_merge` |  |
| `POST` | `/api/palettes/parse` | `pal_parse` |  |
| `POST` | `/api/palettes/ramp` | `pal_ramp` |  |
| `POST` | `/api/palettes/remap` | `pal_remap` |  |
| `POST` | `/api/palettes/save` | `pal_save` |  |
| `POST` | `/api/palettes/sort` | `pal_sort` |  |
| `POST` | `/api/palettes/variants` | `pal_variants` |  |
| `DELETE` | `/api/palettes/{name}` | `pal_delete` |  |
| `POST` | `/api/pixelize` | `pixelize_ep` |  |
| `POST` | `/api/portrait/base` | `portrait_base` |  |
| `POST` | `/api/portrait/export` | `portrait_export` | Individual PNGs + one sheet + Godot SpriteFrames (one 1-frame animation per expression) + Unity importer data. |
| `POST` | `/api/portrait/expressions` | `portrait_expressions` |  |
| `GET` | `/api/projects` | `projects_list` |  |
| `POST` | `/api/projects/save` | `projects_save` |  |
| `DELETE` | `/api/projects/{name}` | `projects_delete` |  |
| `GET` | `/api/projects/{name}` | `projects_load` |  |
| `GET` | `/api/projects/{name}/sprites` | `projects_sprites` |  |
| `POST` | `/api/projects/{name}/sprites` | `projects_add_sprite` |  |
| `DELETE` | `/api/projects/{name}/sprites/{sid}` | `projects_del_sprite` |  |
| `POST` | `/api/tiles/seamless` | `tiles_seamless` | make a pixel tile seamless without new colours |
| `POST` | `/api/tiles/offset` | `tiles_offset` | wrap-around shift (default half) |
| `POST` | `/api/tiles/export` | `tiles_export` | tileset grid sheet + .tres + .tsx, or packed atlas |
| `POST` | `/api/tiles/repair` | `tiles_repair` | AI seam repair: inpaint only the half-shifted seam cross |
| `POST` | `/api/tiles/animate` | `tiles_animate` | loop-perfect frames of a tile (scroll / ripple / shimmer) |
| `POST` | `/api/tiles/export_anim` | `tiles_export_anim` | strip + GIF + Godot / Tiled animation files |
| `POST` | `/api/terrain/generate` | `terrain_generate` | 47 / 16 autotile tiles from terrain A (+ ground B), with lookup |
| `POST` | `/api/terrain/export` | `terrain_export` | sheet + terrain.json + Godot terrain .tres + Tiled wang .tsx |
| `POST` | `/api/queue/add` | `queue_add` | queue a generate / reference job ({kind, params, ui, images}) |
| `GET` | `/api/queue` | `queue_state` | waiting + running jobs, paused flag |
| `POST` | `/api/queue/pause` | `queue_pause` | {paused: bool} |
| `POST` | `/api/queue/cancel_all` | `queue_cancel_all` | cancel every waiting job |
| `GET` | `/api/history` | `history_list` | finished jobs (limit, offset, fav, q, kind) with thumbnails |
| `POST` | `/api/history/clear` | `history_clear` | delete history (favourites kept by default) |
| `GET` | `/api/jobs/{jid}` | `job_get` | one job with params, ui snapshot, inputs and results |
| `POST` | `/api/jobs/{jid}/cancel` | `job_cancel` | |
| `POST` | `/api/jobs/{jid}/meta` | `job_meta` | {fav, note} |
| `POST` | `/api/jobs/{jid}/rerun` | `job_rerun` | {new_seed: bool} |
| `DELETE` | `/api/jobs/{jid}` | `job_delete` | |
| `POST` | `/api/reference` | `reference_ep` |  |
| `POST` | `/api/rig/animate` | `rig_animate` |  |
| `POST` | `/api/rig/autoplace` | `rig_autoplace` |  |
| `POST` | `/api/rig/export_frames` | `rig_export_frames` | Export exactly the frames the user chose (e.g. AI where it helped, rig-only where it didn't). |
| `POST` | `/api/rig/export_pack` | `rig_export_pack` | One sprite sheet + atlas (+ Godot / Unity files) for one or many clips, sharing a feet pivot. |
| `POST` | `/api/rig/parts` | `rig_parts` |  |
| `POST` | `/api/rig/redo` | `rig_redo` |  |
| `GET` | `/api/state` | `state` |  |
| `GET` | `/api/template/dummy` | `template_dummy` |  |
| `POST` | `/api/template/generate` | `template_generate` |  |
