"""CPU-only shared-library round trip, isolation and preset checks."""
from _common import *
from engine import asset_library as L, modular as M, modular_rig as R
root=tmpdir()
body,joints,_=synth_sprite()
recipe={"width":body.width,"height":body.height,"pixel":True,"layers":[{"name":"Base","category":"body","image":M.png_uri(body)}]}
d=R.describe(recipe);recipe["rig"]={"body_key":d["body_key"],"joints":joints}
entry=L.save(root,{"kind":"character","name":"Hero","tags":["RPG","Blue"],"recipe":recipe})
ok(len(L.list_entries(root,"character","rpg blue"))==1,"search and kind filter")
ok(L.preview_path(root,entry["id"]).is_file(),"preview created")
clean=L.apply(root,entry["id"],None)
ok(clean["layers"][0]["name"]=="Base","character snapshot restored")
clean["layers"][0]["name"]="Changed"
ok(L.load(root,entry["id"])["payload"]["recipe"]["layers"][0]["name"]=="Base","snapshot independent")
asset=L.save(root,{"kind":"asset","name":"Base asset","recipe":recipe,"index":0})
added=L.apply(root,asset["id"],recipe,True)
ok(len(added["layers"])==2 and sum(l["visible"] for l in added["layers"])==1,"body alternative added without deleting existing")
preset=L.save(root,{"kind":"rig","name":"Hero rig","recipe":recipe})
base=M.validate(recipe)[0];base.pop("rig")
ok(L.apply(root,preset["id"],base)["rig"]==M.validate(recipe)[0]["rig"],"same body rig restored")
base["layers"][0]["x"]=1
try:L.apply(root,preset["id"],base);ok(False,"mismatched rig")
except ValueError:ok(True,"mismatched rig rejected")
try:L.load(root,"../config");ok(False,"unsafe id")
except ValueError:ok(True,"unsafe id rejected")
L.delete(root,asset["id"])
ok(len(L.list_entries(root))==2 and len(recipe["layers"])==1,"deletion does not alter source project")
image=M.png_uri(body)
static=L.save(root,{"kind":"image","name":"Standalone","image":image})
ok(L.load(root,static["id"])["payload"]["image"]==image,"standalone image round trip")
from engine import full_frame
doc=full_frame.default()
doc.update(width=body.width,height=body.height,pivot=[0,0],frames=[image,image],fps=8)
anim=L.save(root,{"kind":"animation","name":"Idle","document":doc})
ok(anim["frames"]==2 and anim["fps"]==8,"animation metadata")
ok(L.load(root,anim["id"])["payload"]["document"]["frames"]==doc["frames"],"animation frames round trip")
ok(len(L.list_entries(root,"animation"))==1 and len(L.list_entries(root,"character"))==1,"new and legacy entries coexist")
for invalid in [{"kind":"image","name":"Bad","image":"https://example.com/x.png"},{"kind":"animation","name":"Empty","document":full_frame.default()}]:
    try:L.save(root,invalid);ok(False,"invalid asset rejected")
    except ValueError:ok(True,"invalid asset rejected")
try:L.apply(root,anim["id"],recipe);ok(False,"wrong studio")
except ValueError:ok(True,"wrong studio rejected")
before=L.load(root,static["id"])
preview=L.preview_path(root,static["id"]).read_bytes()
changed=L.update_metadata(root,static["id"],{"name":"Renamed","collection":"Forest","favorite":True,"tags":["hero"],"notes":"Reusable"})
ok(changed["favorite"] and changed["collection"]=="Forest","metadata organization persisted")
after=L.load(root,static["id"])
ok(after["payload"]==before["payload"] and after["meta"]["created"]==before["meta"]["created"] and L.preview_path(root,static["id"]).read_bytes()==preview,"metadata edit preserves artwork and creation date")
ok(L.list_entries(root,"image","forest hero")[0]["id"]==static["id"],"collection searchable")
for patch in [{"kind":"rig"},{"favorite":"yes"},{"name":""},{"collection":"x"*81}]:
    try:L.update_metadata(root,static["id"],patch);ok(False,"invalid metadata rejected")
    except ValueError:ok(True,"invalid metadata rejected")
ok(L.load(root,static["id"])==after,"invalid edits leave snapshot unchanged")
directional={**doc,"direction":"S","frames":[],"directions":{"N":{"frames":[image,image]}}}
directional_entry=L.save(root,{"kind":"animation","name":"North clip","document":directional})
ok(directional_entry["frames"]==2 and directional_entry["clips"]==1,"save populated inactive direction")
ok(L.load(root,directional_entry["id"])["payload"]["document"]["directions"]["N"]["frames"]==[image,image],"direction retained")
from engine import visual_motion
from PIL import Image
raw=visual_motion.encode([Image.new("RGB",(32,32),"red"),Image.new("RGB",(32,32),"blue")],8,root/"sample.mp4")
video=L.save_video(root,raw,{"name":"Motion"})
ok(video["kind"]=="video" and video["bytes"]==len(raw),"video metadata")
ok(L.video_path(root,video["id"]).read_bytes()==raw,"original video bytes preserved")
ok(L.preview_path(root,video["id"]).is_file(),"video poster created")
ok(L.list_entries(root,"video")[0]["id"]==video["id"],"video filter")
L.update_metadata(root,video["id"],{"favorite":True})
ok(L.video_path(root,video["id"]).read_bytes()==raw,"video metadata edit preserves bytes")
try:L.save_video(root,b"invalid",{"name":"Invalid"});ok(False,"bad MP4 rejected")
except ValueError:ok(True,"bad MP4 rejected")
old_limit=L.MAX_BYTES
try:
    L.MAX_BYTES=len(raw)
    try:L.save(root,{"kind":"image","name":"Over quota","image":image});ok(False,"video included in quota")
    except ValueError:ok(True,"video included in quota")
finally:L.MAX_BYTES=old_limit
L.delete(root,video["id"])
ok(not L.list_entries(root,"video"),"video deletion")
done("test_asset_library")
