# Phase 9 - export layouts (Godot 4, Unity, Aseprite/Phaser)
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
