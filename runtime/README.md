# SpriteForge modular runtime (Phase 36)

Copy the runtime script once per game project. Keep each exported clip's manifest.json and layers/ folder intact. Export all clips from the same recipe with hidden alternatives enabled, same body and layer order. The character fingerprint checks compatible recipes; FPS, padding and frame count may differ. For another recipe pass false to load_clip/LoadClip. Older Phase 35 bundles lack a fingerprint and should be re-exported.

## Godot 4
Copy godot/SpriteForgeCharacter.gd into res:// once. Attach to a Node2D and set initial_manifest or call:
    $Character.load_clip("res://characters/walk/manifest.json")
    $Character.equip("layer_04")
    $Character.set_layer_visible("layer_03", true)
    $Character.unequip_category("accessory")
    $Character.save_loadout("user://hero.json")
    $Character.load_loadout("user://hero.json")

Use play(), pause(), resume(), clip_finished. Set PNG imports to lossless, no mipmaps; include JSON files in export filter. Node origin is the feet pivot.

## Unity desktop
Copy unity/SpriteForgeCharacter.cs into Assets/Scripts once. Place clip folders (manifest and layers, omit duplicate scripts) in Assets/StreamingAssets/characters. Attach component to an empty GameObject. Set initialManifest relative to StreamingAssets, pixelsPerUnit, sorting layer and order; use SortingGroup for inter-character sorting. Example:
    character.LoadClip("characters/walk/manifest.json");
    character.Equip("layer_04");
    character.SetLayerVisible("layer_03", true);
    character.UnequipCategory("accessory");
    character.SaveLoadout();
    character.LoadLoadout();

Use Play(), Pause(), Resume(), clipFinished. Save defaults to Application.persistentDataPath; supply distinct paths for multiple characters. Desktop synchronous filesystem loading only; Android/WebGL need an asynchronous loader.

Equip hides alternatives in the same category; visibility can stack multiple accessories. Body cannot be unequipped. Only the active clip is retained, switching briefly holds two sets. Export all alternatives for consistent loadouts across clips. IDs refer to manifest indices, not names. No gameplay inventory/stats, state machine, collision, multiplayer or live skeletal rig. Godot/Unity loadout formats are engine-specific. Actual editor/runtime verification pending.
