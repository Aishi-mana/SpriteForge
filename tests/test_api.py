"""Endpoint functions called directly (no web server needed). The model is replaced by fakes; with real fastapi installed nothing is stubbed."""
import asyncio, inspect, struct
from _common import *
from PIL import ImageDraw
stubbed = install_fastapi_stubs()
from engine import main as M, rig, templates as T, directions as D, projects, diag, palettes
HTTPException = http_exception()
tmp = tmpdir(); M.ROOT = tmp; M.CFG_PATH = tmp / "config.json"; palettes.load_into_px(tmp)
md = tmp / "models"; (md / "checkpoints").mkdir(parents=True); (md / "loras").mkdir()
def mk(path, keys):
    off = 0; h = {}
    for k in keys: h[k] = {"dtype": "F16", "shape": [4], "data_offsets": [off, off + 8]}; off += 8
    hb = json.dumps(h).encode(); Path(path).write_bytes(struct.pack("<Q", len(hb)) + hb + b"\0" * off)
mk(md / "checkpoints" / "sd_xl_base_1.0.safetensors", ["model.diffusion_model.input_blocks.4.1.transformer_blocks.0.attn1.to_q.weight", "conditioner.embedder.1.x", "model.diffusion_model.label_emb.0.0.weight"])
mk(md / "checkpoints" / "flux1.safetensors", ["model.diffusion_model.double_blocks.0.x"]); mk(md / "loras" / "pixel-art-xl-v1.1.safetensors", ["lora_unet_down_blocks_0_transformer_blocks_0.lora_down.weight", "lora_te2_x.lora_up.weight"])
M.CFG_PATH.write_text(json.dumps({"models_dir": str(md)})); M.llmm.stop(); M.llmm = M.llm.Manager(tmp, M.cfg, M._save_cfg)
DEF = dict(negative="", lora="", lora_weight=1.0, steps=25, cfg=7.0, seed=-1, sampler="euler_a", bg_tol=40, clean=True, strength=.85, ip_scale=.8, freedom=2, colors=20, palette_src="reference", n=2, height=64, style="normal",
           prompt="", ref=None, mode="auto", size=64, palette="none", remove_bg=True, remove_shadow=True, crisp=True, outline="none", overrides="[]", anim="walk", frames=8, fps=10, facing="right", near="r", weapon="r", amp=1.0,
           pad=0, overlap=1, ss=4, export=False, name="sprite", refine=False, checkpoint="sd_xl_base_1.0.safetensors", character="", radius=0.0, secondary="", keyframes="[]", art_style="pixel", hd_size=768, transparent=False, view="front")
def A(fn, **kw):
    """Call an endpoint function, filling unspecified Form/File params from DEF (works with stubs and with real fastapi)."""
    args = {}
    for p in inspect.signature(fn).parameters:
        if p in kw: args[p] = kw[p]
        elif p in DEF: args[p] = DEF[p]
    return fn(**args)
def fails(fn, code, **kw):
    try: A(fn, **kw); return False
    except HTTPException as e: return e.status_code == code

M.CFG_PATH.write_text('{"models_dir": "C:\\Users\\x\\models"}'); ok(M.cfg()["models_dir"].replace("\\", "/") == "C:/Users/x/models", "config.json with Windows backslashes is repaired, not fatal")
M.CFG_PATH.write_text(json.dumps({"models_dir": str(md)}))
s = M.state(); ok(s["ckpt_kinds"] == {"flux1.safetensors": "dit", "sd_xl_base_1.0.safetensors": "sdxl"} and s["lora_kinds"]["pixel-art-xl-v1.1.safetensors"] == "sdxl", "state tags every checkpoint / LoRA with its model family")
ok("cga16" in s["palettes"], "state lists palettes")
try: M._paths("nope.safetensors"); ok(False, "paths")
except HTTPException as e: ok(e.status_code == 400, "unknown checkpoint -> 400")
ok(M._secondary("") is None and M._secondary('{"enabled": false}') is None and M._secondary({"enabled": True, "flutter": 99, "parts": {"cape": {"segments": 99}}})["flutter"] == 2, "secondary settings are sanitised")

