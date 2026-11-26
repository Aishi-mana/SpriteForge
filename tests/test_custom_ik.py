"""Analytical limb IK, constraints, fixed contacts, timeline and persistence."""
from _common import *
from engine import custom_skeleton as C,custom_ik as I,custom_timeline as T,projects
p=C.preset("chain")
p["ik"]=[{"end":"segment_2","target":[.43,.72],"max_bend":179}]
p=C.validate(p)
solved,pts,report=I.solve(p,(100,80))
ok(report[0]["error"]<1e-6,"reachable target solved")
ok(abs(np.linalg.norm(np.array(pts["root"][1])-pts["root"][0])-15)<1e-6,"upper length preserved")
ok(np.allclose(pts["root"][1],pts["segment_2"][0]),"joint connected")
ok(p["bones"][0]["angle"]==0,"manual pose unchanged")
p["ik"][0]["bend"]=-1
_,other,_=I.solve(p,(100,80))
ok(not np.allclose(pts["root"][1],other["root"][1]),"opposite bend direction")
p["ik"][0]["target"]=[1.5,1.5]
_,_,r=I.solve(p,(100,80))
ok(r[0]["error"]>1,"unreachable target reported")
p["ik"][0]["target"]=[.43,.72]
p["timeline"]={"name":"contact","count":5,"fps":10,"loop":True,"tracks":{}}
p["ik"][0]["keys"]=[{"frame":0,"target":[.4,.4],"curve":"linear"},{"frame":4,"target":[.5,.6],"curve":"linear"}]
p["ik"][0]["locks"]=[{"start":1,"end":3,"target":[.43,.72]}]
p=C.validate(p)
ok(I.at_frame(p["ik"][0],2)==([.43,.72],True),"contact overrides target key")
for frame in range(1,4):
    _,_,r=I.solve(T.pose(p,frame),(100,80),frame)
    ok(r[0]["locked"] and r[0]["error"]<1e-6,"fixed target at frame "+str(frame))
im=Image.new("RGBA",(100,80));im.paste((20,150,180,255),(15,35,85,46))
frames,meta=T.render(data_url(im),p,8)
ok(len(frames)==5 and frames[1].tobytes()==frames[3].tobytes(),"IK-only clip and locked contact")
p["skin"]={"mode":"weighted","resolution":16}
frames,_=T.render(data_url(im),p,8)
ok(frames[0].tobytes()!=frames[2].tobytes(),"weighted IK animation")
root=tmpdir();projects.save(root,"IK",{"custom_skeleton":p,"images":{"customrig":data_url(im)}})
ok(projects.load(root,"IK")["custom_skeleton"]==C.validate(p),"IK persistence")
bad=json.loads(json.dumps(p));bad["ik"][0]["locks"].append({"start":2,"end":4,"target":[.4,.5]})
try:C.validate(bad);ok(False,"overlap")
except ValueError:ok(True,"overlapping contact rejected")
bad=json.loads(json.dumps(p));bad["ik"].append({"end":"segment_3","target":[.5,.5]})
try:C.validate(bad);ok(False,"shared bones")
except ValueError:ok(True,"shared controlled bones rejected")
done("test_custom_ik")
