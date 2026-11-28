// Run with node tests/test_direct_animation.js
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'../ui/index.html'),'utf8'),ctx=vm.createContext({});
vm.runInContext(html.split('/*DA64-BEGIN*/')[1].split('/*DA64-END*/')[0],ctx);
const source={frames:['a','b','c'],fps:12,pivot:[4,8],locked_frames:[1],combat:[{frame:2}],directions:{N:{frames:['n']}}};
const edited=ctx.da64Build(source,new Map([[0,'x'],[2,'z']]));
assert.deepEqual(Array.from(edited.frames),['x','b','z']);
assert.deepEqual(source.frames,['a','b','c']);
assert.equal(edited.fps,12);
assert.equal(edited.pivot,source.pivot);
assert.equal(edited.combat,source.combat);
assert.equal(edited.directions,source.directions);
assert.throws(()=>ctx.da64Build(source,new Map([[1,'y']])),/locked/);
assert.throws(()=>ctx.da64Build(source,new Map([[3,'y']])),/Invalid/);
console.log('direct animation source preservation checks passed');
