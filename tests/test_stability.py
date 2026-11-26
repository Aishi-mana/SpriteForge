"""GPU-free thread isolation and worker cleanup checks."""
from _common import *
from engine import generate as G, local_runtime as L, rig
from unittest.mock import patch
import threading
seen=[]
G.set_sampler("euler")
G._job_context.progress=lambda a,b:seen.append((a,b))
def worker():
    G.set_sampler("dpmpp_2m_karras")
    G._progress(8,9)
    ok(G._job_context.sampler=="dpmpp_2m_karras","second thread sampler")
t=threading.Thread(target=worker);t.start();t.join()
G._progress(1,2)
ok(G._job_context.sampler=="euler" and seen==[(1,2)],"sampler and progress isolated by thread")
G._job_context.cancelled=lambda:True
try:G._check_cancelled();ok(False,"cancelled job")
except RuntimeError:ok(True,"cancelled job rejected before launch")
G._job_context.cancelled=None
root=tmpdir()
class Child:
    returncode=0
    def poll(self):return 0
def launch(args,**kw):
    request=Path(args[-1])
    Image.new("RGB",(16,16),"blue").save(request.parent/"image.png")
    return Child()
with patch.object(L,"ROOT",root),patch.object(L.subprocess,"Popen",side_effect=launch):
    im=L.run("fake-python",{"backend":"qwen","steps":4})
    ok(im.size==(16,16) and not list((root/"local-image-jobs").iterdir()),"successful worker scratch removed")
class Failed(Child):
    returncode=1
with patch.object(L,"ROOT",root),patch.object(L.subprocess,"Popen",return_value=Failed()):
    try:L.run("fake-python",{"backend":"neta","steps":20,"reference":"private"});ok(False,"failure")
    except RuntimeError:ok(True,"worker failure surfaced")
job=next((root/"local-image-jobs").iterdir())
ok((job/"job.log").is_file() and not (job/"request.json").exists(),"failed worker log retained without input")
sp,j,ov=synth_sprite()
try:rig.render(sp,j,ov,"walk",1,ss=99);ok(False,"invalid sampling")
except ValueError:ok(True,"invalid sampling rejected")
done("test_stability")
