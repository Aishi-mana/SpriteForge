extends Node2D
class_name SpriteForgeCharacter
signal clip_finished
@export_file("*.json") var initial_manifest: String
var clip: Dictionary = {}
var nodes: Dictionary = {}
var visibility: Dictionary = {}
var clock: float = 0.0
var playing: bool = false
var frame: int = 0

func _ready() -> void:
	if not initial_manifest.is_empty():
		load_clip(initial_manifest)

func _json(path: String) -> Variant:
	if not FileAccess.file_exists(path):
		return null
	return JSON.parse_string(FileAccess.get_file_as_string(path))

func _texture(path: String) -> Texture2D:
	if path.begins_with("res://") and ResourceLoader.exists(path):
		var tex = load(path)
		if tex is Texture2D:
			return tex
	var img = Image.load_from_file(path)
	return null if img == null or img.is_empty() else ImageTexture.create_from_image(img)

func _valid(m: Variant) -> bool:
	if not m is Dictionary or m.get("version") != 1 or m.get("format") != "spriteforge_modular_animation":
		return false
	if not m.get("layers") is Array or not m.get("frames") is Array or not m.get("sheet") is Dictionary or not m.get("cell") is Dictionary or not m.get("pivot_px") is Array:
		return false
	var n = int(m.get("frame_count",0))
	if n<1 or n>32 or m.frames.size()!=n or float(m.get("fps",0))<1 or float(m.fps)>60 or m.pivot_px.size()!=2 or m.layers.is_empty() or m.layers.size()>24:
		return false
	var w = int(m.cell.get("w",0))
	var h = int(m.cell.get("h",0))
	var sw = int(m.sheet.get("w",0))
	var sh = int(m.sheet.get("h",0))
	if min(w,h,sw,sh)<1 or max(sw,sh)>16384:
		return false
	var ids: Dictionary = {}
	for i in range(m.layers.size()):
		var l = m.layers[i]
		if not l is Dictionary or not l.get("id") is String:
			return false
		var id: String = l.id
		if not id.is_valid_identifier() or ids.has(id) or l.get("sheet")!="layers/"+id+".png" or int(l.get("z",-1))!=i:
			return false
		ids[id]=true
	if not ids.has(m.get("body_layer","")):
		return false
	for i in range(n):
		var r = m.frames[i]
		if not r is Dictionary or int(r.get("index",-1))!=i or int(r.get("w",0))!=w or int(r.get("h",0))!=h or int(r.get("x",-1))<0 or int(r.get("y",-1))<0:
			return false
		if int(r.x)+w>sw or int(r.y)+h>sh:
			return false
	return true

func load_clip(path: String, keep_equipment: bool = true) -> bool:
	var m = _json(path)
	if not _valid(m):
		push_error("SpriteForge: invalid manifest "+path)
		return false
	if keep_equipment and not clip.is_empty() and (str(m.get("character_id","")).is_empty() or m.character_id!=clip.get("character_id","")):
		push_error("SpriteForge: incompatible recipe. Pass false to reset.")
		return false
	if keep_equipment and not clip.is_empty():
		if m.layers.size()!=nodes.size():
			push_error("SpriteForge: incompatible layer set; include all alternatives in every clip.")
			return false
		for l in m.layers:
			if not nodes.has(l.id):
				return false
	var next: Dictionary = {}
	var choices: Dictionary = {}
	for l in m.layers:
		var tex = _texture(path.get_base_dir().path_join(l.sheet))
		if tex==null or tex.get_width()!=int(m.sheet.w) or tex.get_height()!=int(m.sheet.h):
			for s in next.values():
				s.free()
			push_error("SpriteForge: missing/mismatched texture "+l.sheet)
			return false
		var s = Sprite2D.new()
		s.texture=tex
		s.centered=false
		s.position=-Vector2(float(m.pivot_px[0]),float(m.pivot_px[1]))
		s.region_enabled=true
		s.region_filter_clip_enabled=true
		s.texture_filter=CanvasItem.TEXTURE_FILTER_NEAREST if m.get("sampling")=="nearest" else CanvasItem.TEXTURE_FILTER_LINEAR
		s.z_index=int(l.z)
		next[l.id]=s
		choices[l.id]=true if l.id==m.body_layer else (bool(visibility.get(l.id,l.visible)) if keep_equipment else bool(l.visible))
	for s in nodes.values():
		remove_child(s)
		s.queue_free()
	nodes=next
	visibility=choices
	clip=m
	for s in nodes.values():
		add_child(s)
	play()
	return true

func play() -> void:
	clock=0.0
	frame=0
	playing=not clip.is_empty()
	_apply()

func pause() -> void:
	playing=false

func resume() -> void:
	if not clip.is_empty() and (bool(clip.loop) or clock<float(clip.frame_count)/float(clip.fps)):
		playing=true

func _process(delta: float) -> void:
	if not playing:
		return
	clock+=delta
	var count = int(clip.frame_count)
	var fps = float(clip.fps)
	if bool(clip.loop):
		clock=fmod(clock,count/fps)
	elif clock>=count/fps:
		clock=count/fps
		frame=count-1
		playing=false
		_apply()
		clip_finished.emit()
		return
	frame=mini(count-1,int(clock*fps))
	_apply()

func _apply() -> void:
	if clip.is_empty():
		return
	var r = clip.frames[frame]
	for id in nodes:
		var s: Sprite2D = nodes[id]
		s.region_rect=Rect2(float(r.x),float(r.y),float(r.w),float(r.h))
		s.visible=bool(visibility.get(id,false))

func set_layer_visible(id: String, enabled: bool) -> bool:
	if not nodes.has(id) or id==clip.get("body_layer"):
		return false
	visibility[id]=enabled
	_apply()
	return true

func equip(id: String) -> bool:
	if not nodes.has(id) or id==clip.get("body_layer"):
		return false
	var category = ""
	for l in clip.layers:
		if l.id==id:
			category=l.category
	for l in clip.layers:
		if l.category==category and l.id!=clip.body_layer:
			visibility[l.id]=l.id==id
	_apply()
	return true

func unequip_category(category: String) -> void:
	for l in clip.get("layers",[]):
		if l.category==category and l.id!=clip.body_layer:
			visibility[l.id]=false
	_apply()

func reset_equipment() -> void:
	for l in clip.get("layers",[]):
		visibility[l.id]=true if l.id==clip.body_layer else bool(l.visible)
	_apply()

func save_loadout(path: String = "user://spriteforge_loadout.json") -> bool:
	if clip.is_empty() or str(clip.get("character_id","")).is_empty():
		return false
	var file = FileAccess.open(path,FileAccess.WRITE)
	if file==null:
		return false
	file.store_string(JSON.stringify({"version":1,"character_id":clip.character_id,"visibility":visibility}))
	return true

func load_loadout(path: String = "user://spriteforge_loadout.json") -> bool:
	var raw = _json(path)
	if clip.is_empty() or not raw is Dictionary or raw.get("version")!=1 or raw.get("character_id","")!=clip.get("character_id","") or str(raw.get("character_id","")).is_empty() or not raw.get("visibility") is Dictionary:
		return false
	var next = visibility.duplicate()
	for id in raw.visibility:
		if nodes.has(id) and id!=clip.body_layer:
			if not raw.visibility[id] is bool:
				return false
			next[id]=raw.visibility[id]
	visibility=next
	_apply()
	return true
