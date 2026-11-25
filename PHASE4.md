# Phase 4 - rig-based animation
Unzip over your spriteforge folder (new: engine/rig.py; changed: engine/main.py, ui/index.html). No Rust changes, no new pip packages.

Animate tab:
1. Press "Animate" under any sprite result (or upload a sprite).
2. Joints are auto-placed from the sprite's bounding box. Drag them onto the real body: head top, neck, pelvis, shoulders/elbows/wrists, hips/knees/ankles.
   Part colors show which bone each pixel follows. "l_" = screen-left, "r_" = screen-right.
3. Fix mistakes (sword assigned to the head, cape on the arm...): choose the right part, tick Paint mode, drag over those pixels.
4. Pick idle / walk / run / attack / jump, set facing, press Preview. Export writes to <project>/exports/<name>_<anim>/:
   sheet PNG, atlas JSON (Aseprite-style hash + pivot at the feet), GIF (4x) and individual frames.
Best on side-view characters (walk/run/attack). Idle and jump also work front-on.
