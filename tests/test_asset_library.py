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
done("test_asset_library")
