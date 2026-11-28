const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../../ui/index.html'),'utf8');
let calls=[],alerts=[],name='  Hero  ',fail=false;
const ctx=vm.createContext({LIB:{busy:false},J:{method:'POST'},mode:1,prompt:()=>name,alert:s=>alerts.push(s),api:async(url,opts)=>{calls.push([url,JSON.parse(opts.body)]);if(fail)throw Error('disk full');return {name:'Hero'}},FF:{busy:false,videoBusy:false,quickBusy:false}});
vm.runInContext(html.split('/* LIB65-ANIM-BEGIN */')[1].split('/* LIB65-ANIM-END */')[0],ctx);
vm.runInContext(html.split('/* LIB65-QUICK-BEGIN */')[1].split('/* LIB65-QUICK-END */')[0],ctx);
(async()=>{
 const button={textContent:'Save',disabled:false},image='data:image/png;base64,abc';
 await ctx.libQuickImage(image,'Sprite',button);
 assert.deepEqual(calls[0],['/api/library',{kind:'image',image,name:'Hero'}]);
 assert.equal(button.disabled,false);assert.equal(button.textContent,'Save');assert.equal(ctx.LIB.busy,false);
 name=null;await ctx.libQuickImage(image,'Sprite',button);assert.equal(calls.length,1);
 name='Hero';await ctx.libQuickImage(null,'Sprite',button);assert.equal(calls.length,1);
 await ctx.libQuickImage('data:image/webp;base64,abc','Sprite',button);assert.equal(calls.length,1);
 ctx.LIB.busy=true;await ctx.libQuickImage(image,'Sprite',button);assert.equal(calls.length,1);ctx.LIB.busy=false;
 const doc={name:'Idle',frames:[image],fps:8};await ctx.libQuickAnimation(doc,button);assert.deepEqual(calls[1][1].document,doc);
 fail=true;await ctx.libQuickImage(image,'Sprite',button);assert.equal(ctx.LIB.busy,false);assert.equal(button.disabled,false);assert.ok(alerts.some(x=>x.includes('disk full')));
 for(const s of ['Open Asset Library','Save animation to Library','Save candidate to Library','Save map image to Library','Save layout image to Library','Save composite to Library','Save master to Library','Save sprite to Library','data-a="library"'])assert.ok(html.includes(s),s);
 console.log('ok shared library save lifecycle and placement');console.log('ALL PASSED');
})().catch(e=>{console.error(e);process.exitCode=1});

const browser=vm.createContext({});
vm.runInContext(html.split('/* LIB65-BROWSE-BEGIN */')[1].split('/* LIB65-BROWSE-END */')[0],browser);
const rows=[{id:'a',name:'Hero 10',kind:'image',created:'2026-01-01',collection:'Forest',favorite:true},{id:'b',name:'Hero 2',kind:'animation',created:'2026-02-01'},{id:'c',name:'Mage',kind:'image',created:'2026-03-01',collection:'Forest',updated:'2026-04-01'}];
assert.equal(browser.libOrganize(rows,'Forest',true,'new').map(x=>x.id).join(),'a');
assert.equal(browser.libOrganize(rows,'',false,'name').map(x=>x.id).join(),'b,a,c');
assert.equal(browser.libOrganize(rows,'',false,'old').map(x=>x.id).join(),'a,b,c');
assert.equal(browser.libOrganize(rows,'',false,'updated').map(x=>x.id).join(),'c,b,a');
assert.equal(rows.map(x=>x.id).join(),'a,b,c');

assert.equal(ctx.libAnimIndex(0,500,12,1,10,true),6);
assert.equal(ctx.libAnimIndex(0,1000,12,1,10,true),2);
assert.equal(ctx.libAnimIndex(0,1000,12,1,10,false),9);
assert.equal(ctx.libAnimIndex(2,500,12,0.5,10,false),5);
assert.equal(ctx.libAnimClips({direction:'S',frames:[],directions:{N:{frames:['a']},E:{frames:[]}}}).map(v=>v.key).join(),'N');
assert.ok(html.includes("libButton(row,'Play / view'"));
