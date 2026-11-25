# SpriteForge user guide

## 0. The window

- **Left sidebar**: project box (name, Save / Load / Delete), the models folder, the tab buttons, then the controls of the active tab.
  The *shared generation controls* (checkpoint, LoRA, weight, seed, steps, CFG, background, sampler, "Remove ground shadow") show on Generate,
  Reference pose, Portrait, Template and Directions.
- **Right area**: the editor / preview of the active tab, and result cards. Result cards have **Edit** (pixel editor), **Use as reference**,
  **Animate**, **Save** (to the project gallery), **PNG / PNG 8x**.
- **Bottom-right**: `✦ Assistant` (chat). **Top**: `🩺 Diagnostics`.
- Everything in the sidebar is saved in the project, and the project **autosaves every 20 s** once it has been saved once. The last project reopens on start.

Key ideas: a **rig** = 15 joints + which bone each pixel belongs to (10 body bones, plus optional cape/hair/tail parts);
a **clip** = a procedural animation (idle, walk, ...); a **view** = one facing direction of a character; **palette lock** = results use only the reference's colours.

## 1. First run (10 minutes)

1. Set the models folder (sidebar) and press **Set**. Checkpoint and LoRA dropdowns fill in; `sd_xl_base_1.0` and `pixel-art-xl` are preselected.
2. Press **🩺 Diagnostics > Run checks**. Fix anything red/yellow (each row has a fix line). Optional: **GPU test** (loads SDXL, 4 steps; shows peak VRAM).
3. **Generate** tab: keep the default prompt, press **Generate**. First run loads the model (about a minute).

## 2. Make a sprite from text (Generate)

1. Prompt: short, comma-separated, e.g. `knight with blue armor and red cape, holding a sword, standing`. The app adds "pixel art", "single character", "full body" and a plain background.
2. Conversion (all on by default): **Crisp conversion** (grid snap + perceptual palette + dominant-colour downsampling), **Clean stray pixels**, **Outline** (none / selective / dark),
   **Pixelize mode**: *Fixed size (long side)* or *Auto-detect grid*; **Colors** 16-24 is plenty; **Fixed palette** to force a preset or one of your own.
3. Tips: the pixel-art LoRA draws on a hidden 8 px grid, so *Auto-detect grid* (native size) or sizes 96-128 look best; shrinking far below the native size loses thin details.
   Try *Sampler > DPM++ 2M Karras* with the **same seed** to compare. Untick *Crisp conversion* to compare with the old converter.
4. Press **Edit** on a result to fix pixels by hand, **Save** to keep it in the project.

## 3. New poses from a reference (Reference pose)

1. Press **Use as reference** on a sprite (or upload one). Describe the new pose in *Pose / action text*.
2. **Use skeleton pose** (ControlNet): pick a preset (stand, walk, run, jump, attack, crouch; front or side), drag joints (Shift+drag moves the whole figure), Mirror, scale about the feet.
   Line the skeleton up over the faint reference in the *Stand* preset first. *Skeleton strength* ~0.8 (higher = follows the pose more), *Reference strength* ~0.7.
3. **Canvas** = fixed square output size (default 128) at one constant scale, so frames line up. *Lock palette to reference* keeps colours. *Generation size* 768 (640 if memory is tight).
4. Limits: the AI cannot keep a character identical across poses on 8 GB. For animation use the **rig** (section 5); use this tab to explore new poses/looks.

## 4. Pixelize any image

Pixelize tab: upload, choose mode/size/colours/palette/outline, press **Pixelize**. *Auto-detect grid* works best on images that already have a pixel grid
(AI pixel art, upscaled sprites). Illustrations: use Fixed size 96-128 with 24-32 colours.

## 5. Animate (the rig)

1. **Source**: press **Animate** on any sprite, or upload one. Joints are auto-placed from the bounding box (a rough guess).
2. **Rig editor**: drag the 15 joints onto the body (head top, neck, pelvis, shoulders/elbows/wrists, hips/knees/ankles). Colours show which bone owns each pixel.
   `l_` / `r_` mean **screen**-left / screen-right. Wrong ownership (sword on the head, cape on an arm)? Choose the part in the dropdown, tick **Paint mode**, drag over the pixels.
3. **Secondary motion** (cape, hair, tail): paint the loose pixels as **cape**, **hair** or **tail** the same way. They then lag, swing and settle.
   Controls: Flutter, Stiffness, Damping, segments per part, "in front of body". Loops are seamless; seen from behind parts go in front automatically (Directions).
