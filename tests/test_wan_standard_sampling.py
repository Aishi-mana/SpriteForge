from _common import *
import subprocess

ui = (ROOT / "ui/index.html").read_text(encoding="utf-8")
workflow = ui.split('id="ffEasyMode"', 1)[1].split('</select>', 1)[0]
ok(workflow.split('<option', 1)[1].startswith(' value="standard" selected>Standard AI animation</option>'), "standard is first and selected by default")
ok(ui.index('id="ffWanSamplingSummary"') < ui.index('id="ffTechnical"'), "sampling summary is visible outside advanced")
parts = []
for name in ("ffEasyChanged", "ffWanEndpointActive", "ffWanSamplingSummary"):
    start = ui.index("function " + name + "(")
    parts.append(ui[start:ui.index("\n", start)])
script = """
const assert = require('node:assert/strict');
const nodes = {};
const $ = id => nodes[id] ||= {value:'',options:[],hidden:false,textContent:''};
function ffADGate(){}
function ffMotionMethodChanged(){}
function ffVideoDefaults(){throw Error('same model must not reset unrelated settings')}
function ffWanGuideChanged(){ffWanSamplingSummary()}
function ffPresetSync(){}
""" + "\n".join(parts) + """
$('ffVideoModel').value='wan22-gguf';
$('ffVideoModel').options=[{value:'wan22-gguf'}];
$('ffPreset').value='idle_minimal';
$('ffPrompt').value='subtle breathing';
$('ffWanConditioning').value='custom';
const file={name:'end.png'};
$('ffWanEndFile').files=[file];
$('ffVideoCount').value=33;
function select(mode, quality, steps){
    $('ffEasyMode').value=mode;
    ffEasyChanged();
    assert.equal($('ffWanQuality').value,quality);
    assert.equal(Number($('ffVideoSteps').value),steps);
    assert.match($('ffWanSamplingSummary').textContent,new RegExp(steps+' steps'));
}
select('guided','native',20);
select('standard','fast',4);
select('guided','native',20);
select('fastloop','fast',4);
$('ffVideoSteps').value=20;
select('standard','fast',4);
assert.equal($('ffWanConditioning').value,'custom');
assert.equal($('ffWanEndFile').files[0],file);
assert.equal($('ffVideoCount').value,33);
assert.equal($('ffPrompt').value,'subtle breathing');
assert.equal($('ffWanSamplingSummary').hidden,false);
$('ffVideoSteps').value=6;ffWanSamplingSummary();
assert.match($('ffWanSamplingSummary').textContent,/6 steps/);
$('ffVideoModel').value='wan22-fun5b';ffWanSamplingSummary();
assert.equal($('ffWanSamplingSummary').hidden,true);
"""
r = subprocess.run(["node","-e",script],capture_output=True,text=True)
ok(r.returncode == 0, "actual workflow switch restores four steps and retains endpoint: " + r.stderr)
done("test_wan_standard_sampling")
