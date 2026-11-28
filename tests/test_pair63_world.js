// Run with node tests/test_pair63_world.js
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'../ui/index.html'),'utf8');
const ctx=vm.createContext({});
const section=(name)=>html.split('/*'+name+'-BEGIN*/')[1].split('/*'+name+'-END*/')[0];
vm.runInContext(section('PAIR63-TIMING')+'\n'+html.match(/function pair63Effective\(a,i\)\{[^\n]+/)[0]+'\n'+section('PAIR63-WORLD'),ctx);
const base={x:256,y:300,z:0,start:0,end:3,visible:true,opacity:100,offset:0,speed:100,behavior:'loop',clip:{fps:4,frames:['x','y']}};
const a={...base,id:'actor_A',frame_overrides:[{frame:1,x:266,y:310,z:2}]},b={...base,id:'actor_B',z:1,start:1};
const s={width:512,height:384,count:4,fps:4,actors:[a,b]};
assert.deepEqual(Array.from(ctx.wpPairPoint(a,1,[100,200],2,[512,384])),[120,220]);
assert.equal(ctx.wpPairEntries(s,0,[100,200],1).length,1);
assert.deepEqual(Array.from(ctx.wpPairEntries(s,1,[100,200],1),e=>e.a.id),['actor_B','actor_A']);
assert.equal(ctx.wpPairEntries(s,1,[100,200],1)[0].frame,0);
assert.equal(ctx.wpPairEntries(s,1,[100,200],1)[1].frame,1);
console.log('paired world regression checks passed');
