const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const html=fs.readFileSync(path.join(__dirname,'../../ui/index.html'),'utf8');
const code=html.split('/*STUDIO61-START*/')[1].split('/*STUDIO61-END*/')[0];
const run=new Function(`let profile={},CA61={master:null},SP61={approved:null},ptBase=null,ptRes=[],aSrc=null,joints=null,CS={source:null},ares={};const ci61Profile=()=>profile;`+code+`return {state:studio61State,set(p){profile=p},CA61,SP61,CS,rig(u,j,r){aSrc=u;joints=j;ares=r},portrait(u,r){ptBase=u;ptRes=r}};`)();
assert.equal(run.state().identity,false);assert.equal(run.state().rig,false);assert.equal(run.state().clips,0);console.log('ok empty studio');
run.set({name:'Knight',active_outfit:'Armor'});run.CA61.master='art';run.SP61.approved='sprite';run.rig('old',{}, {walk:{}});assert.equal(run.state().name,'Knight');assert.equal(run.state().master,true);assert.equal(run.state().rig,false);assert.equal(run.state().clips,0);console.log('ok unrelated rig not counted');
run.rig('sprite',{}, {walk:{},idle:{}});run.portrait('portrait',[{name:'neutral'},{name:'happy'}]);assert.equal(run.state().rig,true);assert.equal(run.state().clips,2);assert.equal(run.state().expressions,1);console.log('ok linked source and expression state');
assert(html.includes('id="t16"'));assert(html.includes("['Character Studio',()=>tab(16)]"));console.log('ok workspace navigation');
console.log('ALL PASSED');
