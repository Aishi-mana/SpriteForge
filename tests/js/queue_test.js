// Queue + history UI logic: runs the real /*QUEUE*/ block from ui/index.html against a fake DOM and a fake API.
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '../../ui/index.html'), 'utf8');
const block = html.slice(html.indexOf('/*QUEUE*/'), html.indexOf('/*END QUEUE*/')) + html.slice(html.indexOf('/*TILES*/'), html.indexOf('/*END TILES*/')) + html.slice(html.indexOf('/*TERRAIN*/'), html.indexOf('/*END TERRAIN*/')) + html.slice(html.indexOf('/*TILEFX*/'), html.indexOf('/*END TILEFX*/'));
let fail = 0; const ok = (c, m) => { if (!c) { fail++; console.log('FAIL', m) } else console.log('ok  ', m) };
ok(block.length > 3000, 'the queue block is present in the page');

const draws = []; const CTX = new Proxy({ drawImage: (...a) => draws.push(a) }, { get: (t, k) => (k in t ? t[k] : () => {}) });
const els = {}; const mk = id => els[id] || (els[id] = { id, value: '', checked: false, textContent: '', innerHTML: '', style: {}, dataset: {}, className: '', options: [],
  classList: { toggle() {}, add() {}, remove() {} }, getContext: () => CTX, querySelectorAll: () => [mk('qa' + Math.random()), mk('qb' + Math.random()), mk('qc' + Math.random())], querySelector: () => mk('q' + Math.random()), appendChild() {}, scrollIntoView() {} });
const $ = id => mk(id);
const set = (o) => Object.entries(o).forEach(([k, v]) => { const e = $(k); if (typeof v == 'boolean') e.checked = v; else e.value = v });
set({ prompt: 'a knight', neg: 'blurry', ckpt: 'sd_xl_base_1.0.safetensors', lora: 'pixel.safetensors', lw: '0.9', steps: '25', cfg: '7', seed: '-1', bg: 'white', n1: '2', n: '3', mode: 'fixed', size: '64', colors: '16', pal: '', rmbg: true,
  tol: '40', shadow: true, pxcrisp: true, pxclean: false, pxoutline: 'none', sampler: 'euler_a', pose: 'jumping', char: 'knight', ips: '0.7', lockpal: true, matchsz: false, cns: '0.8', canvas: '128', gsize: '768', useskel: true, scl: '1', preset: 'Stand' });

$('preset').options = [{value:'Stand'}];
const calls = []; let apiQueue = [];
const api = async (url, opt) => { calls.push({ url, body: opt && typeof opt.body == 'string' ? JSON.parse(opt.body) : (opt && opt.body ? '[form]' : null), method: opt && opt.method }); const r = apiQueue.shift(); if (r instanceof Error) throw r; return typeof r == 'function' ? r() : r };
const J = { method: 'POST', headers: {} };
globalThis.Image = class { constructor() { this.width = this.height = this.naturalWidth = this.naturalHeight = 16 } set src(v) { this._s = v; setTimeout(() => this.onload && this.onload(), 0) } get src() { return this._s } };
globalThis.document = { createElement: () => mk('c' + Math.random()) };
globalThis.FileReader = class { readAsDataURL(b) { this.result = 'data:image/png;base64,POSE'; setTimeout(() => this.onload(), 0) } };
const rendered = [];
const env = `
let mode = 1, refURL = null, pts = Array.from({length:18},(_, i)=>[i/20, i/30]), lastScale = 1; const PRESETS = { Stand: 1 }; let dirty = false;
const collect = () => ({ prompt: $('prompt').value, steps: $('steps').value });
const applied = []; const applySettings = s => applied.push(s); const setRef = u => { refURL = u }; const markDirty = () => { dirty = true };
const poseBlob = async () => 'BLOB'; const openEditor = (u, o) => { editorCalls.push([u, o]) }; const render = (r, t) => rendered.push([r, t]); const tab = n => { mode = n }; const show = () => {}; const checkModel = () => true;

` + block + `;globalThis.T = { qStatusText, qDiff, qEsc, qTitle, genParams, refParams, genPromptPreview, genPromptInvalidate, genPromptStale, qEnqueue, qFollow, qRefresh, hUse, armed, QS, qRenderList,
  setMode: v => { mode = v }, crIndex, trCornerGrid, trNames, tsSolid, tlRepair, anMake, anExport, anBody, AN, anStop, TR, trBits, trMakeGrid, trBody, trSet, trClear, trGenerate, trMap, trExport, trSlots, TL, tileParams, tlKindChanged, tlAdd, tlSeamless, tlOffset, tlEdit, tsExport, tsRender, hTab, tlUse, setRef: u => { refURL = u }, get pts() { return pts }, get mode() { return mode }, get refURL() { return refURL }, applied, get dirty() { return dirty } };`;
