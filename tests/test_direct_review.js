// Run with node tests/test_direct_review.js
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'../ui/index.html'),'utf8'),ctx=vm.createContext({});
vm.runInContext(html.split('/*DA64-REVIEW-BEGIN*/')[1].split('/*DA64-REVIEW-END*/')[0],ctx);
const m=new Map([[1,'a'],[4,'b']]);
assert.equal(ctx.da64ChangedIndex(m,1,1),4);
assert.equal(ctx.da64ChangedIndex(m,4,1),1);
assert.equal(ctx.da64ChangedIndex(m,1,-1),4);
assert.equal(ctx.da64ChangedIndex(new Map(),2,1),2);
const a=new Uint8ClampedArray([255,0,0,0,20,30,40,255,100,100,100,128]);
const b=new Uint8ClampedArray([0,255,0,0,20,30,40,255,100,100,100,255]);
const d=ctx.da64Difference(a,b);
assert.equal(d.count,1);
assert.equal(d.pixels[3],0);
assert.equal(d.pixels[7],0);
assert.ok(d.pixels[11]>0);
const s={changes:m,undo:Array.from({length:10},()=>m),redo:[]};
ctx.da64HistoryTrim(s);assert.equal(s.undo.length,8);
console.log('direct review regression checks passed');
