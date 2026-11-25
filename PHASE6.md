# Phase 6 - projects (save / load)
Unzip over your spriteforge folder. New: engine/projects.py. Changed: engine/main.py, ui/index.html. No packages, no rebuild.

Top of the sidebar: Project name + Save / Load / Delete (Delete needs a second click).
Saved in <app>/projects/<name>/ : project.json (every setting, per-animation params, rig joints, paint, skeleton pose),
ref.png (reference sprite), anim.png (rig source sprite), sprites/ (results you pressed "Save" on).
- "Save" under any result stores that sprite in the project; the gallery at the bottom has Ref / Anim / x buttons.
- Autosaves every 20 s once the project has been saved once. Reopens your last project on startup.
- Each animation (idle, walk, ...) remembers its own frames / fps / amplitude / facing settings.
- Exports go to <app>/exports/<project>_<anim>/ (export name defaults to the project name).
Project folders are plain files: copy a folder to back it up or move it to another machine.
