// Run with node tests/test_direct_appearance.js
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'../ui/index.html'),'utf8'),ctx=vm.createContext({});
vm.runInContext(html.split('/*DA64-APPEARANCE-BEGIN*/')[1].split('/*DA64-APPEARANCE-END*/')[0],ctx);
const doc={frames:['a','b','c'],locked_frames:[1]};
assert.deepEqual(Array.from(ctx.da64AppearanceIndices(doc,2,2)),[2]);
assert.throws(()=>ctx.da64AppearanceIndices(doc,0,2),/locked/);
assert.throws(()=>ctx.da64AppearanceIndices(doc,2,3),/Invalid/);
const a=new Uint8ClampedArray([0,0,0,0,10,20,30,128,40,50,60,255]);
const b=new Uint8ClampedArray([255,0,0,255,200,100,50,255,0,0,0,0]);
assert.deepEqual(Array.from(ctx.da64AppearanceAlphaPixels(a,b)),[0,0,0,0,200,100,50,128,40,50,60,255]);
assert.equal(b[3],255);
console.log('appearance regression checks passed');