const editorCalls = [];
new Function('$', 'api', 'J', 'rendered', 'editorCalls', env)($, api, J, rendered, editorCalls);
const T = globalThis.T;

ok(T.qStatusText({ status: 'queued' }, 0) == 'Queued · next' && T.qStatusText({ status: 'queued' }, 2) == 'Queued · 2 jobs ahead' && T.qStatusText({ status: 'queued' }, 1) == 'Queued · 1 job ahead', 'waiting status text');
ok(T.qStatusText({ status: 'running', progress: [1, 3] }) == 'Generating… image 2 of 3' && T.qStatusText({ status: 'running', progress: [3, 3] }) == 'Generating… image 3 of 3' && T.qStatusText({ status: 'running' }).includes('loads the model'), 'running status text (never "image 4 of 3")');
ok(T.qEsc('<img src=x onerror="a">&') == '&lt;img src=x onerror=&quot;a&quot;&gt;&amp;', 'prompts are HTML-escaped before they reach innerHTML');
ok(T.qTitle({ kind: 'reference', prompt: 'x' }) == 'Pose · x' && T.qTitle({ kind: 'generate', prompt: '' }) == '(no prompt)', 'job titles');
const A = { params: { steps: 25, seed: 1, prompt: 'a' } }, B = { params: { steps: 30, seed: 1, prompt: 'a', cfg: 5 } };
ok(JSON.stringify(T.qDiff([A, B]).sort()) == '["cfg","steps"]' && T.qDiff([A, A]).length == 0, 'compare lists exactly the settings that differ');

const g = T.genParams(); ok(g.steps === 25 && g.lora_weight === 0.9 && g.n === 2 && g.seed === -1 && g.rmbg === undefined && g.remove_bg === true && g.clean === false && g.palette === 'none' && g.size === 64, 'generate params have real numbers/booleans (not strings)');
set({artstyle:'anime',hdsize:'768',hdgen:'1024'}); ok(T.genParams().art_style==='anime' && T.genParams().hd_size===768 && T.refParams().art_style==='anime','HD style settings travel with both job types'); set({artstyle:'pixel'});
const artSelector=html.match(/<select id="artstyle"[^>]*>([\s\S]*?)<\/select>/)[1];
for(let heads=2;heads<=7;heads++){const style='head_'+heads;ok(artSelector.includes('value="'+style+'"'),'existing art selector has '+style);set({artstyle:style,genBodyBase:true});ok(T.genParams().art_style===style&&T.genParams().body_base===true,'Generate preserves '+style+' with body base enabled')}
set({artstyle:'pixel',genBodyBase:false});
const r = T.refParams(); ok(r.ip_scale === 0.7 && r.n === 3 && r.canvas === 128 && r.gen_size === 768 && r.lock_palette === true && r.match_size === false && r.cn_scale === 0.8 && typeof r.cfg == 'number', 'reference params have real numbers/booleans');

