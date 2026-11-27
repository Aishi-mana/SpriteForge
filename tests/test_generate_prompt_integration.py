"""61N-D: CPU-only prompt parity at the runtime boundary, not image-quality testing."""
from _common import *
from unittest.mock import patch
from types import SimpleNamespace
install_fastapi_stubs()
from engine import main as M, generate as G, local_runtime as LR

# Stub torch entirely, including native pipeline seed generator; no weights or GPU.
fake_torch=SimpleNamespace(cuda=SimpleNamespace(empty_cache=lambda:None),
                           Generator=lambda *args:SimpleNamespace(manual_seed=lambda seed:seed))
received=[]
class Native:
    def __call__(self, **kw):
        received.append((kw["prompt"],kw["negative_prompt"]))
        return SimpleNamespace(images=[Image.new("RGB",(16,16))])
def request(ckpt,lora_dir,lora,lw,positive,negative,steps,cfg,seed,size,*args):
    received.append((positive,negative))
    return "python",{"seed":seed}
with patch.dict(sys.modules,{"torch":fake_torch}), patch.object(G,"_load",return_value=Native()), patch.object(G,"_apply_sampler"), patch.object(G.mf,"identify",return_value="sdxl"), patch.object(LR,"request",side_effect=request), patch.object(LR,"run",return_value=Image.new("RGB",(16,16))):
    for backend in (None,"neta","qwen"):
        with patch.object(LR,"route",return_value=backend):
            for style in ("pixel","anime","head_2","head_7"):
                for base in (False,True):
                    p=M.GenParams(prompt="standing adult character, front view" if not base else "neutral mannequin, front view",negative="extra fingers",checkpoint="mock",art_style=style,body_base=base,bg="green",seed=17)
                    view=M.generate_prompt_preview(p)
                    kind,art=M._generate_prompt_kind(p)
                    before=len(received)
                    G.generate("mock","","1","",""+p.prompt,p.negative,steps=1,seed=17,n=2,bg=p.bg,kind=kind,art_style=art)
                    ok(received[before:]==[(view["positive"],view["negative"])]*2,"preview equals runtime submission "+str(backend)+" "+style+" "+str(base))

# Legacy/default and non-character modes must not inherit the mannequin prompt.
for kind in ("tile","prop","icon","ui"):
    p=M.GenParams(prompt="stone",checkpoint="",body_base=True,kind=kind,art_style="head_3")
    v=M.generate_prompt_preview(p)
    ok(v["kind"]==kind and v["art_style"]=="pixel" and "mannequin" not in v["positive"],"non-character routing "+kind)
p=M.GenParams(prompt="blue armor and red cape",checkpoint="")
ok(M.generate_prompt_preview(p)["kind"]=="sprite" and p.body_base is False,"legacy Generate keeps explicit user subject")
done("test_generate_prompt_integration")
