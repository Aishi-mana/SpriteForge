from _common import *
from engine import rig
sp,j,ov=synth_sprite()
end={k:[v[0]+4,v[1]-2] for k,v in j.items()}
keys=[{"t":0,"joints":j},{"t":1,"joints":end}]
frames,meta=rig.render(sp,j,ov,"custom",3,keyframes=keys)
ok(len(frames)==3,"custom clip renders")
for i, t in enumerate((0,.5,1)):
    p=meta["joints"][i]["neck"]
    ok(abs(p[0]-(j["neck"][0]+meta["pad"]+4*t))<.01,"interpolated neck pivot")
try:
    rig.custom_keys([keys[0],keys[0]])
    ok(False,"duplicate times rejected")
except ValueError:
    ok(True,"duplicate times rejected")
done("test_custom_rig")
