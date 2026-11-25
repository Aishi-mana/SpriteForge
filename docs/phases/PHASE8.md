# Phase 8 - six new clips
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
