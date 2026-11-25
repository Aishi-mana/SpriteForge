# Phase 14 - pixel editor
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
