# Phase 18 - 4 and 8 direction sheets
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
  bigger body bob, slight sway); three-quarter views swing about 65%. The side view is unchanged (pixel-identical to before).
- Seen from behind, painted cape / hair / tail parts are drawn in front of the body automatically.
New dummy views for the Template tab / API: back, diag (south-east), diag_back (north-east); every dummy still comes with an exact rig.
The direction slots (sprites + rigs) are saved in the project.
