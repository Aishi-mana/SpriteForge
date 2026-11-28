# Phase 66B — Workspace consolidation

Navigation categories are immediately below the app title; all 20 original IDs and handlers are retained. Pinned studios and the five most recently visited studios use local browser preferences, separate from project data. Use Pin studio / Unpin studio in the main toolbar, then select a pinned or recent studio in the sidebar. Startup still opens Generate. Project name and save/load stay visible; the main toolbar exposes project controls, Library, Queue/history, commands and focus mode. In focus mode the project shortcut reveals the sidebar. Advanced sampling fields are grouped under a remembered disclosure; model, LoRA and background remain directly accessible. No sampling value, model default or backend behavior changed.

## Verification

Source inventory preserved all existing element IDs without duplicates. JavaScript syntax parsed. Added CPU source and Node preference regressions in tests/test_phase66b_workspace.py; CI execution and actual Windows WebView visual acceptance pending.

Desktop acceptance: switch all 20 studios via categories, pin/unpin, reopen application and verify pinned/recent lists and advanced disclosure, use Queue/Library in focus mode, open project controls and save/load, verify Generate/Reference/Rig/full-frame paths and existing sampling defaults. Check narrow-window layout, keyboard focus and repeated generation. No GPU benchmark or packaging changes.
