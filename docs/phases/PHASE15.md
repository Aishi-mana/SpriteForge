# Phase 15 - palette tools
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
