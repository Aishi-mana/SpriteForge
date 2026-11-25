"""No model imports or GPU allocation: standalone request contract."""
from _common import *
from engine import local_runtime as lr
from PIL import Image
from unittest.mock import patch
import os
root=tmpdir()
models=root/"models"; (models/"checkpoints").mkdir(parents=True);(models/"diffusion_models").mkdir()
n=models/"checkpoints"/lr.NETA;n.touch()
q=models/"diffusion_models"/lr.QWEN;q.touch()
runtime=root/"comfy";(runtime/"comfy").mkdir(parents=True);(runtime/"comfy/sd.py").touch()
(runtime/"comfy_extras").mkdir();(runtime/"comfy_extras/nodes_qwen.py").touch()
py=root/"python.exe";py.touch()
with patch.dict(os.environ,{"SPRITEFORGE_COMFY_ROOT":str(runtime),"SPRITEFORGE_COMFY_PYTHON":str(py)}):
    ok(lr.readiness(n)==("neta",[]),"Neta runtime detected without loading weights")
    ok(len(lr.readiness(q)[1])==2,"Qwen missing encoder/VAE listed")
    for p in lr.qwen_files(models,q).values():p.parent.mkdir(parents=True,exist_ok=True);p.touch()
    ok(lr.readiness(q)==("qwen",[]),"Qwen split model layout ready")
    with patch("engine.model_families.check_lora"):
        exe,req=lr.request(n,models/"loras","",1,"clothed game character","text",20,4,42,1024,Image.new("RGBA",(64,64)),ip_scale=.7)
        ok(exe==py and req["backend"]=="neta" and abs(req["referenceStrength"]-.3)<1e-6,"Neta reference routed to denoise")
        _,req=lr.request(q,models/"loras","",1,"character","text",4,1,42,768,Image.new("RGBA",(64,64)))
        ok(req["backend"]=="qwen" and req["steps"]==4 and req["cfg"]==1 and "referenceStrength" not in req,"Qwen reference uses native conditioning")
        ok(req["width"]==768 and req["seed"]==42 and req["reference"].startswith("data:image/jpeg;base64,"),"bounded reference and settings")
    try:lr.run(py,{},cancelled=lambda:True);ok(False,"cancel preflight")
    except RuntimeError:ok(True,"cancel prevents worker launch")
done("test_local_runtime")
