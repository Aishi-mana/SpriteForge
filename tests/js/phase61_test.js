const fs=require('fs'),path=require('path'),assert=require('assert');
const html=fs.readFileSync(path.join(__dirname,'../../ui/index.html'),'utf8');
function slice(a,b){const i=html.indexOf(a),j=html.indexOf(b,i);assert(i>=0&&j>i);return html.slice(i,j)}
const map=slice('const M55=','function map55Brushes(')+slice('function map55HasContent()','function map55Undo()');
const clip=slice('let cl54Library=[];','function cl54Refresh()');
const preview=slice('function bh56Stop()','async function bh56Start()');
const els={};const $=id=>els[id]||(els[id]={value:'',textContent:''});
let permit=false,refreshes=0,draws=0,stopped=0;
const T=new Function('$','confirm','map55Draw','cl54Refresh','clearInterval',`
const BH56={ticket:1,timer:123,move:1,clips:{idle:[1]}};
`+map+clip+preview+`
return {M55,BH56,map55HasContent,map55Reset,map55New,cl54ConfirmTopology,cl54ClearTopology,bh56Stop,setClips:v=>cl54Library=v,getClips:()=>cl54Library};
`)($,()=>permit,()=>draws++,()=>refreshes++,()=>stopped++);
T.M55.cells[0]='tile';T.M55.solid[0]=true;T.M55.undo.push({});T.M55.images.set('tile',{});T.M55.drag=true;
assert(T.map55HasContent());T.map55New();assert.equal(T.M55.cells[0],'tile');
T.map55Reset();assert(!T.map55HasContent());assert.equal(T.M55.cells.length,192);assert.equal(T.M55.undo.length,0);assert.equal(T.M55.images.size,0);assert(!T.M55.drag);console.log('ok map reset and cancel');
T.setClips([{name:'walk'}]);assert(!T.cl54ConfirmTopology());assert.equal(T.getClips().length,1);permit=true;assert(T.cl54ConfirmTopology());T.cl54ClearTopology();assert.equal(T.getClips().length,0);assert.equal(refreshes,1);console.log('ok clip confirmation and explicit clear');
T.bh56Stop();assert.equal(T.BH56.ticket,2);assert.equal(T.BH56.timer,null);assert.deepEqual(T.BH56.clips,{});assert.equal(stopped,1);console.log('ok behavior preview invalidation');
assert(html.includes('if(token!==BH56.ticket||mode!==14)return;'));assert(html.includes('map55Reset();$(\'asoft\')'));console.log('ok project and workspace integration guards');
console.log('ALL PASSED');