4. **Animation**: pick a clip (loops: idle, walk, run, climb, cheer; play once: attack, cast, block, jump, hurt, death), frames, FPS, *Sprite faces* (right/left),
   *Nearer limbs* (screen-right/left/both for front views), *Weapon arm* (attack/cast/block), Amplitude, Canvas padding (0 = auto), Joint overlap.
   Press **Preview animation**. Click a frame in the strip to pause on it; *Onion skin* shows neighbours; **✏ Edit frame** edits it by hand.
5. **AI joint cleanup** (optional, slow ~20-60 s/frame): tick it, write a short character description, press Preview. Only small discs around moving joints are repainted
   (SDXL inpaint at low strength, same seed for every frame, snapped to your palette). Then **review**: untick *AI* under a frame to keep the rig-only version,
   *AI all / Rig all*, **Redo unticked frames (new seed)**, *Highlight what the AI changed*, *Show before cleanup*. Frames the AI changed too much are reverted automatically.
6. **Export**: layout (row per animation / grid / column), padding, power-of-two, *Crop to content* (keeps the feet pivot), *Same cell size for every animation*,
   Godot 4 files, Unity files, GIF previews, frame PNGs; tick the clips for a **pack**. **Export current animation** or **Export pack (ticked animations)** write to `exports/<name>_pack/`
   (or `<name>_<clip>/` for one clip): sheet PNG, Aseprite-style atlas JSON (frame tags with fps + loop, per-frame pivot), `.tres` + `.tscn` (Godot 4), `_unity.json` + importer script, `README.txt`.
7. **Godot**: copy `*_sheet.png`, `*.tres`, `*.tscn` to the folder you typed in *Godot folder* (default `res://sprites/`), open the `.tscn`: an AnimatedSprite2D with all animations, origin at the feet, nearest filter.
   **Unity**: copy the sheet, `*_unity.json`, `SpriteForgeImporter.cs` into `Assets/`, select the json, then *Assets > SpriteForge > Import Sprite Sheet* (slices sprites with a feet pivot and creates one `.anim` per clip).

## 6. Portraits and expressions

