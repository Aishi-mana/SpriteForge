"""CPU-only tests of model detection and compatibility."""
from _common import *
from engine import model_families as mf
import struct
d=tmpdir()
def make(name,keys,meta=None):
    p=d/name
    h={k:{"dtype":"F16","shape":[1],"data_offsets":[2*i,2*i+2]} for i,k in enumerate(keys)}
    if meta:h["__metadata__"]=meta
    raw=json.dumps(h).encode()
    p.write_bytes(struct.pack("<Q",len(raw))+raw+b"\0"*(2*len(keys)))
    return p
l=make("neta.safetensors",["model.diffusion_model.noise_refiner.0.attn.qkv.weight"])
ok(mf.identify(l)=="lumina2" and not mf.describe(l)["supported"],"Lumina checkpoint detected; missing local components flagged")
folder=d/"NetaYume";folder.mkdir();(folder/"model_index.json").write_text('{"_class_name":"Lumina2Pipeline"}')
ok(mf.describe(folder)["supported"] and not mf.describe(folder)["reference"],"local Lumina folder offered for text generation")
base=d/"Lumina2-base";base.mkdir();(base/"model_index.json").write_text('{"_class_name":"Lumina2Pipeline"}')
ok(mf.describe(l)["supported"],"compatible single-file route offered with base")
a=make("adapter.safetensors",["transformer.layers.0.attn.to_q.lora_A.weight"],{"ss_base_model_version":"lumina2"})
ok(mf.identify(a,True)=="lumina2","adapter metadata identifies family")
ok(mf.compatibility("lumina2","sdxl")=="incompatible" and mf.compatibility("lumina2","lumina2")=="match","families do not mix")
ok(mf.compatibility("sdxl","unknown")=="unknown","ambiguous adapter unverified")
try:
    mf.check_lora(folder,d,"missing.safetensors")
    ok(False,"missing adapter rejected")
except ValueError:ok(True,"missing adapter rejected")
done("test_model_families")