(async () => {
  apiQueue = [{ id: 'j1' }]; T.setMode(1); const a = await T.qEnqueue();
  ok(a.id == 'j1' && calls[0].url == '/api/queue/add' && calls[0].body.kind == 'generate' && calls[0].body.params.prompt == 'a knight' && calls[0].body.ui.steps == '25' && !calls[0].body.images, 'tab 1 queues a generate job with its UI snapshot');
  T.setMode(2); T.setRef(null); apiQueue = []; let e1 = null; try { await T.qEnqueue() } catch (e) { e1 = e }
  ok(e1 && /reference/i.test(e1.message) && calls.length == 1, 'reference tab without a reference image: clear error, nothing queued');
  T.setRef('data:image/png;base64,REF'); apiQueue = [{ id: 'j2' }]; await T.qEnqueue(); const b2 = calls[1].body;
  ok(b2.kind == 'reference' && b2.images.ref.endsWith('REF') && b2.images.pose.endsWith('POSE') && b2.ui.__skel.pts.length == 18 && b2.params.character == 'knight', 'reference job carries the reference, the skeleton render and the skeleton points');
  $('useskel').checked = false; apiQueue = [{ id: 'j3' }]; await T.qEnqueue(); ok(!calls[2].body.images.pose, 'without "Use skeleton" no pose image is sent'); $('useskel').checked = true;

  // follow: queued -> running -> finished
  const seq = [{ jobs: [{ id: 'x0', status: 'running', progress: [0, 1] }, { id: 'jx', status: 'queued' }], paused: false },
               { jobs: [{ id: 'jx', status: 'running', progress: [1, 2] }], paused: false }, { jobs: [], paused: false },
               { id: 'jx', status: 'done', results: [{ sprite: 's', info: { size: [8, 8] } }] }];
  apiQueue = seq.slice(); const t0 = Date.now(); await T.qFollow('jx');
  ok(rendered.length == 1 && rendered[0][0][0].sprite == 's' && $('status').textContent.startsWith('Done'), 'follow() waits for the job and renders its results like a direct run');
  apiQueue = [{ jobs: [], paused: false }, { id: 'jy', status: 'error', error: 'out of memory' }]; let e2 = null; try { await T.qFollow('jy') } catch (e) { e2 = e }
  ok(e2 && e2.message == 'out of memory', 'a failed job surfaces its readable error');
  apiQueue = [{ jobs: [], paused: false }, { id: 'jz', status: 'cancelled', error: null }]; await T.qFollow('jz'); ok($('status').textContent.startsWith('Job cancelled'), 'a cancelled job is reported, not rendered');

  // strip + tab label
  apiQueue = [{ jobs: [{ id: 'a', status: 'running' }, { id: 'b', status: 'queued' }, { id: 'c', status: 'queued' }], paused: true }]; await T.qRefresh();
  ok($('qstrip').textContent.includes('1 running') && $('qstrip').textContent.includes('2 waiting') && $('qstrip').textContent.includes('paused') && $('t9').textContent == 'Queue (3)' && $('qpause').textContent == 'Resume', 'strip, tab badge and pause button reflect the queue');
  apiQueue = [{ jobs: [], paused: false }]; await T.qRefresh(); ok($('qstrip').textContent == '' && $('t9').textContent == 'Queue', 'an empty queue shows nothing');

  // loading settings back
  const job = { kind: 'reference', ui: { prompt: 'p', __skel: { pts: Array.from({ length: 18 }, () => [0.5, 0.5]), scale: 1.2, preset: 'Stand' } }, images: { ref: 'data:image/png;base64,OLD', pose: 'data:image/png;base64,P' } };
  $('useskel').checked = false; T.hUse(job);
  ok(T.applied.length == 1 && T.refURL.endsWith('OLD') && $('useskel').checked === true && T.pts[0][0] == 0.5 && $('scl').value == 1.2 && T.mode == 2 && T.dirty, 'Use these settings restores controls, reference image, skeleton and switches tab');
  T.hUse({ kind: 'generate', ui: { prompt: 'q' }, images: {} }); ok(T.mode == 1, 'a generate job opens the Generate tab');

  // two-click button
  let fired = 0; const btn = { dataset: {}, textContent: 'Delete' }; T.armed(btn, 'delete', () => fired++); ok(fired == 0 && btn.textContent == 'Click again to delete', 'first click only arms');
  T.armed(btn, 'delete', () => fired++); ok(fired == 1 && btn.textContent == 'Delete', 'second click confirms');

  // ---------- tiles and props ----------
  set({ tkind: 'tile', tprompt: 'mossy stones', tsize: '32', tcolors: '10', tn: '4', tpal: '', tseam: true, toutline: 'dark', tsname: 'World', tcols: '4', tspace: '1', tmargin: '0', tsgodot: true, tstiled: false, xgpath: 'res://art/' });
  let tp = T.tileParams(); ok(tp.kind == 'tile' && tp.size === 32 && tp.colors === 10 && tp.n === 4 && tp.palette === 'none' && tp.seamless === true && tp.outline === 'none' && tp.mode == 'fixed', 'tile params: real numbers, outline forced off for tiles (it would break the seams)');
  $('tkind').value = 'icon'; tp = T.tileParams(); ok(tp.kind == 'icon' && tp.outline == 'dark', 'icons keep the chosen outline');
  $('tprompt').value = 'mossy cobblestone ground'; $('tkind').value = 'prop'; T.tlKindChanged(); ok($('tprompt').value.includes('barrel') && $('tsize').value == '48', 'choosing a kind fills a sensible example prompt and size');
  $('tprompt').value = 'my own text'; $('tkind').value = 'icon'; T.tlKindChanged(); ok($('tprompt').value == 'my own text', 'a prompt you typed is never overwritten');
  $('tkind').value = 'tile'; T.setMode(10); apiQueue = [{ id: 'jt' }]; await T.qEnqueue(); const bt = calls[calls.length - 1].body;
  ok(bt.kind == 'generate' && bt.params.kind == 'tile' && bt.params.prompt == 'my own text' && !bt.images, 'the Tiles tab queues a generate job with kind=tile');
  ok(T.hTab({ kind: 'generate', params: { kind: 'tile' } }) == 10 && T.hTab({ kind: 'generate', params: { kind: 'icon' } }) == 10 && T.hTab({ kind: 'generate', params: {} }) == 1 && T.hTab({ kind: 'reference', params: {} }) == 2, 'history jobs reopen the right tab');
  T.hUse({ kind: 'generate', ui: { tprompt: 'x' }, params: { kind: 'prop' }, images: {} }); ok(T.mode == 10, 'Use these settings on a tile/prop job opens the Tiles tab');
  ok(T.qTitle({ kind: 'generate', sub: 'tile', prompt: 'grass' }) == 'Tile · grass' && T.qTitle({ kind: 'generate', sub: '', prompt: 'x' }) == 'x', 'history titles show the tile / prop / icon / ui kind');
  T.TL.tiles.length = 0; T.TL.src = 'data:image/png;base64,AAA'; $('tlname').value = ''; T.tlAdd(); $('tlname').value = ' grass '; T.tlAdd();
  ok(T.TL.tiles.length == 2 && T.TL.tiles[0].name == 'tile_00' && T.TL.tiles[1].name == 'grass', 'tiles get automatic or trimmed names');
  apiQueue = [{ dir: '/x', count: 2, mode: 'tileset', columns: 4, rows: 1, sheet: [64, 16], files: ['a.png'] }]; await T.tsExport(); const be = calls[calls.length - 1];
  ok(be.url == '/api/tiles/export' && be.body.name == 'World' && be.body.columns === 4 && be.body.spacing === 1 && be.body.margin === 0 && be.body.godot === true && be.body.tiled === false && be.body.godot_path == 'res://art/' && be.body.tiles.length == 2, 'export sends the tileset with typed options');
  ok($('status').textContent.startsWith('Exported 2 tiles as a 4×1 tileset'), 'export reports where the files went');
  T.TL.tiles.length = 0; $('status').textContent = ''; await T.tsExport(); ok($('status').textContent.includes('Add at least one tile'), 'exporting an empty tileset gives a clear message');
  T.TL.src = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='; apiQueue = [{ sprite: 'data:image/png;base64,NEW', info: { seam_before: 5.2, seam: 1.1 } }]; await T.tlSeamless();
  ok(T.TL.src.endsWith('NEW') && $('status').textContent.includes('5.2 → 1.1') && calls[calls.length - 1].url == '/api/tiles/seamless', 'Make seamless replaces the workbench tile and reports the score');
  apiQueue = [{ sprite: 'data:image/png;base64,SHIFT', info: {} }]; await T.tlOffset(); ok(T.TL.src.endsWith('SHIFT') && calls[calls.length - 1].url == '/api/tiles/offset', 'Offset shifts the workbench tile');
  T.tlEdit(); ok(editorCalls.length == 1 && editorCalls[0][0].endsWith('SHIFT'), 'Edit opens the pixel editor on the workbench tile'); editorCalls[0][1].apply('data:image/png;base64,EDITED'); ok(T.TL.src.endsWith('EDITED'), 'applying the editor updates the workbench tile');

  // ---------- terrain sets ----------
  const plus = [[0, 1, 0], [1, 1, 1], [0, 1, 0]];
  ok(T.trBits(plus, 1, 1) == 85 && T.trBits(plus, 1, 0) == (16 | 32 | 8) && T.trBits(plus, 0, 1) == (4 | 2 | 8) && T.trBits([[1, 1], [1, 1]], 0, 0) == (4 | 8 | 16), 'neighbour bits equal the Python engine (same fixtures as tests/test_terrain.py)');
  const g = T.trMakeGrid(16, 10), ones = g.flat().reduce((a, b) => a + b, 0); ok(g.length == 10 && g[0].length == 16 && g.flat().every(v => v === 0 || v === 1) && ones > 40 && ones < 120, 'random blob grid: right size, 0/1, about half filled');
  set({ atype: 'blob47', ainset: '0', around: '', arim: 'dark', abase: 'bake', atname: 'meadow', atterr: 'Grass', atground: true });
  let tb = T.trBody(); ok(tb.kind == 'blob47' && tb.inset === 0 && tb.round === -1 && tb.rim == 'dark' && tb.base == 'bake' && tb.ground === true && tb.name == 'meadow' && tb.terrain_name == 'Grass' && tb.columns === 4 && tb.godot === true && tb.tiled === false && tb.godot_path == 'res://art/', 'terrain request: typed fields, empty rounding means auto (-1)');
  $('ainset').value = '3'; $('around').value = '0'; tb = T.trBody(); ok(tb.inset === 3 && tb.round === 0, 'an explicit rounding of 0 is kept (not mistaken for auto)'); $('ainset').value = '0'; $('around').value = '';
  T.TL.src = null; $('status').textContent = ''; T.trSet('a'); ok(!T.TR.a && $('status').textContent.includes('workbench'), 'setting A without a workbench tile explains what to do');
  T.TL.src = 'data:image/png;base64,GRASS'; T.trSet('a'); T.TL.src = 'data:image/png;base64,DIRT'; T.trSet('b'); ok(T.TR.a.endsWith('GRASS') && T.TR.b.endsWith('DIRT') && $('tra').src.endsWith('GRASS') && $('tra').style.display == 'inline-block', 'workbench tile becomes terrain A / ground B');
  T.trClear(); ok(T.TR.b === null && T.TR.a.endsWith('GRASS'), 'Clear B keeps A');
  T.TR.a = null; $('status').textContent = ''; await T.trGenerate(); ok($('status').textContent.includes('Set terrain A first') && calls[calls.length - 1].url != '/api/terrain/generate', 'generate without A: clear message, no request');
  T.TR.a = 'data:image/png;base64,GRASS'; T.TR.b = 'data:image/png;base64,DIRT';
  const lookup = Array.from({ length: 256 }, (_, i) => i % 3), fake = { tiles: [0, 1, 2].map(i => ({ index: i, mask: i * 5, image: 'data:image/png;base64,T' + i })), ground: 'data:image/png;base64,G', lookup, kind: 'blob47', tile_size: 16, inset: 3, round: 2, rim: 'dark', base: 'bake' };
  apiQueue = [fake]; await T.trGenerate(); const gc = calls[calls.length - 1];
  ok(gc.url == '/api/terrain/generate' && gc.body.a.endsWith('GRASS') && gc.body.b.endsWith('DIRT') && T.TR.res.tiles.length == 3 && $('trinfo').textContent.includes('3 tiles') && $('trinfo').textContent.includes('inset 3px'), 'Generate sends A and B with the options and shows the info');
  await new Promise(r => setTimeout(r, 20)); draws.length = 0; await T.trMap(); ok(draws.length == 16 * 10, 'map preview paints every cell (tile or ground) of a 16x10 map'); ok($('status').textContent.includes('Random map built'), 'map preview reports');
  apiQueue = [{ dir: '/x/meadow_terrain', count: 47, kind: 'blob47', ground: true, sheet: [128, 96], files: ['meadow.png', 'terrain.json'] }]; await T.trExport(); const ec = calls[calls.length - 1];
  ok(ec.url == '/api/terrain/export' && ec.body.name == 'meadow' && $('status').textContent.startsWith('Exported 47 blob47 tiles + ground (128×96)'), 'export posts the same options and reports the folder');
  T.TR.a = null; $('status').textContent = ''; await T.trExport(); ok($('status').textContent.includes('Set terrain A first'), 'export without A: clear message');

  // ---------- phase 22: corner / multi sets, solid, repair, animation ----------
  ok(T.crIndex([0, 0, 0, 0], 2) == 0 && T.crIndex([1, 0, 1, 1], 2) == 11 && T.crIndex([2, 1, 0, 2], 3) == ((2 * 3 + 1) * 3 + 0) * 3 + 2, 'corner index formula equals the engine (same fixtures as tests/test_tilefx.py)');
  const cg = T.trCornerGrid(16, 10, 3); ok(cg.length == 11 && cg[0].length == 17 && cg.flat().every(v => v >= 0 && v < 3) && new Set(cg.flat()).size >= 2, 'random corner map: (W+1)x(H+1) labels in range, more than one terrain');
  set({ atterr: 'Grass, Dirt ,Water' }); ok(JSON.stringify(T.trNames()) == '["Grass","Dirt","Water","Terrain D"]', 'terrain names: trimmed, missing ones get defaults');
  set({ atype: 'multi', around: '' }); T.TR.a = 'data:image/png;base64,A'; T.TR.b = 'data:image/png;base64,B'; T.TR.c = 'data:image/png;base64,C'; T.TR.d = null; tb = T.trBody();
  ok(tb.kind == 'multi' && tb.c.endsWith('C') && tb.d === null && tb.names.length == 4 && tb.terrain_name == 'Grass', 'multi request carries A, B, C (D empty) and the names');
  T.TR.c = null; $('status').textContent = ''; await T.trGenerate(); ok($('status').textContent.includes('A, B and C'), 'multi without C: clear message, nothing sent');
  T.TR.c = 'data:image/png;base64,C'; const cfake = { tiles: Array.from({ length: 81 }, (_, i) => ({ index: i, mask: null, corners: [0, 0, 0, i % 3], image: 'data:image/png;base64,T' + i })), ground: null, lookup: [], kind: 'multi', tile_size: 16, inset: 0, round: 1.9, rim: 'dark', base: 'bake', n: 3 };
  apiQueue = [cfake]; await T.trGenerate(); ok(calls[calls.length - 1].body.kind == 'multi' && $('trinfo').textContent.includes('81 tiles') && $('trinfo').textContent.includes('3 terrains'), 'multi set generated, info shows terrain count');
  await new Promise(r => setTimeout(r, 20)); draws.length = 0; await T.trMap(); ok(draws.length == 160, 'corner map preview paints 16x10 cells with the index formula');
  const c0 = T.TR.imgs.t.length; ok(c0 == 81, 'all 81 tile images are loaded for the map');
  // solid flags
  T.TL.tiles.length = 0; T.TL.tiles.push({ name: 'wall', image: 'data:image/png;base64,W' }, { name: 'floor', image: 'data:image/png;base64,F' }); T.tsSolid(0, true); T.tsSolid(5, true);
  ok(T.TL.tiles[0].solid === true && T.TL.tiles[1].solid === undefined && T.TL.tiles.length == 2, 'solid flag set on the right tile; unknown index ignored');
  apiQueue = [{ dir: '/x', count: 2, mode: 'tileset', columns: 2, rows: 1, sheet: [32, 16], files: [] }]; await T.tsExport(); ok(calls[calls.length - 1].body.tiles[0].solid === true && !calls[calls.length - 1].body.tiles[1].solid, 'the tileset export carries the solid flags');
  // AI repair
  T.TL.src = 'data:image/png;base64,TILE'; set({ rfstr: '0.6', rfband: '20', seed: '7' }); apiQueue = [{ sprite: 'data:image/png;base64,FIXED', info: { seam_before: 9.1, seam: 1.4, seed: 7 } }]; await T.tlRepair(); const rc = calls[calls.length - 1];
  ok(rc.url == '/api/tiles/repair' && rc.body.strength === 0.6 && Math.abs(rc.body.band - 0.2) < 1e-9 && rc.body.tile.endsWith('TILE') && rc.body.seed === 7 && rc.body.prompt == 'my own text', 'repair request: strength, cross width as a fraction, tile, prompt');
  ok(T.TL.src.endsWith('FIXED') && $('status').textContent.includes('9.1 → 1.4') && $('tlrepair').disabled === false, 'repair replaces the workbench tile, reports the seam score and re-enables the button');
  T.TL.src = null; $('status').textContent = ''; await T.tlRepair(); ok($('status').textContent.includes('workbench'), 'repair without a tile: clear message');
  apiQueue = [new Error('CUDA out of memory')]; T.TL.src = 'data:image/png;base64,TILE'; await T.tlRepair(); ok($('status').textContent.includes('out of memory') && $('tlrepair').disabled === false, 'a failed repair shows the error and re-enables the button');
  // animation
  set({ anmode: 'ripple', anframes: '6', andir: 'down', anms: '90', anamt: '2', anname: 'water' }); const ab = T.anBody();
  ok(ab.mode == 'ripple' && ab.frames === 6 && ab.ms === 90 && ab.amount === 2 && ab.name == 'water' && ab.direction == 'down' && ab.tile.endsWith('TILE'), 'animation request has typed fields');
  apiQueue = [{ frames: ['data:image/png;base64,F0', 'data:image/png;base64,F1', 'data:image/png;base64,F2'], ms: 90 }]; await T.anMake(); await new Promise(r => setTimeout(r, 30));
  ok(T.AN.frames.length == 3 && T.AN.ms == 90 && T.AN.timer && $('status').textContent.startsWith('3 frames, 90 ms'), 'frames are loaded and the preview loops'); T.anStop(); ok(T.AN.timer === null, 'the preview stops (it is stopped when you leave the tab)');
  apiQueue = [{ dir: '/x/water_anim', frames: 6, ms: 90, sheet: [96, 16], files: ['water.png', 'water.tres'] }]; await T.anExport(); ok(calls[calls.length - 1].url == '/api/tiles/export_anim' && $('status').textContent.startsWith('Exported 6 frames (96×16 strip, 90 ms)'), 'animation export request and report');
  T.TL.src = null; $('status').textContent = ''; await T.anMake(); ok($('status').textContent.includes('workbench'), 'animation without a tile: clear message');
  // 61N-D: history restores captured generation parameters even with stale UI snapshots.
  T.hUse({kind:'generate',ui:{artstyle:'pixel',genBodyBase:false,prompt:'old'},params:{kind:'sprite',art_style:'head_6',body_base:true,prompt:'neutral mannequin',negative:'extra fingers'}});
  const restored=T.applied[T.applied.length-1];
  ok(restored.artstyle==='head_6'&&restored.genBodyBase===true&&restored.prompt==='neutral mannequin'&&restored.neg==='extra fingers','history restores actual mode, style and prompt');
  set({artstyle:'head_6',genBodyBase:true,prompt:'neutral mannequin'});
  const preview={style_text:'six head heights',positive:'assembled',negative:'negative',kind:'body_base',art_style:'head_6',checkpoint:'SDXL',background:'white'};
  apiQueue=[preview];await T.genPromptPreview();
  ok($('genPromptPositive').textContent==='assembled'&&$('genPromptStyle').textContent==='six head heights','preview renders returned engine text');
  set({prompt:'different'});T.genPromptStale();
  ok($('genPromptPositive').textContent===''&&$('genPromptStatus').textContent.includes('Settings changed'),'changing prompt invalidates visible preview');
  let resolve;apiQueue=[()=>new Promise(r=>resolve=r)];const pending=T.genPromptPreview();T.genPromptInvalidate();resolve(preview);await pending;
  ok($('genPromptPositive').textContent==='','late preview cannot overwrite invalidated project snapshot');
  apiQueue=[new Error('preview unavailable')];await T.genPromptPreview();
  ok($('genPromptStatus').textContent.includes('preview unavailable'),'preview error reported');
  console.log(fail ? fail + ' FAILED' : 'ALL PASSED'); process.exit(fail ? 1 : 0);
})().catch(e => { console.error(e.stack || e); process.exit(1); });
