# Phase 64I — Integration and desktop acceptance

Status: integration changes submitted; CPU and desktop acceptance pending. PR #168 passed CPU run 46167123563 and merged at 0716b2f4.

## Integration changes
Busy editor open/discard actions now explain why they cannot proceed. Closing the comparison invalidates pending canvas draws; stale errors cannot overwrite a new source session. Runtime regression covers staging, original isolation, undo, redo, restore, locked frames and stale revision protection. No model/backend or export format changes.

## Windows desktop acceptance (record pass/fail, model, actual result)
Use a disposable short animation and retain a copy of its original JSON. Launch spriteforge.bat after pulling. 
- [ ] Open Direct Animation Editor from Full-frame Animation Studio; compare, play, seek, close and reopen.
- [ ] Import a matching PNG, reject mismatched dimensions and locked frames, try range import, undo/redo/restore; export original and edited JSON and check frame order and timing.
- [ ] Save checkpoint, discard and reopen same original, resume; reject a different original. Test overlay and difference during rapid seeking.
- [ ] Apply candidate, verify timeline Undo restores original, reopen editor and repeat without restarting.
- [ ] Inspect motion and generate guide; test character replacement and appearance edit with installed compatible models, cancel/discard and retry. Verify no silent fallback.
- [ ] Stage temporal correction and compare result; verify locked frames unchanged.
- [ ] In paired preview replace B only; check A remains unchanged and independent ZIP opens.
- [ ] Import/reuse MP4, trim/reverse, extract, stage and export; confirm original retained.
- [ ] Export PNG atlas/frames and animated WebP; inspect output in viewer, confirm transparency and timing (identical WebP frames may coalesce).

CPU tests do not establish actual desktop rendering, GPU quality, video codec availability or game-engine import. Record these separately. Phase 65 unified asset library remains next after integration; no permanent revision library added here.
