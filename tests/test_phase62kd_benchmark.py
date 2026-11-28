from _common import *
import subprocess

ui = (ROOT / "ui/index.html").read_text(encoding="utf-8")
for token in ('id="ffBenchPanel"', 'id="ffBenchLastRun"', 'onclick="ffBenchOpen()"',
              'id="ffADSpeed"', 'value="8">Quick preview', 'value="20">Quality comparison',
              "FF.videoRunReference===result.reference", "FF.videoRun?.ticket===ticket",
              "const started=performance.now()", "const extractedStart=performance.now()",
              "timing_source:source?'request wall time'", "version:2,candidates:rows",
              "FF.benchSource=null;ffBenchClear()", "const source=ffBenchSource(d)"):
    ok(token in ui, "benchmark wiring: " + token)
# Run actual UI helpers with minimal DOM stubs.
parts = []
for name in ("ffADSpeedChanged", "ffADSpeedSync", "ffBenchSource", "ffBenchLabelFor", "ffBenchOpen"):
    start = ui.index("function " + name + "(")
    end = ui.index("\n", start)
    parts.append(ui[start:end])
script = """
const assert = require('node:assert/strict');
const nodes = {};
const $ = id => nodes[id] ||= {value:'',placeholder:'',scrollIntoView(){}};
const doc = {frames:['a']};
const FF = {doc,benchSource:{doc,run:{model:'animatediff/base/v2',profile:'balanced',steps:12,seconds:5.2}}};
""" + "\n".join(parts) + """
assert.equal(ffBenchSource(doc), FF.benchSource);
assert.equal(ffBenchSource({...doc}), null);
ffBenchOpen();
assert.equal($('ffBenchSeconds').value, '');
assert.equal($('ffBenchSeconds').placeholder, '5.2');
assert.match($('ffBenchLabel').placeholder,/balanced.*12 steps/);
FF.doc = {...doc};
ffBenchOpen();
assert.equal($('ffBenchSeconds').placeholder, 'Unknown');
$('ffADSpeed').value = '8'; ffADSpeedChanged();
assert.equal($('ffVideoSteps').value, '8');
$('ffVideoSteps').value = '17'; ffADSpeedSync();
assert.equal($('ffADSpeed').value, 'custom');
$('ffADSpeed').value = 'custom'; ffADSpeedChanged();
assert.equal($('ffVideoSteps').value, '17');
"""
r = subprocess.run(["node","-e",script],capture_output=True,text=True)
ok(r.returncode==0, "runtime benchmark provenance and sampling preset helpers: " + r.stderr)
done("test_phase62kd_benchmark")
