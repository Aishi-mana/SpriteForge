# Changelog

Each phase was delivered as a zip containing only the changed files. Full per-phase notes are in `docs/phases/`. Phase 1 (skeleton, txt2img, pixelize) predates the notes.

## Phase 1 - skeleton, pixelize, text-to-sprite
FastAPI engine + browser UI, SDXL + pixel-art LoRA, background removal, grid detection, palette quantise, PNG export.

## Phase 2 - reference pose + Tauri shell
Unzip over your existing spriteforge folder (config.json is NOT included, yours is kept).
Launch with spriteforge.bat (run.bat still works for browser-only mode).
Use "spriteforge.bat rebuild" after changing anything in src-tauri/.
Reference mode downloads the SDXL IP-Adapter from Hugging Face on first use (~3 GB), then works offline.

## Phase 3 - skeleton pose editor + ControlNet + fixed canvas
Unzip over your spriteforge folder (no Rust changes, no rebuild needed). Keep your config.json.
Reference pose tab -> "Use skeleton pose" (on by default):
- Pick a preset, drag joints (Shift+drag moves everything), Mirror flips left/right.
- Use the "Stand" preset to line the skeleton up over your reference (shown faintly), then keep the scale for all poses.
- Output is a fixed square canvas (default 128 px) at one constant scale, so frames line up.
- Local ControlNet: put an SDXL OpenPose file with "openpose" and "xl" in its name in <models>/controlnet.
  Otherwise xinsir/controlnet-openpose-sdxl-1.0 downloads once from Hugging Face.
- "Remove ground shadow" strips the grey blob under feet (untick it if it eats real boots).

