"""Batch recipe planning, grouped persistent jobs, safe animation export."""
from _common import *
from engine import production as P,jobs,projects,custom_skeleton as C
import copy
body={"name":"heroes","params":{"prompt":"same costume style","seed":20,"checkpoint":"x"},"characters":[{"name":"Knight","prompt":"blue armor"},{"name":"Mage","prompt":"violet robe"}]}
name,rows=P.plan(body)
ok(name=="heroes" and [r["params"]["seed"] for r in rows]==[20,21],"sequential fixed seeds")
ok(rows[0]["params"]["prompt"]=="same costume style, blue armor" and rows[0]["params"]["n"]==1,"shared appearance prefix and single image jobs")
try:P.plan({**body,"characters":[body["characters"][0]]*2});ok(False,"duplicate")
except ValueError:ok(True,"duplicate names rejected")
root=tmpdir()
def ex(kind,p,inputs,progress):
    if "blue" in p["prompt"]:raise RuntimeError("pretend error")
    return [{"sprite":data_url(Image.new("RGBA",(16,16),(10,20,30,255))),"info":{"seed":p["seed"]}}]
m=jobs.Manager(root,ex);m.set_paused(True);added=m.add_batch(rows,"batch1",name)
ok(len(added)==2 and len(m.batches()[0]["rows"])==2,"batch queued with group metadata")
m.set_paused(False);m.wait_idle(10)
ok([r["status"] for r in m.batches()[0]["rows"]]==["error","done"],"one failure does not stop remaining jobs")
m.set_paused(True);retry=m.rerun(added[0]["id"])
ok(m.batches()[0]["rows"][0]["id"]==retry["id"],"retry keeps row identity")
m.shutdown()
m2=jobs.Manager(root,ex,start_worker=False)
ok(m2.batches()[0]["rows"][0]["status"]=="interrupted","batch history recovered")
m2.shutdown()
p=C.preset("chain");p["timeline"]={"name":"wave","count":2,"tracks":{"tip":[{"frame":0,"angle":0},{"frame":1,"angle":20}]}}
im=data_url(Image.new("RGBA",(32,32),(30,40,100,255)))
projects.save(root,"Source",{"custom_skeleton":p,"images":{"customrig":im},"settings":{"csPad":0}})
d=C.preset("chain")
projects.save(root,"Destination",{"custom_skeleton":d,"images":{"customrig":im},"settings":{"csPad":0}})
opts={"gif":False,"godot":False,"unity":False}
out=P.animation(root,{"source":"Source","target":"Destination","options":opts})
ok(out["status"]=="done" and out["frames"]==2 and Path(out["dir"]).is_dir(),"retarget and batch export")
ok(projects.load(root,"Destination")["custom_skeleton"]==C.validate(d),"destination project not modified")
again=P.animation(root,{"source":"Source","target":"Destination","options":opts})
ok(again["dir"]!=out["dir"],"unique export directories")
done("test_production")
