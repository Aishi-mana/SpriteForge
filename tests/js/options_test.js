// The model dropdown helpers (fill / tagOptions / checkModel) must never corrupt an option's VALUE (the real file name).
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '../../ui/index.html'), 'utf8');
function grab(name) { let i = html.indexOf('function ' + name + '('), depth = 0, k = html.indexOf('{', i); for (; ; k++) { if (html[k] == '{') depth++; else if (html[k] == '}') { depth--; if (!depth) break } } return html.slice(i, k + 1) }
function mkSelect() { return { options: [], selectedIndex: 0, set innerHTML(h) { this.options = [...h.matchAll(/<option(?: value="([^"]*)")?>([^<]*)<\/option>/g)].map(m => { const o = { _v: m[1] !== undefined ? m[1].replace(/&quot;/g, '"').replace(/&amp;/g, '&') : undefined, text: m[2].replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<') }; Object.defineProperty(o, 'value', { get() { return this._v !== undefined ? this._v : this.text } }); return o }); this.selectedIndex = 0 },
  get value() { return this.options[this.selectedIndex] ? this.options[this.selectedIndex].value : '' }, set value(v) { this.selectedIndex = this.options.findIndex(o => o.value == v) } } }
const els = { ckpt: mkSelect(), lora: mkSelect(), status: { className: '', textContent: '' } }; const $ = id => els[id]; let modelKinds = { c: {}, l: {} };
eval(grab('fill') + grab('tagOptions') + grab('checkModel') + ';globalThis.fill=fill;globalThis.tagOptions=tagOptions;globalThis.checkModel=checkModel;');
let fail = 0; const ok = (c, m) => { if (!c) { fail++; console.log('FAIL', m) } else console.log('ok  ', m) };
const ck = ['sd_xl_base_1.0.safetensors', 'flux1-dev-fp8.safetensors', 'photon_v1.safetensors', 'mystery.safetensors', 'broken.safetensors', 'juggernaut "XL".safetensors'];
const kinds = { 'sd_xl_base_1.0.safetensors': 'sdxl', 'flux1-dev-fp8.safetensors': 'dit', 'photon_v1.safetensors': 'sd15', 'mystery.safetensors': 'unknown', 'broken.safetensors': 'broken', 'juggernaut "XL".safetensors': 'sdxl' };
fill($('ckpt'), ck); fill($('lora'), ['pixel-art-xl-v1.1.safetensors', 'Qwen-Edit.safetensors'], '(none)');
modelKinds = { c: kinds, l: { 'pixel-art-xl-v1.1.safetensors': 'sdxl', 'Qwen-Edit.safetensors': 'other' } }; tagOptions();
ok($('ckpt').options[0].text === ck[0], 'an SDXL option has no tag');
ok(ck.every((n, i) => $('ckpt').options[i].value === n), 'EVERY option value is still the exact file name after tagging (the v13 bug)');
$('ckpt').value = 'juggernaut "XL".safetensors'; ok($('ckpt').value === 'juggernaut "XL".safetensors', 'file names with quotes survive');
ok($('lora').options[0].value === '' && $('lora').options[2].text.includes('not for SDXL'), 'LoRA list keeps (none); a Qwen LoRA is tagged');
const sel = (c, l) => { $('ckpt').value = c; $('lora').value = l };
sel(ck[0], 'pixel-art-xl-v1.1.safetensors'); ok(checkModel() === true, 'SDXL + pixel LoRA allowed');
sel('mystery.safetensors', ''); ok(checkModel() === true, 'unrecognised checkpoint is allowed (never blocked on a guess)');
sel(ck[1], ''); ok(checkModel() === false, 'Flux checkpoint blocked'); sel(ck[2], ''); ok(checkModel() === false, 'SD1.5 blocked'); sel(ck[4], ''); ok(checkModel() === false, 'broken file blocked');
sel(ck[0], 'Qwen-Edit.safetensors'); ok(checkModel() === false, 'Qwen LoRA blocked');
console.log(fail ? fail + ' FAILED' : 'ALL PASSED'); process.exit(fail ? 1 : 0);
