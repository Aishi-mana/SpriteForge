"""Retargeting preserves destination geometry/skin while transferring clips and contacts."""
from _common import *
from engine import custom_skeleton as C,custom_retarget as R,custom_timeline as T,custom_ik as I,projects
import copy
s=C.preset("chain")
s["timeline"]={"name":"wave","count":5,"fps":12,"loop":False,"tracks":{"segment_3":[{"frame":0,"angle":10},{"frame":4,"angle":45,"curve":"ease"}]}}
s["ik"]=[{"end":"segment_2","target":[.43,.62],"max_bend":179,
          "keys":[{"frame":0,"target":[.43,.62]},{"frame":4,"target":[.44,.62]}],
          "locks":[{"start":1,"end":3,"target":[.43,.62]}]}]
s=C.validate(s)
d=copy.deepcopy(C.preset("chain"))
# Rename the destination IDs and change its rest dimensions and manual pose.
for b in d["bones"]:
    b["id"]="d_"+b["id"]
    if b["parent"]:b["parent"]="d_"+b["parent"]
    b["tail"]=[.1+.8*b["tail"][0],b["tail"][1]]
d["root_head"]=[.1+.8*d["root_head"][0],d["root_head"][1]]
d["bones"][2]["angle"]=7
d["skin"]={"mode":"weighted","resolution":16,"strokes":[{"bone":"d_root","x":.4,"y":.5,"radius":.1,"value":1,"strength":.7}]}
d=C.validate(d);before=copy.deepcopy(d)
mapping=R.suggest(s,d)["mapping"]
ok(len(mapping)==4 and mapping["segment_2"]=="d_segment_2","display-name bone suggestions")
out=R.transfer(s,d,mapping,[100,100],[200,100],True,"limb",2)
p=out["profile"];report=out["report"]
ok(d==before and p["bones"]==d["bones"] and p["skin"]==d["skin"],"destination rest geometry, manual pose and weights preserved")
ok(p["timeline"]["tracks"]["d_segment_3"]==s["timeline"]["tracks"]["segment_3"],"rotation keys and curves remapped")
ok(p["timeline"]["fps"]==12 and not p["timeline"]["loop"] and p["timeline"]["count"]==5,"timing preserved")
ok(report["ik_chains"]==1 and report["contact_ranges"]==1,"IK and foot contacts transferred")
lock=p["ik"][0]["locks"][0]
ok(lock["start"]==1 and lock["end"]==3 and abs(lock["target"][0]-(.1+.8*.43))<1e-7,"limb-scaled fixed contact position")
for frame in range(1,4):
    _,_,rr=I.solve(T.pose(p,frame),(200,100),frame)
    ok(rr[0]["locked"] and rr[0]["error"]<1e-5,"destination contact solved "+str(frame))
ok(out["source"]["size"]==[100,100] and out["destination"]["size"]==[200,100],"paired geometry preview")
canvas=R.transfer(s,d,mapping,[100,100],[200,100],True,"canvas")["profile"]
ok(canvas["ik"][0]["locks"][0]["target"]==s["ik"][0]["locks"][0]["target"],"canvas target option")
partial=R.transfer(s,d,{"segment_3":"d_segment_3"},[100,100],[200,100])
ok(partial["report"]["skipped_ik"]==["segment_2"] and partial["report"]["hierarchy_mismatches"],"incomplete mapping reported")
try:R.transfer(s,d,{"root":"d_root","segment_3":"d_root"},[100,100],[200,100]);ok(False,"duplicate")
except ValueError:ok(True,"duplicate destination rejected")
try:R.transfer(s,d,{"root":"d_root"},[100,100],[200,100]);ok(False,"no tracks")
except ValueError:ok(True,"mapping without animated data rejected")
im=Image.new("RGBA",(200,100));im.paste((20,150,180,255),(25,44,170,56))
frames,meta=T.render(data_url(im),p,8,frame=2)
ok(frames[0].size==(216,116),"retargeted timeline renders with destination weights")
root=tmpdir();projects.save(root,"Retarget",{"custom_skeleton":p,"images":{"customrig":data_url(im)}})
ok(projects.load(root,"Retarget")["custom_skeleton"]==p,"retargeted clip persists")
done("test_custom_retarget")
