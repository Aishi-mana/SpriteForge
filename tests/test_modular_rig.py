"""CPU-only attachment behavior and reusable body rig."""
from _common import *
from engine import modular as M, modular_rig as R, rig
from PIL import Image
body,joints,ovr=synth_sprite()
w,h=body.size
hat=Image.new("RGBA",(w,h));hat.paste((251,2,199,255),(w//2-3,0,w//2+3,6))
recipe={"width":w,"height":h,"pixel":True,"layers":[{"name":"Body","category":"body","image":M.png_uri(body)},{"name":"Hat","category":"accessory","attachment":"head","image":M.png_uri(hat)}]}
d=R.describe(recipe)
recipe["rig"]={"body_key":d["body_key"],"joints":d["joints"]}
ok(R.describe(recipe)["saved_rig"],"body rig saved")
frames,meta=R.render(recipe,"walk",4)
ok(len(frames)==4 and frames[0].size==tuple(meta["size"]),"modular animation returns normal frames")
ok(any(np.any(np.asarray(f)[...,0]==251) for f in frames),"attachment color survives body palette")
recipe["layers"][1]["attachment"]="r_arm_l"
ok(R.describe(recipe)["saved_rig"],"equipment swap preserves body rig")
other,_=R.render(recipe,"walk",4)
ok(any(a.tobytes()!=b.tobytes() for a,b in zip(frames,other)),"different bone changes layer motion")
recipe["layers"][0]["x"]=1
ok(not R.describe(recipe)["saved_rig"],"body transform invalidates stored rig")
clean,_=M.validate(recipe)
ok(clean["layers"][1]["attachment"]=="r_arm_l" and clean["rig"]==recipe["rig"],"recipe persists attachment and rig")
done("test_modular_rig")
