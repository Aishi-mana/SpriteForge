const assert=require('assert/strict'),fs=require('fs'),path=require('path');
const html=fs.readFileSync(path.join(__dirname,'../../ui/index.html'),'utf8');
const code=html.split('/*AW61-START*/')[1].split('/*AW61-END*/')[0];
const run=new Function(`let SP61={approved:null},CA61={busy:false},CS={busy:false,source:null},endpointBusy=false,aSrc='old',ares={walk:{}},customKeys=[],endpoint={},refURL=null;let permit=false,calls=[],els={};const $=id=>els[id]??=( {value:'walk',textContent:''});const confirm=()=>permit;function tab(n){calls.push(n)}function markDirty(){}function animChanged(){calls.push('clip')}function setAnim(u){aSrc=u;calls.push(u)}function useRef(u){refURL=u;calls.push('ref')}function loadPreset(v){calls.push(v)}const CLIPS=['idle','walk','run','attack','jump'];`+code.replace(/function aw61ResetRig\(\)\{[^\n]*\}/,'function aw61ResetRig(){ares={};calls.push("reset")}')+`return {aw61Rig,aw61Pack,aw61Ready,SP61,CA61,calls,els,allow:()=>permit=true,getResults:()=>ares};`)();
assert.equal(run.aw61Ready(),false);run.SP61.approved='new';assert.equal(run.aw61Rig(),false);assert.equal(run.getResults().walk!==undefined,true);console.log('ok missing source and cancelled replacement');
run.allow();assert.equal(run.aw61Rig('walk'),true);assert.deepEqual(run.calls,['reset','new','clip']);assert.deepEqual(run.getResults(),{});console.log('ok confirmed source replacement clears old clips');
run.aw61Pack();assert.equal(run.els.xc_idle.checked,true);assert.equal(run.els.xc_jump.checked,false);assert.equal(run.calls.filter(x=>x==='reset').length,1);console.log('ok starter pack and same-source reuse');
run.CA61.busy=true;assert.equal(run.aw61Ready(),false);console.log('ok busy guard');
console.log('ALL PASSED');
