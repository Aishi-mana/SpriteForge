"""CPU hierarchy validation, rigid pose preview and project persistence."""
from _common import *
from engine import custom_skeleton as C, projects
sp,_,_=synth_sprite()
for k in ("humanoid","quadruped","winged","chain"):
    p=C.preset(k);ok(C.validate(p)==p,k+" preset valid")
p=C.preset("chain")
im,pts=C.render(sp,p,0)
ok(im.tobytes()==sp.tobytes(),"zero rotations preserve source pixels")
p["bones"][0]["angle"]=45
p["bones"][1]["angle"]=-30
m,s=C.transforms(p,sp.size)
a,z=s["root"]
ok(np.allclose(m["root"]@np.r_[z,1],m["segment_2"]@np.r_[s["segment_2"][0],1]),"child stays connected after parent and local rotation")
im,pts=C.render(sp,p,32)
ok(im.size==(sp.width+64,sp.height+64) and im.getchannel("A").getbbox() is not None,"padded pose render")
ok(np.allclose(pts["root"][1],pts["segment_2"][0]),"posed endpoints connected")
bad=json.loads(json.dumps(p));bad["bones"][0]["parent"]="tip"
try:C.validate(bad);ok(False,"cycle")
except ValueError:ok(True,"cycle rejected")
bad=json.loads(json.dumps(p));bad["bones"][2]["parent"]="missing"
try:C.validate(bad);ok(False,"missing parent")
except ValueError:ok(True,"missing parent rejected")
bad=json.loads(json.dumps(p));bad["bones"][1]["tail"]=bad["bones"][0]["tail"]
try:C.validate(bad);ok(False,"zero-length bone")
except ValueError:ok(True,"zero-length bone rejected")
root=tmpdir();projects.save(root,"Custom",{"custom_skeleton":p,"images":{"customrig":data_url(sp)}})
d=projects.load(root,"Custom")
ok(d["custom_skeleton"]==C.validate(p) and from_url(d["images"]["customrig"]).tobytes()==sp.tobytes(),"custom profile and sprite project roundtrip")
done("test_custom_skeleton")
