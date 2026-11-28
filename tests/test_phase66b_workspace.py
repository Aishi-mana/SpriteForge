"""Phase 66B workspace navigation and preference regressions."""
from _common import *
import re, shutil, subprocess
ui=(ROOT / "ui/index.html").read_text(encoding="utf-8")
markup=ui.split("<script>",1)[0]
nav=re.search(r'<nav class="tabs sf62nav".*?</nav>',markup,re.S).group()
ok(sorted(map(int,re.findall(r'id="t(\d+)"',nav)))==list(range(1,21)),"all workspace IDs preserved")
ok(markup.index(nav)<markup.index('id="ws66Project"')<markup.index('id="gpu"'),"navigation and project precede technical setup")
project=markup.split('id="ws66Project"',1)[1].split('</section>',1)[0]
ok('onclick="saveProject()"' in project and 'onclick="loadProject()"' in project,"project save/load remain directly accessible")
tools=markup.split('id="ws58Tools"',1)[1].split('</div>',1)[0]
ok(all(x in tools for x in ('tab(12)','tab(9)','ws66ProjectOpen()','ws66PinCurrent()')),"global shortcuts preserved in focus mode")
sampling=markup.split('id="ws66Sampling"',1)[1].split('</details>',1)[0]
ok(all('id="'+x+'"' in sampling for x in ('lw','seed','steps','cfg','sampler')) and 'id="bg"' not in sampling,"only optional sampling fields folded")
ok('ws66Record(n)' in ui and 'ws66Init();' in ui,"tab navigation and initialization wired")
node=shutil.which("node")
if node:
    script=ui.split("/*WS66-START*/",1)[1].split("/*WS66-END*/",1)[0]
    runner=tmpdir() / "ws66.js"
    runner.write_text(script+"""
const assert=require('node:assert/strict');
assert.deepEqual(ws66Normalize(null),{pinned:[],recent:[],sampling:false});
assert.deepEqual(ws66Normalize({pinned:[20,4,20,0,21,'1'],recent:[9,1,2,3,4,5,9],sampling:true}),{pinned:[20,4],recent:[9,1,2,3,4],sampling:true});
assert.deepEqual(ws66Normalize({pinned:'bad',recent:{},sampling:'true'}),{pinned:[],recent:[],sampling:false});
let mode=20;let storage={};const localStorage={setItem:(k,v)=>storage[k]=v};
function element(){return {children:[],textContent:'',replaceChildren(){this.children=[]},appendChild(x){this.children.push(x)},setAttribute(k,v){this[k]=v},removeAttribute(k){delete this[k]}}}
const elements={};const $=id=>elements[id]??=element();const document={createElement:()=>element()};
$('t20').textContent='AI full-frame animation';$('t4').textContent='Rig animation';
ws66Record(20);ws66PinCurrent();assert.deepEqual(WS66.pinned,[20]);assert.equal($('ws66Pin')['aria-pressed'],'true');
mode=4;ws66Record(4);ws66PinCurrent();assert.deepEqual(WS66.recent,[4,20]);assert.deepEqual(WS66.pinned,[20,4]);assert.equal($('t4')['aria-current'],'page');assert.equal($('t20')['aria-current'],undefined);
ws66PinCurrent();assert.deepEqual(WS66.pinned,[20]);assert.deepEqual(JSON.parse(storage[WS66_KEY]).pinned,[20]);assert.equal($('ws66Favorites').children[1].textContent,'AI full-frame animation');
""",encoding="utf-8")
    result=subprocess.run([node,str(runner)],capture_output=True,text=True)
    ok(result.returncode==0,"workspace preference behavior: "+result.stderr)
done("test_phase66b_workspace")
