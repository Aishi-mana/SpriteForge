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

/* Integration: exercise real staging history and source identity without DOM/GPU. */
const integration=vm.createContext({FF:{rev:3},DA64:{session:null,busy:false},da64Stop(){},da64Draw(){},confirm:()=>true});
const names=['da64Live','da64Build','da64Record','da64HistoryTrim','da64Undo','da64Redo','da64ResetAll'];
for(const name of names){
 const line=html.split('\n').find(l=>l.startsWith('function '+name+'('));
 assert.ok(line,name);vm.runInContext(line,integration);
}
vm.runInContext(`
 const source={frames:['a','b','c'],locked_frames:[1]};
 FF.doc=source;
 const s=DA64.session={source,rev:3,index:0,changes:new Map(),undo:[],redo:[]};
 da64Record(s,[[0,'x'],[2,'z']]);
 if(source.frames.join()!=='a,b,c'||da64Build(source,s.changes).frames.join()!=='x,b,z')throw Error('source isolation');
 da64Undo();if(s.changes.size!==0)throw Error('undo');
 da64Redo();if(s.changes.size!==2)throw Error('redo');
 da64ResetAll();if(s.changes.size!==0)throw Error('restore');
 da64Undo();if(s.changes.size!==2)throw Error('restore undo');
 let rejected=false;try{da64Record(s,[[1,'bad']])}catch{rejected=true}
 if(!rejected||s.changes.size!==2)throw Error('locked frame');
 FF.rev++;if(da64Live(s))throw Error('stale source accepted');
 da64Undo();if(s.changes.size!==2)throw Error('stale mutation');
`,integration);
assert.ok(html.includes("da64Stop();da64ReviewTicket++"));
assert.ok(html.includes("token===da64ReviewTicket&&da64Live(s)"));
console.log('direct editor integration checks passed');
