# Phase 63B — Advanced synchronized playback and timeline

Each actor has an inclusive scene start/end (zero-based; -1 end follows scene length), source frame offset, 10–300% speed and loop/hold/hide behavior. Both tracks display one-based sampled source frame numbers, with blank cells for hidden actors. Click a rendered timeline cell or use scrub, previous/next and restart. Playback uses elapsed time to avoid cumulative timer drift; preview loop is optional. Pair JSON v1 retains timing via existing scene actor fields, and 63A bundles retain their prior defaults. The CPU renderer remains authoritative. Existing 512×384, 60-frame and source budgets remain unchanged.

Acceptance: test clips with unequal FPS and counts, delayed entry, nonzero offsets, all end modes, preview one-shot, stepping and save/reload. Confirm source clips unchanged. Desktop and CI validation pending.
