const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(path.join(__dirname,'../../ui/index.html'),'utf8');
const block=html.split('/*POSE-PRESET-START*/')[1].split('/*POSE-PRESET-END*/')[0];
const store=new Map(), nodes={};const $=id=>nodes[id]??=( {value:'',textContent:'',options:[],replaceChildren(){this.options=[]},appendChild(o){this.options.push(o)}} );
const factory=Array.from({length:18},()=>[.5,.5]);$('scl').value=1;
const c=vm.createContext({$,localStorage:{getItem:k=>store.get(k),setItem:(k,v)=>store.set(k,v)},document:{createElement:()=>({})},confirm:()=>true,markDirty(){},redraw(){},PRESETS:{'Stand (side, facing right)':factory}});
function run(s){return vm.runInContext(s,c)}
run('let pts=PRESETS["Stand (side, facing right)"].map(p=>p.slice()),lastScale=1;'+block);
run('pts[0][0]=.25; savePoseDefault(); resetPoseFactory()');assert.equal(run('pts[0][0]'),.5);
run('loadPreset(POSE_START)');assert.equal(run('pts[0][0]'),.25);console.log('ok saved override and factory reset');
$('posepresetname').value='My chibi';run('savePoseNew()');assert.equal($('preset').value,'My chibi');
run('pts[0][0]=.8; loadPreset("My chibi")');assert.equal(run('pts[0][0]'),.25);
assert.equal(JSON.parse(store.get('sf_pose_presets_v1'))['My chibi'].pts[0][0],.25);console.log('ok named preset persists and copies points');
run('deletePoseSaved()');assert.equal(run('poseExists("My chibi")'),false);assert.equal($('preset').value,'Stand (side, facing right)');
run('deletePoseSaved()');assert.equal(run('pts[0][0]'),.5);console.log('ok delete custom and clear built-in override');
console.log('ALL PASSED');
