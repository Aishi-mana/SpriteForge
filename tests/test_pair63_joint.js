// Run with node tests/test_pair63_joint.js
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'../ui/index.html'),'utf8');
const ctx=vm.createContext({});
vm.runInContext(html.split('/*PAIR63-JOINT-BEGIN*/')[1].split('/*PAIR63-JOINT-END*/')[0],ctx);
const mask=ctx.pair63JointMask(4,1,50);
assert.deepEqual(Array.from(mask),[1,1,2,2]);
const raw=new Uint8ClampedArray([255,0,0,255,255,0,0,128,0,0,255,255,0,0,255,255]);
assert.deepEqual(Array.from(ctx.pair63JointPixels(raw,mask,1)),[255,0,0,255,255,0,0,128,0,0,0,0,0,0,0,0]);
ctx.pair63JointPaint(mask,4,1,1,0,0,2);
assert.deepEqual(Array.from(mask),[1,2,2,2]);
ctx.pair63JointPaint(mask,4,1,3,0,0,0);
assert.equal(ctx.pair63JointPixels(raw,mask,2)[15],0);
assert.equal(raw[15],255);
console.log('joint mask regression checks passed');
