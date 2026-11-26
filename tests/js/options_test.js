// The model dropdown helpers (fill / tagOptions / checkModel) must never corrupt an option's VALUE (the real file name).
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '../../ui/index.html'), 'utf8');
function grab(name) { let i = html.indexOf('function ' + name + '('), depth = 0, k = html.indexOf('{', i); for (; ; k++) { if (html[k] == '{') depth++; else if (html[k] == '}') { depth--; if (!depth) break } } return html.slice(i, k + 1) }
function mkSelect() { return { options: [], selectedIndex: 0, set innerHTML(h) { this.options = [...h.matchAll(/<option(?: value="([^"]*)")?>([^<]*)<\/option>/g)].map(m => { const o = { _v: m[1] !== undefined ? m[1].replace(/&quot;/g, '"').replace(/&amp;/g, '&') : undefined, text: m[2].replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<') }; Object.defineProperty(o, 'value', { get() { return this._v !== undefined ? this._v : this.text } }); return o }); this.selectedIndex = 0 },
  get value() { return this.options[this.selectedIndex] ? this.options[this.selectedIndex].value : '' }, set value(v) { this.selectedIndex = this.options.findIndex(o => o.value == v) } } }
const els = { ckpt: mkSelect(), lora: mkSelect(), status: { className: '', textContent: '' } }; const $ = id => els[id]; let modelKinds = { c: {}, l: {} };
eval(grab('fill') + html.split('/*MODEL-COMPAT-START*/')[1].split('/*MODEL-COMPAT-END*/')[0] + ';globalThis.fill=fill;globalThis.tagOptions=tagOptions;globalThis.checkModel=checkModel;');
let fail = 0; const ok = (c, m) => { if (!c) { fail++; console.log('FAIL', m) } else console.log('ok  ', m) };
const ck = ['sd_xl_base_1.0.safetensors', 'flux1-dev-fp8.safetensors', 'photon_v1.safetensors', 'mystery.safetensors', 'broken.safetensors', 'juggernaut "XL".safetensors'];
const kinds = { 'sd_xl_base_1.0.safetensors': 'sdxl', 'flux1-dev-fp8.safetensors': 'dit', 'photon_v1.safetensors': 'sd15', 'mystery.safetensors': 'unknown', 'broken.safetensors': 'broken', 'juggernaut "XL".safetensors': 'sdxl' };
fill($('ckpt'), ck); fill($('lora'), ['pixel-art-xl-v1.1.safetensors', 'Qwen-Edit.safetensors'], '(none)');
modelKinds = { c: kinds, l: { 'pixel-art-xl-v1.1.safetensors': 'sdxl', 'Qwen-Edit.safetensors': 'other' } }; tagOptions();
ok($('ckpt').options[0].text.includes('sdxl'), 'checkpoint displays its family');
ok(ck.every((n, i) => $('ckpt').options[i].value === n), 'EVERY option value is still the exact file name after tagging (the v13 bug)');
$('ckpt').value = 'juggernaut "XL".safetensors'; ok($('ckpt').value === 'juggernaut "XL".safetensors', 'file names with quotes survive');
ok($('lora').options[0].value === '' && $('lora').options[2].text.includes('Incompatible') && $('lora').options[2].disabled, 'LoRA list keeps (none); a Qwen LoRA is tagged');
const sel = (c, l) => { $('ckpt').value = c; $('lora').value = l };
sel(ck[0], 'pixel-art-xl-v1.1.safetensors'); ok(checkModel() === true, 'SDXL + pixel LoRA allowed');
sel('mystery.safetensors', ''); ok(checkModel() === true, 'unrecognised checkpoint is allowed (never blocked on a guess)');
sel(ck[1], ''); ok(checkModel() === false, 'Flux checkpoint blocked'); sel(ck[2], ''); ok(checkModel() === true, 'SD1.5 text generation allowed'); sel(ck[4], ''); ok(checkModel() === false, 'broken file blocked');
sel(ck[0], 'Qwen-Edit.safetensors'); ok(checkModel() === false, 'Qwen LoRA blocked');
fill($('ckpt'), ['NetaYume','SDXL']);fill($('lora'), ['neta-lora','pixel-xl','mystery'], '(none)');modelKinds={c:{},l:{'neta-lora':'lumina2','pixel-xl':'sdxl','mystery':'unknown'},info:{NetaYume:{family:'lumina2',label:'Lumina2',supported:true,reference:false,flow:true},SDXL:{family:'sdxl',label:'SDXL',supported:true,reference:true}}};$('ckpt').value='NetaYume';tagOptions();ok($('lora').options[1].text.includes('Family match')&&!$('lora').options[1].disabled,'Lumina LoRA matches');ok($('lora').options[2].disabled,'SDXL LoRA disabled for Lumina');ok($('lora').options[3].text.includes('Unverified'),'unknown not falsely certified');$('ckpt').value='SDXL';tagOptions();ok(!$('lora').options[2].disabled&&$('lora').options[1].disabled,'switching checkpoint updates compatibility');
console.log(fail ? fail + ' FAILED' : 'ALL PASSED'); process.exit(fail ? 1 : 0);
