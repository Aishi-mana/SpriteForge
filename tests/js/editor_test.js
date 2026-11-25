// Drives the pixel editor's interaction layer (tools, undo, selection, apply...) against a fake DOM / canvas.
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, '../../ui/index.html'), 'utf8');
const code = html.slice(html.indexOf('/*PXE-START*/'), html.indexOf('// ---- where the editor is used ----'));
const FAKE = {}; let nimg = 0;
class ImageData { constructor(d, w, h) { this.data = d; this.width = w; this.height = h } }
class Image { set src(u) { const p = FAKE[u]; this.width = p.w; this.height = p.h; this.data = p.d; setTimeout(() => this.onload && this.onload(), 0) } }
function mkEl(id) { const el = { id, dataset: {}, style: {}, value: '', checked: false, textContent: '', innerHTML: '', width: 300, height: 150, children: [],
  classList: { _s: new Set(['hide']), toggle(c, f) { f ? this._s.add(c) : this._s.delete(c) }, contains(c) { return this._s.has(c) }, add(c) { this._s.add(c) }, remove(c) { this._s.delete(c) } },
  appendChild(c) { this.children.push(c) }, setPointerCapture() {}, getBoundingClientRect() { return { left: 0, top: 0, width: this.width, height: this.height } },
  getContext() { const e = this; return { buf: null, imageSmoothingEnabled: false, globalAlpha: 1, lineDashOffset: 0, clearRect() {}, fillRect() {}, strokeRect() {}, beginPath() {}, moveTo() {}, lineTo() {}, stroke() {}, setLineDash() {},
    drawImage(img) { if (img && img.data && arguments.length == 3) { this.buf = new Uint8ClampedArray(img.data) } }, getImageData(x, y, w, h) { return { data: new Uint8ClampedArray(this.buf || new Uint8ClampedArray(w * h * 4)), width: w, height: h } },
    putImageData(id) { this.buf = new Uint8ClampedArray(id.data) }, createImageData(w, h) { return { data: new Uint8ClampedArray(w * h * 4), width: w, height: h } } } } }; return el }