sp, J, OV = synth_sprite(); big = sp.resize((320, 512), Image.NEAREST)
r = A(M.pixelize_ep, file=Up(big), mode="auto", size=64, colors=8); ok(r["results"][0]["info"]["grid"] == 8, "pixelize endpoint detects the grid")
r = A(M.rig_autoplace, sprite=Up(sp)); ok(set(r["joints"]) == set(rig.JOINTS), "rig autoplace")
r = A(M.rig_parts, sprite=Up(sp), joints=json.dumps(J), overrides=json.dumps(OV)); ok(r["overlay"].startswith("data:image/png"), "rig parts overlay")
r = A(M.rig_animate, sprite=Up(sp), joints=json.dumps(J), overrides=json.dumps(OV), anim="walk", frames=6, secondary=json.dumps({"enabled": True})); ok(len(r["frames"]) == 6 and r["fps"] == 10, "rig animate")
ok(fails(M.rig_animate, 400, sprite=Up(sp), joints=json.dumps(J), anim="moonwalk"), "unknown animation -> 400")
fake_calls = []
def fake_inpaint(*a, **k):
    fake_calls.append(a); img, mask = a[6], a[7]; arr = np.asarray(img).copy(); arr[np.asarray(mask) > 0] = (40, 80, 200); return Image.fromarray(arr)
M.gen.inpaint = fake_inpaint
r = A(M.rig_animate, sprite=Up(sp), joints=json.dumps(J), overrides=json.dumps(OV), anim="walk", frames=4, refine=True, character="knight"); ok("key" in r and len(r["accept"]) == 4 and len(r["raw_frames"]) == 4, "AI cleanup path: key, accept flags, raw frames returned")
n_calls = len(fake_calls); A(M.rig_animate, sprite=Up(sp), joints=json.dumps(J), overrides=json.dumps(OV), anim="walk", frames=4, refine=True, character="knight"); ok(len(fake_calls) == n_calls, "the same cleanup request is served from cache (no second AI pass)")
rr = M.rig_redo(M.RedoBody(key=r["key"], frames=[1, 2], seed=-1, strength=.5)); ok(len(rr["frames"]) == 4 and len(fake_calls) > n_calls, "redo re-runs only the chosen frames")
try: M.rig_redo(M.RedoBody(key="nope", frames=[0])); ok(False, "redo expired")
except HTTPException as e: ok(e.status_code == 400, "redo with an unknown key -> 400")
pk = M.PackBody(sprite=data_url(sp), joints=J, overrides=OV, name="Hero", options={"gif": False}, anims=[M.PackAnim(anim="walk", count=4), M.PackAnim(anim="idle", count=3)], secondary={"enabled": True})
r = M.rig_export_pack(pk); ok(r["frames"] == 7 and Path(r["dir"]).exists(), "export pack renders and writes files")
try: M.rig_export_pack(M.PackBody(sprite=data_url(sp), joints=J, anims=[M.PackAnim(anim="walk"), M.PackAnim(anim="walk")])); ok(False, "dup")
except HTTPException as e: ok(e.status_code == 400, "duplicate animations in a pack -> 400")

d = A(M.template_dummy, height=9999, style="bogus", view="bogus"); ok(from_url(d["sprite"]).height == 128 and len(d["joints"]) == 15, "dummy endpoint clamps height and falls back on bad style/view")
ok(all(len(A(M.template_dummy, height=48, style="chibi", view=v)["overrides"]) > 50 for v in T.VIEWS), "all 5 dummy views are served with exact bone labels")
tpl, tj, tov = T.make_dummy(64, "normal", "front"); refim = Image.new("RGB", (100, 150), (255, 255, 255)); ImageDraw.Draw(refim).rectangle([30, 30, 70, 120], fill=(40, 80, 200))
r = A(M.template_generate, template=Up(tpl), ref=Up(refim), n=2, seed=5); ok(len(r["results"]) == 2 and from_url(r["results"][0]["sprite"]).size == tpl.size and r["results"][1]["info"]["seed"] == 6, "template generate: n results at the template's size, consecutive seeds")
ok(fails(M.template_generate, 400, template=Up(Image.new("RGBA", (32, 48), (0, 0, 0, 0)))), "empty template -> 400")
r = A(M.dirs_generate, ref=Up(refim), dirs=json.dumps(D.DIRS8), seed=42); ok([x["dir"] for x in r["results"]] == D.UNIQUE and r["error"] is None, "dirs generate: 8 directions -> 5 unique views")
ok(fails(M.dirs_generate, 400, ref=Up(refim), dirs="[]") and fails(M.dirs_generate, 400, ref=Up(refim), dirs='["X"]'), "empty / unknown direction lists -> 400")
slots = {k: {"sprite": data_url(from_url(v["sprite"])), "joints": v["joints"], "overrides": v["overrides"]} for k, v in {x["dir"]: x for x in r["results"]}.items()}
res = M.dirs_render(M.DirRender(slots=slots, clip=M.DirClip(anim="walk", count=4), dirs=D.DIRS8)); ok(len(res["dirs"]) == 8, "dirs render: 8 directions")
out = M.dirs_export(M.DirBody(slots=slots, clips=[M.DirClip(anim="walk", count=4), M.DirClip(anim="idle", count=3)], dirs=D.DIRS8, name="Hero", options={"gif": False})); ok(out["animations"] == 16, "dirs export: 2 clips x 8 directions")

