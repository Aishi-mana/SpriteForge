from _common import *
from engine import wan_video as W
import subprocess

base = {"guidance":{"preset":"idle_minimal"}, "conditioning":"flf"}
same = W.settings(base)
ok(same["end_reference"] is None and "identical starting pose" in same["prompt"], "idle uses same start/end")
attack = W.settings({"guidance":{"preset":"attack","loop":True}, "conditioning":"flf", "end_reference":"target"})
ok(not attack["guidance"]["loop"] and "supplied ending pose" in attack["prompt"] and "Return to the starting pose" not in attack["prompt"], "custom combat target disables contradictory loop guidance")
ok(W.graph(attack)["i2v"]["inputs"]["end_image"] == ["ref2",0], "custom target uses first-last graph")
closed_attack = W.settings({"guidance":{"preset":"attack"}, "conditioning":"flf"})
ok("small motion cycle" not in closed_attack["prompt"] and "return to the supplied starting pose" in closed_attack["prompt"], "explicit same pose can support combat recovery")
free = W.settings({"guidance":{"preset":"attack"}, "conditioning":"i2v"})
ok(W.graph(free)["i2v"]["class_type"]=="WanImageToVideo", "free motion retains original graph")
for body in ({"conditioning":"i2v","end_reference":"target"},{"conditioning":"flf","end_reference":""}):
    try:
        W.settings({"prompt":"attack",**body})
        ok(False,"invalid target accepted")
    except ValueError:
        ok(True,"invalid target rejected")

ui = (ROOT / "ui/index.html").read_text(encoding="utf-8")
ok(ui.index('id="ffWanEndpoints"') < ui.index('id="ffTechnical"'), "ending pose controls visible outside advanced settings")
ok(ui.count('id="ffWanEndFile"') == 1 and 'id="ffWanEndPreview"' in ui, "single endpoint picker with preview")
ok('endpoint===\'custom\'?\'flf\':endpoint' in ui and "if(endpoint==='custom'&&!file)" in ui, "generation sends custom endpoint as FLF and requires image")
easy = ui[ui.index("function ffEasyChanged()"):ui.index("function ffWanEndpointMode(")]
ok("ffWanEndFile" not in easy and "ffWanConditioning" not in easy, "mode changes and refresh do not clear selected endpoint")
parts = []
for name in ("ffWanEndpointMode", "ffWanEndpointActive", "ffADGate"):
    start = ui.index("function " + name + "(")
    parts.append(ui[start:ui.index("\n",start)])
script = """
const assert = require('node:assert/strict');
const nodes = {};
const $ = id => nodes[id] ||= {value:'',files:[],disabled:false,title:''};
const FF = {};
""" + "\n".join(parts) + """
for(const p of ['idle','idle_minimal','alert','floating','weapon_ready'])assert.equal(ffWanEndpointMode('auto',p),'flf');
for(const p of ['attack','slash','walk','cast','custom'])assert.equal(ffWanEndpointMode('auto',p),'i2v');
assert.equal(ffWanEndpointMode('flf','attack'),'flf');
assert.equal(ffWanEndpointMode('custom','idle'),'custom');
assert.equal(ffWanEndpointMode('i2v','idle'),'i2v');
$('ffVideoModel').value='wan22-gguf';
$('ffWanConditioning').value='custom';ffADGate();
assert.equal($('ffGenerateMain').disabled,true);
$('ffWanEndFile').files=[{}];ffADGate();
assert.equal($('ffGenerateMain').disabled,false);
$('ffWanEndFile').files=[];$('ffVideoModel').value='wan22-fun5b';ffADGate();
assert.equal($('ffGenerateMain').disabled,false);
FF.videoBusy=true;ffADGate();assert.equal($('ffGenerateMain').disabled,true);
"""
r=subprocess.run(["node","-e",script],capture_output=True,text=True)
ok(r.returncode==0,"runtime endpoint selection and gate: "+r.stderr)
done("test_wan_visible_endpoints")
