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
from types import SimpleNamespace
calls=[]
cuda=SimpleNamespace(is_available=lambda:True,mem_get_info=lambda i:(3*2**30,8*2**30),get_device_name=lambda i:"Fake GPU",memory_allocated=lambda i:2**30,memory_reserved=lambda i:2*2**30,empty_cache=lambda:calls.append("released"))
fake=SimpleNamespace(cuda=cuda)
G._cache.update(key=("fake.safetensors",),pipe=object())
status=G.resource_status(fake)
ok(status["cuda"] and status["recommended_size"]==640 and status["memory"]["free"]==3*2**30 and status["checkpoint"]=="fake.safetensors","8 GiB resource reporting and recommendation")
with G._lock:
    try:G.release_resources(True,fake);ok(False,"busy release")
    except RuntimeError:ok(G._cache["pipe"] is not None and not calls,"busy release cannot unload active model")
G.release_resources(False,fake)
ok(G._cache["pipe"] is not None and calls==["released"],"cache release retains pipeline")
G.release_resources(True,fake)
ok(G._cache["pipe"] is None and G._cache["key"] is None and calls==["released","released"],"unload clears pipeline")
cpu=SimpleNamespace(cuda=SimpleNamespace(is_available=lambda:False))
ok(G.resource_status(cpu)["memory"] is None and not G.resource_status(cpu)["cuda"],"CPU-only status tolerates missing CUDA")
# Cache identity includes adapter directories only when relevant.
k=G._pipeline_key
ok(k("ckpt","lora",1,"a",True)!=k("ckpt","lora",1,"b",True),"LoRA directory change invalidates pipeline")
ok(k("ckpt",None,1,"a",False)==k("ckpt",None,1,"b",False),"unused LoRA directory does not force reload")
ok(k("ckpt",None,1,None,False,True,"a")!=k("ckpt",None,1,None,False,True,"b"),"ControlNet directory change invalidates pipeline")
ok(k("ckpt",None,1,None,False)!=k("ckpt",None,1,None,False,inpaint=True),"generation and inpaint cache isolated")
class Gone(Exception):pass
class Denied(Exception):pass
class Proc:
    def memory_info(self):return SimpleNamespace(rss=100)
    def children(self,recursive=False):return [self,SimpleNamespace(memory_info=lambda:(_ for _ in ()).throw(Gone()))]
ps=SimpleNamespace(Process=Proc,virtual_memory=lambda:SimpleNamespace(available=500,total=1000),NoSuchProcess=Gone,AccessDenied=Denied)
ram=G.ram_status(ps)
ok(ram=={"process_rss":100,"child_rss":100,"children":2,"children_measured":1,"available":500,"total":1000},"RAM status tolerates exited worker")
ok(G.ram_status(SimpleNamespace(Process=lambda:None)) is None,"RAM probe failure is optional")
ok(status["memory"]["reserved_unused"]==2**30,"unused allocator reserve reported")
done("test_stability")