parsed = A(M.pal_parse, file=Up(b"0d2b45\n203c56\n544e68\nffecd6\n", "Dawn.hex")); sv = M.pal_save(M.PalSave(name=parsed["name"], colors=parsed["colors"])); ok("Dawn" in M.state()["palettes"], "palette import -> save -> appears in the Fixed palette list")
r = A(M.pal_remap, file=Up(sp), palette=json.dumps(parsed["colors"]), dither="bayer4", strength=.6); ok(from_url(r["image"]).size == sp.size, "palette remap")
ok(len(A(M.pal_variants, file=Up(sp), shifts="[60,120]", protect="[]", chroma=1.0, keep_dark=True)["variants"]) == 2 and A(M.pal_extract, file=Up(sp), n=0)["total"] == 7, "palette variants / extract")
ok(fails(M.pal_remap, 400, file=Up(sp), palette="not json"), "bad colour list -> 400"); M.pal_delete("Dawn"); ok("Dawn" not in M.state()["palettes"], "palette delete")

def fake_generate(*a, **k):
    img = Image.new("RGB", (1024, 1024), (200, 200, 205)); ImageDraw.Draw(img).ellipse([300, 150, 700, 600], fill=(240, 200, 165)); n = a[13]; return [(img, a[8] + i) for i in range(n)]
M.gen.generate = fake_generate
r = A(M.portrait_base, prompt="knight", n=2, size=64, colors=12, seed=3, bg="light gray", ip_scale=.6); ok(len(r["results"]) == 2 and from_url(r["results"][0]["sprite"]).size == (64, 64), "portrait base: pixelised to the chosen size")
base = from_url(r["results"][0]["sprite"]); stream = "".join(A(M.portrait_expressions, base=Up(base), mask=json.dumps({"cx": .5, "cy": .45, "rx": .27, "ry": .3}), items=json.dumps([{"name": "happy", "text": ""}, {"name": "sad", "text": ""}]), character="x", strength=.82, extra=4))
ev = [json.loads(l[5:]) for l in stream.split("\n\n") if l.startswith("data:")]; ok([e["result"]["name"] for e in ev if "result" in e] == ["happy", "sad"] and ev[-1].get("done"), "portrait expressions stream one result per expression, then done")
pe = M.portrait_export(M.PortraitExport(name="Hero", images=[M.PortraitItem(name="neutral", image=data_url(base)), M.PortraitItem(name="happy", image=data_url(base)), M.PortraitItem(name="happy", image=data_url(base))], columns=2))
ok(pe["frames"] == 3 and "happy_2" in (Path(pe["dir"]) / "Hero_portraits.tres").read_text(), "portrait export: duplicate names are made unique; Godot gets one animation per expression")

M.projects_save({"name": "Knight", "settings": {"a": 1}, "images": {"ref": data_url(sp)}}); ok(M.projects_load("Knight")["settings"] == {"a": 1} and "Knight" in [p["name"] for p in M.projects_list()["projects"]], "project save / load / list through the API")
sid = M.projects_add_sprite("Knight", {"sprite": data_url(sp)})["id"]; ok(len(M.projects_sprites("Knight")["sprites"]) == 1, "saved sprites through the API"); M.projects_del_sprite("Knight", sid); M.projects_delete("Knight")
try: M.projects_load("../../etc"); ok(False, "traversal")
except HTTPException as e: ok(e.status_code == 400, "project path traversal -> 400")
rep = M.diag_run(); ok(rep["summary"] and any(c["section"] == "Models" for c in rep["checks"]), "diagnostics endpoint returns a structured report")
try: M.llm_config(M.LlmCfg(server="/bin/sh")); ok(False, "llm server")
except HTTPException as e: ok(e.status_code == 400, "assistant config only accepts a file named llama-server")
if stubbed:
    body, code = asyncio.run(M._http_error(types.SimpleNamespace(url=types.SimpleNamespace(path="/api/x")), HTTPException(500, "OutOfMemoryError: boom"))); ok(code == 500 and "boom" in str(list(diag.ERRORS)[-1]), "HTTP errors are recorded for the diagnostics report")
done("test_api")