1. **Portrait** tab: describe face/hair/eyes/collar. *Start from*: Text only, or your Reference sprite via IP-Adapter. Size 128 is ideal (1024/128 = the LoRA's 8 px grid). **Generate base portrait**, then **Use as base** on one.
2. **Face area**: preset (whole face / eyes + brows / mouth) or drag on the portrait to draw your own. Only that area is repainted; everything else stays pixel-identical.
3. Tick expressions (happy, sad, angry, surprised, embarrassed, smug, sleepy, pain, scared, determined, laughing, serious) and/or type your own; **Generate expressions**.
   *Change strength* 0.82 (higher = bigger change). *Extra colors allowed* lets blush/tears keep their colours (0 = base palette only).
4. **Export portrait set**: PNGs + sheet + atlas + Godot (one 1-frame animation per expression) + Unity data.

## 7. Palette tools

Load a sprite (upload / Reference / Rig source / Portrait). **From image** extracts its palette. Library: built-ins (pico8, gameboy, cga16, c64, sweetie16) + yours; **Import** `.hex/.gpl/.pal` or a swatch PNG (Lospec),
name it, **Save** (it then appears in every *Fixed palette* list). **Remap** with dithering (none / ordered 2x2 / 4x4 / Floyd-Steinberg), **Reduce to N**, **Merge similar**,
**Make variants** (hue shifts keep lightness; click swatches to protect skin/eyes; very dark colours stay), **Ramp** (shading ramp: shadows cool, highlights warm), **Export** .hex .gpl .pal + PNG.

## 8. Template + reference

1. **Template** tab: upload a plain dummy sprite, or **Make dummy template** (built-in neutral mannequin: 32-128 px, normal/chibi, front/side; comes with a perfect rig).
2. Add a **Reference image** (the look to copy). Prompt optional. **Generate from template**: SDXL repaints only inside the silhouette, guided by the reference. The result has *exactly* the template's size and shape.
   *Redraw strength* (higher = more freedom), *Reference strength*, *Silhouette freedom px* (0 = exact; 2+ lets hair/capes stick out where the model drew something), *Palette from* Reference/Result.
3. **Animate (template rig)** on a result opens it in Animate with the template's joints and painted parts already set.

## 9. Directions (4 / 8)

Only 5 views are needed: **S, SE, E, NE, N** (W, SW, NW are exact mirrors). 4 directions need S, E, N.
1. **Generate all views** (built-in dummy per angle + the Template tab's reference/prompt/strengths, one seed and palette for all). Or fill each view by hand:
   **Upload**, **Dummy**, **Edit**, **Rig...** (open in Animate to refine, then **Take rig**), **Regen** (re-roll that view).
2. **Preview**: any clip in all directions at once (compass layout).
3. **Export direction sheets**: tick clips; rows in clockwise order from south, or RPG Maker order (down, left, right, up) for 4 directions. Animations are named `<clip>_<dir>` (`walk_s`, `idle_ne`),
   all frames share one cell size and one feet pivot; `directions.json` lists rows and mirrors. Walk/run are view-aware (front/back step in place, three-quarter swings less); capes go in front when seen from behind.

## 10. Tiles and props

**Tiles & props** tab: choose Seamless tile / Prop / Item icon / UI element, write a prompt, Generate (or add to the queue). For tiles the result is an exact size x size seamless tile with a *seam score* (about 1 = invisible).
Press **To tileset** under a result to put it on the **workbench**: see it repeated, **Offset 1/2** to look at the old edges, **Make seamless** (no new colours), **Edit**, then **Add to tileset**.
**Random map preview** shows how your tiles combine; **Export tileset** writes a grid sheet + Godot 4 `.tres` + Tiled `.tsx` (or a packed atlas for different sizes) to `exports/<name>_tileset/`.

**Terrain sets (autotile).** Below the workbench: put a seamless tile on the workbench, press **Use workbench tile as A** (e.g. grass), do the same for **B** (e.g. dirt, optional), then **Generate set**:
47 tiles (or 16 with *sides only*) with borders, rounded corners and a rim colour. **Autotile map preview** paints a random blob map: all joins must look continuous. **Export terrain set** writes the sheet,
`terrain.json` with the neighbour lookup, a Godot 4 TileSet with the terrain already configured (paint with the Terrains tab) and a Tiled `.tsx` wang set. Inset, rounding, rim and baked/transparent ground are in the sidebar.

**Corner and multi-terrain sets.** Choose *16-tile corners* or *Multi-terrain corners* as set type: tiles are picked by the terrain at their four corners (2 terrains: 16 tiles; 3: 81; 4: 256). Fill slots A-D from the workbench, name the terrains in the sidebar, Generate, preview, Export.

**Animated tiles.** Put a seamless tile on the workbench, choose Scroll / Ripple / Shimmer in the sidebar, **Make frames**: the card loops the result. **Export animated tile** writes the strip, a GIF and Godot / Tiled animation files.

**Solid tiles and seam repair.** Tick **solid** under a tileset tile to export a collision shape for it. **AI repair seams** (workbench) lets the AI redraw only the middle cross of a tile where the old seams are.

## 11. Pixel editor

Open with **Edit** on any sprite/frame/portrait/gallery item (or *Edit source sprite* in Animate). Tools: Pencil B, Eraser E, Fill G, Picker I, Line L, Rectangle R, Oval O, Select M.
Palette-locked painting (`+ Add`, `Recolor`, `Drop unused`), brush 1-5, filled shapes, mirror, grid, zoom, undo/redo (Ctrl+Z/Y), show original, onion skin (frames), arrow keys nudge, flip.
**Apply** writes back to where it came from. The canvas size never changes (so rigs and frame alignment stay valid).

## 12. Queue and history

On **Generate** and **Reference pose**, **Generate** runs through a queue. **＋ Add to queue** adds a job without waiting, so you can queue several and keep working.
Open the **Queue** tab (or click the strip under the button) to see progress, Pause / Resume, and Cancel. Every finished job lands in the **history** below:
click a card to **Use these settings**, **Re-run** (same seed) or **Fork** (new seed), ★ favourite it, add a note, or tick several and **Compare**. History survives restarts (newest 300 kept, favourites always).

## 13. Assistant

`✦ Assistant`: gear > **Scan** (finds `llama-server` and `.gguf` files under the scan folder) > pick model > Save. First message loads the model (CPU by default; unloads after 10 idle minutes).
It proposes changes as **Apply** buttons (prompt, negative, character, pose, anim, template, portrait, strengths). It never generates or exports by itself.

## 14. Where your data lives

`projects/<name>/` (project.json, images, sprites/, results/, portrait/) - plain files, copy a folder to back it up. `exports/` sheets, packs and tilesets. `palettes/` your palette library.
`history/` the queue history. `config.json` settings. Logs: `engine.log` (desktop app), `llm.log`, `diagnostics.txt`.
