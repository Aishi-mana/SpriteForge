const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(path.join(__dirname,'../../ui/index.html'),'utf8'),c={};vm.createContext(c);vm.runInContext(html.split('/*SYSTEM-ASSETS-START*/')[1].split('/*SYSTEM-ASSETS-END*/')[0],c);
const d=c.sysStarter();assert.equal(d.assets.length,0);assert.equal(d.components.length,9);assert(d.components.some(v=>v.kind==='text'));console.log('ok editable starter');
assert.equal(c.sysId(d.components,'part_'),'part_10');console.log('ok unique IDs');
assert.equal(c.sysHit(d.components,60,95).name,'Health fill');assert.equal(c.sysHit(d.components,60,46).name,'HUD title');console.log('ok topmost hit');
d.components[3].visible=false;assert.equal(c.sysHit(d.components,60,95).name,'Health track');assert.equal(c.sysHit(d.components,900,200),null);console.log('ok hidden component and empty hit');
console.log('ALL PASSED');