function mkCanvas() { const c = mkEl('canvas'), ctx = c.getContext(); c.getContext = () => ctx; c.toDataURL = () => { const k = 'data:fake' + (++nimg); FAKE[k] = { w: c.width, h: c.height, d: new Uint8ClampedArray(ctx.buf) }; return k }; return c }
const els = {}; const $ = id => els[id] || (els[id] = mkEl(id)); els.edcv = mkCanvas();
els.edbrush = mkEl('edbrush'); els.edbrush.value = '1'; els.edpick = mkEl('edpick'); els.edpick.value = '#000000'; els.edzoom = mkEl('edzoom'); els.edonion = mkEl('edonion'); els.edonion.checked = true; els.ped = mkEl('ped');
const buttons = ['pencil', 'eraser', 'fill', 'pick', 'line', 'rect', 'ellipse', 'select'].map(t => { const b = mkEl('b'); b.dataset.t = t; return b }); let keyHandler = null;
globalThis.document = { createElement: () => mkCanvas(), querySelectorAll: () => buttons, addEventListener: (n, f) => { if (n == 'keydown') keyHandler = f } };
globalThis.$ = $; globalThis.ImageData = ImageData; globalThis.Image = Image; globalThis.show = (id, v) => $(id).classList.toggle('hide', !v);
globalThis.dl = () => {}; globalThis.saveSprite = () => {}; globalThis.useRef = () => {}; globalThis.setAnim = () => {};
(0, eval)(code + ';globalThis.ED=ED;globalThis.PXE=PXE;globalThis.edcv=edcv;');
let fail = 0; const ok = (c, m) => { if (!c) { fail++; console.log('FAIL', m) } else console.log('ok  ', m) };
const px = (i, x, y) => Array.from(PXE.get(i, x, y)), eq = (a, b) => JSON.stringify(a) == JSON.stringify(b);
const down = (x, y) => edcv.onpointerdown({ clientX: x * ED.zoom + ED.zoom / 2, clientY: y * ED.zoom + ED.zoom / 2, pointerId: 1, preventDefault() {} });
const move = (x, y) => edcv.onpointermove({ clientX: x * ED.zoom + ED.zoom / 2, clientY: y * ED.zoom + ED.zoom / 2 }); const up = () => edcv.onpointerup({});
const key = (k, m = {}) => keyHandler({ key: k, target: { tagName: 'DIV' }, preventDefault() {}, ...m }); const wait = () => new Promise(r => setTimeout(r, 5));
(async () => {
  const W = 16, d = new Uint8ClampedArray(W * W * 4), put = (x, y, c) => d.set([...c, 255], (y * W + x) * 4);
  for (let y = 2; y < 6; y++) for (let x = 2; x < 6; x++) put(x, y, [200, 0, 0]); put(10, 10, [0, 0, 200]); FAKE['data:src'] = { w: W, h: W, d };
  let applied = null; openEditor('data:src', { label: 'Update test', apply: u => { applied = u } }); await wait();
  ok(ED.img && ED.img.w == 16 && !$('ped').classList.contains('hide') && ED.pal.length == 2 && eq(ED.pal[0], [200, 0, 0]), 'opens on the image with its palette, most used first');
  edTool('pencil'); down(8, 8); up(); ok(eq(px(ED.img, 8, 8), [200, 0, 0, 255]), 'pencil paints the selected colour');
  down(0, 15); move(5, 15); up(); ok([0, 1, 2, 3, 4, 5].every(x => px(ED.img, x, 15)[3] == 255), 'dragging draws a gap-free line');
  edTool('eraser'); down(8, 8); up(); ok(px(ED.img, 8, 8)[3] == 0, 'eraser clears'); edTool('pencil'); $('edbrush').value = '3'; down(12, 3); up(); ok(px(ED.img, 11, 2)[3] == 255 && px(ED.img, 13, 4)[3] == 255, '3x3 brush'); $('edbrush').value = '1';
  $('edmirror').checked = true; down(1, 8); up(); ok(px(ED.img, 1, 8)[3] == 255 && px(ED.img, 14, 8)[3] == 255, 'mirror mode paints the opposite side too'); $('edmirror').checked = false;
  down(7, 7); up(); edUndo(); ok(px(ED.img, 7, 7)[3] == 0, 'undo'); edRedo(); ok(px(ED.img, 7, 7)[3] == 255, 'redo'); edUndo();
  const n0 = ED.undo.length; down(0, 0); move(5, 0); move(5, 5); up(); ok(ED.undo.length == n0 + 1, 'a whole drag is ONE undo step'); edUndo();
  edTool('pick'); down(10, 10); ok(eq(ED.color, [0, 0, 200]) && ED.tool == 'pencil', 'picker takes the colour and returns to pencil'); down(4, 4); up(); ok(px(ED.img, 4, 4).join() == '0,0,200,255', 'painting uses the picked colour');
  ED.color = [10, 200, 10]; edTool('fill'); down(0, 10); up(); ok(px(ED.img, 0, 10)[1] == 200, 'fill floods the region'); edUndo();
  $('edfilled').checked = true; ED.color = [1, 2, 3]; edTool('rect'); down(10, 1); move(13, 3); ok(ED.shape && ED.shape.length == 12, 'rect preview while dragging'); up(); ok(px(ED.img, 12, 2).join() == '1,2,3,255' && ED.shape == null, 'rect commits on release'); $('edfilled').checked = false; edUndo();
  edTool('select'); down(2, 2); move(5, 5); up(); ok(ED.sel && ED.sel.w == 4 && ED.sel.h == 4, 'drag selects 4x4');
  down(3, 3); move(8, 8); up(); ok(px(ED.img, 2, 2)[3] == 0 && px(ED.img, 7, 7).join() == '200,0,0,255' && ED.sel.x == 7, 'moving a selection lifts and drops its pixels');
  edNudge(1, 0); ok(px(ED.img, 8, 7)[0] == 200, 'arrow nudge'); edDelete(); ok(px(ED.img, 8, 8)[3] == 0 && ED.sel == null, 'Delete clears the selection');
  edTool('select'); down(1, 1); up(); ok(ED.sel == null, 'a plain click deselects');
  edTool('pencil'); const f0 = PXE.clone(ED.img); edFlip(false); edFlip(false); ok(f0.d.every((v, i) => v == ED.img.d[i]), 'flip twice = identity');
  ED.color = [200, 0, 0]; $('edpick').value = '#00ff00'; edRecolor(); ok(!PXE.used(ED.img).has('200,0,0') && PXE.used(ED.img).has('0,255,0') && eq(ED.color, [0, 255, 0]), 'recolor everywhere + palette follows');
  key('e'); ok(ED.tool == 'eraser', 'E selects eraser'); key('b'); key(']'); ok($('edbrush').value == '2', '] grows brush'); ok(ED.orig.d.every((v, i) => v == d[i]), 'the original stays untouched for compare');
  const snap = PXE.clone(ED.img); edApply(); await wait(); ok(applied && FAKE[applied].d.every((v, i) => v == snap.d[i]) && $('ped').classList.contains('hide'), 'Apply hands back exactly the edited pixels and closes');
  openEditor('data:src', {}); await wait(); edTool('pencil'); down(0, 0); up(); edClose(); ok(!$('ped').classList.contains('hide') && $('edclose').textContent.startsWith('Discard'), 'closing with edits asks first'); edClose(); ok($('ped').classList.contains('hide'), 'second click closes');
  openEditor('data:src', {}); await wait(); ED.tool = 'pencil'; keyHandler({ key: 'e', target: { tagName: 'INPUT', type: 'text' }, preventDefault() {} }); ok(ED.tool == 'pencil', 'shortcuts ignored while typing in a text box');
  console.log(fail ? fail + ' FAILED' : 'ALL PASSED'); process.exit(fail ? 1 : 0);
})();
