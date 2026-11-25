# Phase 16 - secondary motion (cape, hair, tail)
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
