"""CPU regression tests for manual blend, occlusion, ordering and persistence."""
from _common import *
from engine import modular as M, modular_rig as R, layer_motion as L, softmesh, layer_export as E
body,joints,_=synth_sprite()
w,h=body.size
asset=Image.new("RGBA",(w,h),(0,0,0,0));asset.paste((249,0,190,255),(7,15,34,36))
weights={"bone_a":"torso","bone_b":"r_arm_l","base":0,"strokes":[[.75,.4,.2,1]]}
settings=M.weight_settings(weights)
mesh=L.weighted_mesh(np.asarray(asset),settings,False)
ok(mesh[2].min()==0 and mesh[2].max()>.8,"painted B influence with untouched A region")
A=np.eye(3);B=np.eye(3);B[0,2]=5
im=softmesh.deform(mesh,A,B,0,1,(w,h),False)
ok(im.tobytes()!=asset.tobytes(),"two-bone weighted motion changes pixels")
recipe={"width":w,"height":h,"pixel":True,"layers":[
 {"name":"Body","category":"body","image":M.png_uri(body)},
 {"name":"Coat","category":"outfit","attachment":"auto","image":M.png_uri(asset),
  "motion":{"mode":"weighted","weights":weights}}]}
d=R.describe(recipe);recipe["rig"]={"body_key":d["body_key"],"joints":joints}
a,_=R.render(recipe,"walk",3)
recipe["layers"][1]["occlusion"]={"depth":"front","bones":["r_arm_u","r_arm_l"]}
b,_=R.render(recipe,"walk",3)
ok(any(x.tobytes()!=y.tobytes() for x,y in zip(a,b)),"body-bone occlusion changes overlap")
ok(R.describe(recipe)["saved_rig"],"weight and depth changes retain body rig")
clean,_=M.validate(recipe)
ok(clean["layers"][1]["motion"]["weights"]==settings,"manual weight recipe preserved")
recipe["layers"][1]["occlusion"]["depth"]="behind"
ok(M.layer_order(recipe["layers"],[1],0)==[1,0],"explicit behind override")
out=E.export(recipe,"walk",2,10,"right","r","r",1,0,0,"weights",tmpdir(),columns=2)
manifest=json.loads((Path(out["dir"])/"manifest.json").read_text())
ok(manifest["layers"][0]["id"]=="layer_01" and manifest["layers"][1]["id"]=="layer_00","export uses explicit depth order")
try:M.weight_settings({"bone_a":"head","bone_b":"head"});ok(False,"duplicate bones")
except ValueError:ok(True,"duplicate bones rejected")
try:M.weight_settings({"strokes":[[0,0,.2,1]]*193});ok(False,"stamp cap")
except ValueError:ok(True,"stamp cap")
done("test_layer_weights")
