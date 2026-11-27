const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const html=fs.readFileSync(path.join(__dirname,'../../ui/index.html'),'utf8');
const locks=html.split('/*IE61-START*/')[1].split('/*EDIT61-PRESETS-START*/')[0];
const code=html.split('/*EDIT61-PRESETS-START*/')[1].split('/*EDIT61-PRESETS-END*/')[0];
const api=new Function(locks+code+'return {presets:IE61_EDITS,edit:ie61EditPreset,locks:ie61LockPreset}')();
assert.equal(Object.keys(api.presets).length,10);
for(const [key,p] of Object.entries(api.presets)){
 const v=api.edit(key,p.example);assert(v.instruction.includes(p.example));assert(v.hint);assert(api.locks(v.locks).length>0);
}
console.log('ok all ten editing presets');
assert.equal(api.edit('wings','   '),null);assert.equal(api.edit('unknown','test'),null);assert.equal(api.edit('hair','a'.repeat(1001)),null);
console.log('ok invalid descriptions rejected');
assert.equal(api.edit('wings','feathered wings').expand,true);
assert(!api.locks('equipment').includes('accessories'));
assert(!api.locks('hair').includes('hairstyle'));
assert(!api.locks('expression').includes('face'));
assert(!api.locks('default').includes('outfit'));
console.log('ok appropriate unlocks and wing expansion');
assert(html.includes("if(p.expand&&!q('regional').checked)"));
assert(html.includes('featureless non-explicit mannequin'));
console.log('ok mask compatibility and mannequin template');
console.log('ALL PASSED');
