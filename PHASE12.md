# Phase 12 - quality pass (crisp conversion, grid snap, palette, outline, sampler)
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