## Phase 3.1 - fix OOM in skeleton mode
Skeleton mode now uses sequential CPU offload (UNet + ControlNet don't fit together in 8 GB).
New "Generation size" option (default 768). Failed runs reset the pipeline so retries start clean.

## Phase 4 - rig-based animation
Unzip over your spriteforge folder (new: engine/rig.py; changed: engine/main.py, ui/index.html). No Rust changes, no new pip packages.
Animate tab:
1. Press "Animate" under any sprite result (or upload a sprite).
2. Joints are auto-placed from the sprite's bounding box. Drag them onto the real body: head top, neck, pelvis, shoulders/elbows/wrists, hips/knees/ankles.
   Part colors show which bone each pixel follows. "l_" = screen-left, "r_" = screen-right.
3. Fix mistakes (sword assigned to the head, cape on the arm...): choose the right part, tick Paint mode, drag over those pixels.
4. Pick idle / walk / run / attack / jump, set facing, press Preview. Export writes to <project>/exports/<name>_<anim>/:
   sheet PNG, atlas JSON (Aseprite-style hash + pivot at the feet), GIF (4x) and individual frames.
Best on side-view characters (walk/run/attack). Idle and jump also work front-on.

## Phase 5 - AI joint cleanup
Unzip over your spriteforge folder. New: engine/refine.py. Changed: engine/rig.py, engine/generate.py, engine/main.py, ui/index.html.
No new packages. No Rust rebuild.
Animate tab -> tick "AI joint cleanup", describe the character, press Preview.
- Only small discs around moving joints (shoulders, elbows, hips, knees, neck, pelvis) are repainted; everything else is untouched.
- SDXL inpaint + your pixel LoRA at low strength (default 0.45), same seed for every frame, then snapped to the sprite's own palette.
- Safety net: if the AI changes too much in a frame, that frame silently keeps the rig-only version (reported in the status line).
- "Show before cleanup" toggles the preview; the strip shows before/after rows.
- Export right after Preview reuses the cleaned frames (no second AI pass).
Limits: frames must be <= 256 px (sprite + padding). Expect roughly 20-60 s per frame on 8 GB.

## Phase 6 - projects (save / load)
Unzip over your spriteforge folder. New: engine/projects.py. Changed: engine/main.py, ui/index.html. No packages, no rebuild.
Top of the sidebar: Project name + Save / Load / Delete (Delete needs a second click).
Saved in <app>/projects/<name>/ : project.json (every setting, per-animation params, rig joints, paint, skeleton pose),
ref.png (reference sprite), anim.png (rig source sprite), sprites/ (results you pressed "Save" on).
- "Save" under any result stores that sprite in the project; the gallery at the bottom has Ref / Anim / x buttons.
- Autosaves every 20 s once the project has been saved once. Reopens your last project on startup.
- Each animation (idle, walk, ...) remembers its own frames / fps / amplitude / facing settings.
- Exports go to <app>/exports/<project>_<anim>/ (export name defaults to the project name).
Project folders are plain files: copy a folder to back it up or move it to another machine.

## Phase 7 - review & reuse AI cleanup results
Unzip over your spriteforge folder. Changed: engine/refine.py, engine/rig.py, engine/projects.py, engine/main.py, ui/index.html. No packages, no rebuild.
Animate tab, after a Preview with "AI joint cleanup":
- Under every frame is an "AI" tick. Untick it to keep that frame's rig-only version (red outline). "AI all" / "Rig all" flip everything.
- Frames the AI changed too much are pre-unticked automatically.
- "Redo unticked frames (new seed)" re-runs the AI only for those frames and merges the results back (needs the live result, i.e. same session).
- "Highlight what the AI changed" paints changed pixels magenta on the preview. "Show before cleanup" plays the rig-only version.
- Onion skin (works for any animation) shows the previous/next frame faintly. Click a frame to pause and inspect it.
- Export writes exactly the frames you chose (AI + rig-only mix) through /api/rig/export_frames, with no second AI pass.
- Cleaned results are saved inside the project (per animation) and come back when you load it, ready to review and export.

## Phase 8 - six new clips
Unzip over your spriteforge folder. Changed: engine/rig.py, ui/index.html. No packages, no rebuild.
New in the Animate tab's animation list:
  Loops:      climb, cheer          (plus idle, walk, run)
  Play once:  cast, block, hurt, death  (plus attack, jump)
- hurt:  flinch backward and recover (6 frames).
- death: stagger, knees buckle, topples backward and ends lying flat (10 frames). New whole-body tilt about the feet; canvas auto-pads wide.
- cast:  charge with arms overhead, thrust forward, hold, return. Uses the Weapon-arm setting.
- block: crouch into a guard with the weapon arm raised, hold, return. Uses the Weapon-arm setting.
- climb: alternating arm reaches and knee lifts (best on a front or back view; set "Nearer limbs" to both).
- cheer: both arms up with small hops.
Each clip remembers its own frames/fps defaults. The atlas JSON now has meta.loop (true/false) so engines know whether to repeat it.

## Phase 9 - export layouts (Godot 4, Unity, Aseprite/Phaser)
Unzip over your spriteforge folder. New: engine/exporter.py. Changed: engine/main.py, ui/index.html. No packages, no rebuild.
Animate tab -> Export section:
- "Export current animation" or "Export pack (ticked animations)": one sheet + atlas for any set of clips.
- Layout: one row per animation / grid (columns) / single column, frame padding, power-of-two option.
- Shared cell size + shared feet pivot for every clip, optionally cropped to the visible content (pivot stays valid).
- AI-cleaned frames (with your accept/reject choices) are used automatically when "Use AI-cleaned frames" is ticked.
Output: <app>/exports/<name>_pack/  (or <name>_<anim>/ for a single clip)
  <name>_sheet.png            sprite sheet
  <name>_atlas.json           Aseprite-style JSON hash (frameTags with fps + loop, per-frame pivot) - also loads in Phaser
  <name>.tres / <name>.tscn   Godot 4 SpriteFrames (all animations, loop + speed) and a ready AnimatedSprite2D scene (feet origin, nearest filter)
  <name>_unity.json + SpriteForgeImporter.cs   Unity: select the json, Assets > SpriteForge > Import Sprite Sheet -> slices sprites (pivot = feet) and creates one .anim per clip
  <name>_<anim>.gif           previews (optional), frames/ (optional), README.txt with the steps
Not tested inside Godot/Unity (no engines in the build environment): report any import errors and they will be fixed.

## Phase 10 - local assistant chat (GGUF via llama.cpp)
Unzip over your spriteforge folder. New: engine/llm.py. Changed: engine/main.py, ui/index.html. No packages, no rebuild.
Needs llama.cpp's llama-server (llama-server.exe) and a chat .gguf somewhere under C:/AI (the folder is scanned 4 levels deep).
1. Press "✦ Assistant" (bottom-right), open the gear, press Scan, pick a model, Save.
2. First message starts llama-server on port 8766 (CPU by default, so SDXL keeps all the VRAM); it unloads itself after 10 idle minutes.
3. The assistant answers with prompts and settings; each proposed change is an "Apply" button. It never generates or exports by itself.
Fields it can set: prompt, negative, character, pose, anim, reference / skeleton / cleanup strength.
It sees your current tab, prompt, character, pose text, animation and checkpoint/LoRA names.
Settings (server path, model, GPU layers, context, idle minutes, scan folder) are stored in config.json. Log: llm.log.
Safety: only a file named llama-server and a .gguf model can be configured.
Suggested models: any 3-4B instruct model at Q4 (e.g. Qwen2.5-3B-Instruct, Llama-3.2-3B-Instruct, Phi-3.5-mini).

## Phase 11 - portrait maker + expressions
Unzip over your spriteforge folder. New: engine/portrait.py. Changed: engine/generate.py, engine/main.py, engine/projects.py, engine/llm.py, ui/index.html. No packages, no rebuild.
New "Portrait" tab:
1. Base portrait: describe the face / hair / eyes / collar. "Start from" = Text only, or your Reference sprite via IP-Adapter
   (set it in the Reference tab first). Pick size (64-256), colours and background, press Generate base portrait, then "Use as base".
2. Face area: pick a preset (whole face / eyes + brows / mouth) or drag on the portrait to draw your own area. Only this area is repainted.
3. Tick expressions (happy, sad, angry, surprised, embarrassed, smug, sleepy, pain, scared, determined, laughing, serious) and/or type your own,
   press Generate expressions. They appear one by one as they finish (SDXL inpaint, same seed for all, with your pixel LoRA).
   - Everything outside the face area stays pixel-identical to the base.
   - Results snap to the base palette; "Extra colors allowed" (default 4) lets blush, tears, sweat drops keep their own colours.
   - "Change strength" (default 0.82): higher = bigger expression change, lower = closer to the base face.
4. "Base" button on any expression continues from it; "x" removes it; PNG downloads one.
5. Export portrait set: individual PNGs + one sheet + Aseprite-style JSON + Godot 4 .tres/.tscn (one animation per expression, e.g. play("happy"))
   + Unity json + importer script, into <app>/exports/<name>_portraits_pack/.
The base portrait, face area and all expressions are saved in the project. The assistant can also fill the portrait prompt and a custom expression.

## Phase 12 - quality pass (crisp conversion, grid snap, palette, outline, sampler)
Unzip over your spriteforge folder. Changed: engine/pixelize.py, engine/generate.py, engine/main.py, ui/index.html. No packages, no rebuild.
What was wrong: the old converter AVERAGED pixels (blending colours at every edge) and then built a palette from those blends.
It also ignored the 8 px grid the pixel-art LoRA draws on. Result: muddy colours, lost small details, speckled/dithered skin.
Now (on by default, "Crisp conversion" checkbox):
- Snaps to the real pixel grid first when one is found (also fixed a bug where clean upscales were detected at half the true grid).
- Picks the palette with perceptual (OKLab) clustering over the image's own colours: small distinct colours (emblems, gems) survive.
- Converts by quantising first, then taking the DOMINANT colour of each cell: no in-between shades are ever created.
- Clean stray pixels: removes single dither/noise pixels that almost match their surroundings (real highlights are kept).
- Outline: none / selective (darkened edge colour) / dark. Added as a 1 px ring (canvas-mode frames keep their size).
- Works for Generate, Reference pose, Pixelize and Portrait. Untick "Crisp conversion" to get the old behaviour for comparison.
- Sampler dropdown (Euler a / DPM++ 2M Karras / Euler): keep the same seed and compare.
Measured on a known test image (blur + noise): old converter 67-84 % of pixels correct, new 97-99.8 %, even at 8 colours.

## Phase 13 - diagnostics
Unzip over your spriteforge folder. New: engine/diag.py. Changed: engine/generate.py, engine/llm.py, engine/portrait.py, engine/main.py, ui/index.html. No packages, no rebuild.
Press "🩺 Diagnostics" (next to the title). "Run checks" gives a report with OK / WARN / FAIL / INFO rows and a fix line for every problem:
- System: Python and packages (missing ones listed), RAM, disk space, app folder writable, config.json.
- GPU: PyTorch build, CUDA device, VRAM free, whether this PyTorch build contains your GPU's architecture (RTX 50-series needs cu128), a real fp16 math test.
- Models: every checkpoint / LoRA header is read: broken or truncated downloads are caught, and files are classified (SDXL / SD1.5 / Flux-or-other).
- Downloads: IP-Adapter, OpenPose ControlNet, internet reachability.
- Assistant: llama-server version (CUDA / Vulkan), model, size vs. settings.
- Self-tests (CPU, ~1 s): pixelize, rig animation, export, projects, portrait pipeline - proves the app's own code works on your machine.
- Recent API errors and the last lines of engine.log / llm.log.
Buttons: "GPU test" loads SDXL and renders 4 steps (reports load time, speed, peak VRAM); "Assistant test" loads the model and asks for one word (speed in tokens/s);
"Copy report" puts the whole report on the clipboard (also saved as diagnostics.txt).
Also new: checkpoints that cannot work (Flux, SD1.5, HiDream, broken files) and LoRAs for other model families (Qwen, Wan, Flux) are now tagged in the dropdowns, and Generate / Portrait / cleanup refuse them with a clear message instead of a cryptic error. The first SDXL checkpoint is preselected if sd_xl_base is missing.

## Phase 14 - pixel editor
Unzip over your spriteforge folder. Only ui/index.html changed (no engine changes, no packages, no rebuild).
An "Edit" button now appears on: generated results (Generate / Reference / Pixelize), portrait base cards, portrait expressions,
saved-sprite gallery items, plus "Edit frame" under the animation preview and "Edit source sprite" in the Animate panel.
The editor never changes the canvas size, so rig joints, paint and frame alignment stay valid.
Tools (keys): Pencil B, Eraser E, Fill G, Color picker I, Line L, Rectangle R, Oval O, Select/move M.
- Colors: the image's own palette (most used first). "+ Add" adds the picked colour, "Recolor" changes the selected colour everywhere, "Drop unused" tidies the list. The pencil only paints palette colours.
- Brush 1-5 (square or round), filled shapes, "fill replaces this colour everywhere", mirror left/right (symmetry axis shown), grid, zoom 2-32x.
- Select: drag a box, drag inside it to move, arrow keys nudge (selection, or the whole image if nothing is selected), Del clears, Flip H/V work on the selection or whole image.
- Undo / redo (Ctrl+Z, Ctrl+Y), one step per stroke. "Show original" compares with the starting image. Onion skin of neighbouring frames when editing an animation frame.
- Apply (writes back to where it came from), Save to project, PNG / PNG 8x, use as reference, send to Animate.
Animation frames: edits are used by Export ("Use reviewed / edited frames") and are saved in the project. Pressing Preview again re-renders and discards manual edits for that animation.
Gallery items: "Save over this sprite" replaces the saved file.

## Phase 15 - palette tools
Unzip over your spriteforge folder. New: engine/palettes.py. Changed: engine/pixelize.py, engine/main.py, engine/projects.py, ui/index.html. No packages, no rebuild.
New "Palette" tab (also: "Palette tools..." button inside the pixel editor).
Source: upload a sprite, or use the Reference / Rig source / Portrait base. "From image" fills the working palette (most-used first).
- Library: built-ins (pico8, gameboy, cga16, c64, sweetie16) + your own. Import a .hex / .gpl (GIMP) / .pal (JASC) file or a swatch PNG (e.g. downloaded from Lospec),
  name it, Save. Saved palettes appear in the "Fixed palette" list of Generate / Reference / Pixelize automatically (survives restarts: palettes/*.json).
- Export the working palette as .hex, .gpl, .pal and PNG swatches (exports/palettes/) - loads in Aseprite, GIMP, Lospec, Godot...
- Remap image: snaps every pixel to the nearest colour (perceptual OKLab). Dithering: none / ordered 2x2 / ordered 4x4 / Floyd-Steinberg, with strength.
- Reduce to N colours, Merge similar colours (distance slider) - tidies AI noise.
- Colour variants: hue-shifted copies for team colours / palette swaps. Lightness is kept (shading stays right); colours are pulled into gamut instead of clipped;
  click swatches to protect them (skin, eyes); very dark colours (outlines) can be kept automatically.
- Shading ramp: dark->light steps from any colour with the pixel-art rule (shadows drift cool, highlights warm); click ramp colours to add them.
- Results appear as cards with Edit / Reference / Animate / Save / PNG. The working palette and protected colours are saved in the project.
Floyd-Steinberg is limited to images up to ~200k pixels (larger ones fall back to ordered dithering with a note).

## Phase 15.1 - HOTFIX: "checkpoint not found ... not SDXL" / cannot generate
Cause (introduced in phase 13): the model tagger changed the option TEXT, and because the options had no separate value, the tag became part of the file name.
Also the classifier treated 'transformer_blocks' (present in real SDXL files) as a non-SDXL sign, so sd_xl_base_1.0 and the pixel-art LoRA were wrongly flagged.
Fixed: options now carry the exact file name as their value; classification checks real SDXL markers first; only positively identified Flux/DiT, SD 1.5, Qwen/Wan LoRAs and broken files are blocked; anything unrecognised is labelled "? not recognised" but still allowed.
Unzip over your spriteforge folder (ui/index.html, engine/diag.py), then press Ctrl+R / relaunch.

## Phase 16 - secondary motion (cape, hair, tail)
Unzip over your spriteforge folder. Changed: engine/rig.py, engine/main.py, ui/index.html. No packages, no rebuild.
How to use (Animate tab):
1. In "Fix wrongly assigned pixels / paint cape, hair, tail" pick cape, hair or tail, tick Paint mode and paint the LOOSE pixels (the cape, the ponytail, the tail).
   Painted parts show in their own colour in the rig editor. No joints to place: the attach point (nearest the neck / head / pelvis) and the tip are found automatically.
2. Preview any animation. The painted parts now lag behind the body, swing and settle:
   - they follow the body's rotation and movement with a delay, overshoot a little and settle (damped spring chains, 1-6 segments)
   - running / walking blows them backwards; looping clips get a gentle breeze so an idle is never frozen
   - looping clips are simulated for several cycles first, so the loop is seamless; one-shot clips start from rest
3. Controls: Flutter (how strongly they react), Stiffness (higher = snappier, shorter swing), Damping (higher = settles faster),
   segments per part (more = bendier), "in front of body" per part (default: behind).
Painted parts never disappear: with the switch off (or a part too small to simulate) they simply stay attached to the body.
With nothing painted the output is pixel-identical to before. Works with export, packs and AI joint cleanup (cloth joints get cleaned too).

## Phase 17 - sprite templates + image reference
Unzip over your spriteforge folder. New: engine/templates.py. Changed: engine/generate.py, engine/main.py, engine/projects.py, engine/diag.py, engine/llm.py, ui/index.html.
No packages, no rebuild. Reference generation uses the IP-Adapter you already downloaded for the Reference-pose tab (else ~3 GB, once).
New "Template" tab:
1. Template: upload a plain dummy sprite (or use the Rig source / Reference tab sprite), or press "Make dummy template" for a built-in neutral mannequin
   (32-128 px, normal or chibi proportions, front or side view). The built-in dummy comes with a perfect rig: every pixel is pre-assigned to its bone.
2. Reference image: any picture whose look you want (armour, outfit, colours). Optional: with none, the prompt alone decides.
3. Generate: SDXL repaints INSIDE the template's silhouette only (inpaint), guided by the reference (IP-Adapter) and your prompt.
   Result = exactly the template's pixel size and shape. Controls:
   - Redraw strength: higher = more freedom to redraw, lower = stays closer to the dummy's shading and limb layout
   - Reference strength: how strongly the reference's look is copied
   - Silhouette freedom (px): 0 = exact silhouette; 2+ lets hair, capes and weapons stick out slightly (only where the model really drew something)
   - Palette from: Reference (colours match your picture) or Result; Colors; Clean stray pixels
4. Each result has "Animate (template rig)": opens it in the Animate tab with the template's joints and painted parts already in place, because the size and alignment are identical.
Template, reference image and rig are saved in the project.

## Phase 18 - 4 and 8 direction sheets
Unzip over your spriteforge folder. New: engine/directions.py. Changed: engine/rig.py, engine/templates.py, engine/main.py, engine/projects.py, ui/index.html.
No packages, no rebuild. Generating views uses the IP-Adapter already used by the Template tab.
New "Directions" tab. Only FIVE views are needed: south, south-east, east, north-east, north.
West, south-west and north-west are exact mirror images of east, south-east and north-east (4 directions need only S, E, N).
1. Fill the views: "Generate all views" (built-in dummy for each viewing angle + the Template tab's reference image, prompt and strengths,
   ONE seed and one palette for all views so they match), or per view: Upload, Dummy, Edit (pixel editor), Rig... (open in Animate), Take rig, Regen.
   A view without a rig gets one guessed automatically.
2. Preview: any animation in all directions at once, laid out like a compass (mirrored views are labelled).
3. Export direction sheets: tick the animations; one row per direction, in clockwise-from-south order or RPG Maker order (down, left, right, up).
   Animations are named <clip>_<dir> (walk_s, walk_sw, idle_e ...) in the atlas JSON, the Godot SpriteFrames and the Unity data, with loop flags.
   Every frame of every direction shares one cell size and one feet pivot, so switching direction never makes the character jump.
   directions.json lists the rows and which directions are mirrors.
Animation changes:
- Walk and run are now view-aware: seen from the front or back the legs cannot swing sideways, so the walk becomes a step-and-bob (small thigh swing,

## Phase 19 - generation queue + history
Generate / Reference pose jobs run through a background queue (add several, pause, cancel, progress). Every finished job is kept in a searchable history with its settings:
use settings again, re-run (same seed), fork (new seed), favourite, note, compare side by side. New: engine/jobs.py, Queue tab. Details: docs/phases/PHASE19.md.

## Phase 20 - tiles and props
New "Tiles & props" tab: seamless tiles (blended before pixelising, seam score), props, item icons and UI elements; workbench with repeat preview, wrap-around offset and a colour-preserving seam repair;
tileset builder with random map preview; export to a grid sheet + Godot 4 TileSet (.tres) + Tiled (.tsx), or a packed atlas for mixed sizes. Details: docs/phases/PHASE20.md.

## Phase 21 - autotile / terrain sets
Terrain set card on the Tiles & props tab: from a seamless terrain tile (+ optional ground tile) generate a 47-tile blob set or a 16-tile edge set with exact joins, rim and rounding options,
a random autotile map preview, and export with the neighbour lookup, a Godot 4 TileSet with terrain peering bits and a Tiled wang set. New: engine/terrain.py. Details: docs/phases/PHASE21.md.

## Phase 22 - tile follow-ups
Corner (dual-grid) sets and multi-terrain sets (81 / 256 tiles) with exact joins, animated tiles (scroll / ripple / shimmer, loop-perfect, GIF + Godot + Tiled export), per-tile solid flags exported as collision shapes,
and AI seam repair (inpaint only the half-shifted seam cross). Details: docs/phases/PHASE22.md.

## Phase 23 - multi-style character generation
Style presets, HD full-colour output, reference pose support and queue/project settings. See docs/phases/PHASE23.md. Hardware validation pending.

## Phase 24 — HD rig animation (initial implementation)
Automatic smooth rigid-bone rendering for sources above 160 px, alpha preservation, preview fitting, HD export filtering and memory budgets. Regression tests added; execution and visual validation pending.

## Pose preset library
Reference pose editor supports saving changes to existing pose templates, named custom poses, factory reset and clearing saved overrides. Stored in local browser/webview preferences; project/history snapshots retain their own edited skeletons. Tests added; execution pending.

## Phase 25 — reference-guided custom keyframes
Capture start/end and intermediate joint poses, import approximate reference-image joints, preview and export a custom clip, persist timelines in projects. Tests added; execution pending.

## Phase 26 — actual start/end reference animation
Locked first and final image frames, independent SDXL in-betweens or quick crossfade, reference clip persistence and exact-frame PNG export. Phase 25 custom keyframes retained separately. Tests added; execution pending.

## Phase 27 — soft joint deformation
Optional CPU two-bone mesh skinning for elbows and knees; per-clip softness, preview/export and directional integration, rigid fallback, pixel/HD sampling, regression tests. Phase 25/26 retained.

## Phase 28 — character model compatibility
Architecture-aware text generation and checkpoint-specific LoRA compatibility labels. Local Diffusers folders and experimental Lumina single-file transformer route. Existing SDXL reference/inpaint retained. GPU validation pending.
