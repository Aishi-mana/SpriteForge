"""CPU-only per-layer deformation, legacy defaults, persistence and independent springs."""
from _common import *
from engine import modular as M, modular_rig as R, layer_motion as L, rig
from PIL import Image
body,joints,_=synth_sprite()
w,h=body.size
cape=Image.new("RGBA",(w,h));cape.paste((251,2,199,255),(4,15,11,46))
coat=Image.new("RGBA",(w,h));coat.paste((25,230,80,255),(27,16,31,34))
recipe={"width":w,"height":h,"pixel":True,"layers":[
    {"name":"Cape","category":"other","attachment":"torso","image":M.png_uri(cape)},
    {"name":"Base","category":"body","image":M.png_uri(body)},
    {"name":"Sleeve","category":"outfit","image":M.png_uri(coat)}]}
clean,_=M.validate(recipe)
ok(all(l["motion"]["mode"]=="rigid" for l in clean["layers"]),"legacy layers retain rigid defaults")
d=R.describe(recipe);recipe["rig"]={"body_key":d["body_key"],"joints":joints}
base,_=R.render(recipe,"run",6)
recipe["layers"][0]["motion"]={"mode":"spring","preset":"cape","segments":3,"anchor_x":.9,"anchor_y":0}
recipe["layers"][2]["motion"]={"mode":"soft","softness":70}
clean,_=M.validate(recipe)
ok(clean["layers"][0]["motion"]["segments"]==3 and clean["layers"][2]["motion"]["softness"]==70,"motion settings persisted")
pt=L.spring_geometry(np.asarray(cape),clean["layers"][0]["motion"],rig.SEC_DEFAULTS["cape"])
ok(pt is not None and pt["nseg"]==3,"chain created from layer pixels")
frames,meta=R.render(recipe,"run",6)
ok(len(frames)==6 and all(im.size==tuple(meta["size"]) for im in frames),"deformable clip size")
ok(any(a.tobytes()!=b.tobytes() for a,b in zip(base,frames)),"motion differs from rigid")
ok(R.describe(recipe)["saved_rig"],"motion changes preserve body rig")
ok(M.render(recipe).tobytes()==M.render(clean).tobytes(),"static assembly unchanged")
try:M.motion_settings({"mode":"spring","segments":7});ok(False,"invalid segments")
except ValueError:ok(True,"invalid segments rejected")
recipe["layers"][2]["attachment"]="head"
try:M.validate(recipe);ok(False,"invalid soft attachment")
except ValueError:ok(True,"soft requires auto bone splitting")
done("test_layer_motion")
