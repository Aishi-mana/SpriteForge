"""Model classification (realistic tensor names), diagnostics report, assistant (llama.cpp) manager with a fake server."""
import os, stat, struct, time
from _common import *
from engine import diag, llm

def mk(path, keys, trunc=0):
    off = 0; h = {}
    for k in keys: h[k] = {"dtype": "F16", "shape": [4], "data_offsets": [off, off + 8]}; off += 8
    hb = json.dumps(h).encode(); blob = struct.pack("<Q", len(hb)) + hb + b"\0" * off; Path(path).write_bytes(blob[:-trunc] if trunc else blob)
d = tmpdir()
SDXL = ["model.diffusion_model.input_blocks.4.1.transformer_blocks.0.attn1.to_q.weight", "model.diffusion_model.label_emb.0.0.weight", "conditioner.embedder.1.model.transformer.resblocks.0.attn.in_proj_weight", "first_stage_model.decoder.conv_in.weight"]
cases = [("sdxl", SDXL), ("sd15", ["cond_stage_model.transformer.text_model.encoder.layers.0.self_attn.k_proj.weight", "model.diffusion_model.input_blocks.1.1.transformer_blocks.0.attn1.to_q.weight"]),
         ("dit", ["model.diffusion_model.double_blocks.0.img_attn.qkv.weight", "model.diffusion_model.single_blocks.0.linear1.weight"]),
         ("dit", ["model.diffusion_model.double_stream_blocks.0.block.attn1.to_q.weight"]), ("dit", ["transformer_blocks.0.attn.add_q_proj.weight", "img_in.weight", "txt_in.weight"]),
         ("sdxl", ["unet.add_embedding.linear_1.weight", "unet.down_blocks.1.attentions.0.transformer_blocks.0.attn1.to_q.weight", "text_encoder_2.text_model.embeddings.position_ids"]), ("unknown", ["some.random.tensor"])]
for want, keys in cases:
    mk(d / "m.safetensors", keys); diag._HDR.clear(); ok(diag.inspect_file(d / "m.safetensors")["kind"] == want, f"checkpoint '{want}' recognised from realistic tensor names ({keys[0][:44]}...)")
lcases = [("sdxl", ["lora_unet_down_blocks_1_attentions_0_transformer_blocks_0_attn1_to_q.lora_down.weight", "lora_te2_text_model_encoder_layers_0_self_attn_k_proj.lora_up.weight"]),
          ("unknown", ["lora_unet_input_blocks_4_1_transformer_blocks_0_attn1_to_q.lora_down.weight"]), ("other", ["lora_unet_double_blocks_0_img_attn_proj.lora_down.weight"]),
          ("other", ["diffusion_model.transformer_blocks.0.attn.to_q.lora_A.weight"]), ("other", ["diffusion_model.blocks.0.cross_attn.k.lora_down.weight"])]
for want, keys in lcases:
    mk(d / "l.safetensors", keys); diag._HDR.clear(); ok(diag.inspect_file(d / "l.safetensors", True)["kind"] == want, f"LoRA '{want}' recognised ({keys[0][:44]}...)")
mk(d / "t.safetensors", SDXL, trunc=9); ok(diag.inspect_file(d / "t.safetensors")["status"] == "bad", "a truncated download is detected")
(d / "h.safetensors").write_bytes(b"<html>error page</html>" * 5); ok(diag.inspect_file(d / "h.safetensors")["status"] == "bad", "an HTML error page saved as .safetensors is detected")

md = d / "models"; (md / "checkpoints").mkdir(parents=True); (md / "loras").mkdir()
mk(md / "checkpoints" / "sd_xl_base_1.0.safetensors", SDXL); mk(md / "checkpoints" / "flux1-dev-fp8.safetensors", cases[2][1]); mk(md / "loras" / "pixel-art-xl-v1.1.safetensors", lcases[0][1])
rows = {c["name"]: c for c in diag.check_models(str(md))}
ok(rows["Checkpoints"]["status"] in ("ok", "warn") and rows["Recommended base (sd_xl_base_1.0)"]["status"] == "ok" and rows["Pixel-art LoRA"]["status"] == "ok", "models check finds the SDXL base and the pixel-art LoRA")
ok(diag.check_models(str(d / "nope"))[0]["status"] == "fail", "missing models folder -> fail with a fix")
rep = diag.run_checks(d, str(md), {"settings": {"search_dir": "C:/AI", "model": "", "gpu_layers": 0, "ctx": 4096, "idle_min": 10, "port": 8766}, "server": "", "models": [], "running": False, "ready": False})
ok({"System", "GPU", "Models", "Downloads", "Assistant", "Self-test"} <= {c["section"] for c in rep["checks"]} and (d / "diagnostics.txt").exists(), "full report has every section and is saved as diagnostics.txt")
ok(all(c["status"] == "ok" for c in rep["checks"] if c["section"] == "Self-test"), "all built-in self-tests pass")
diag.record_error("/api/x", 500, "boom"); ok("boom" in diag.build_text(rep["checks"], d), "recent API errors appear in the report")

if os.name != "posix":
    ok(True, "assistant manager test skipped (needs a POSIX shell script)")
else:
    bd = d / "AI" / "llama" / "bin"; bd.mkdir(parents=True); (d / "AI" / "models").mkdir()
    fake = bd / "llama-server"; fake.write_text('''#!/usr/bin/env python3
import sys, time, json
from http.server import BaseHTTPRequestHandler, HTTPServer
a = sys.argv
if "--version" in a: print("version: 4567 (abc) built with cuda"); sys.exit(0)
port = int(a[a.index("--port") + 1]); t0 = time.time()
class H(BaseHTTPRequestHandler):
    def log_message(s, *x): pass
    def do_GET(s):
        ok = time.time() - t0 > 1.5 and s.path == "/health"; s.send_response(200 if ok else 503); s.end_headers(); s.wfile.write(b"{}")
    def do_POST(s):
        n = int(s.headers.get("Content-Length", 0)); s.rfile.read(n); s.send_response(200); s.send_header("Content-Type", "text/event-stream"); s.end_headers()
        for tok in ["Sure ", '<set field="prompt">', "red knight", "</set>"]:
            s.wfile.write(("data: " + json.dumps({"choices": [{"delta": {"content": tok}}]}) + "\\n\\n").encode()); s.wfile.flush(); time.sleep(.03)
        s.wfile.write(b"data: [DONE]\\n\\n")
HTTPServer(("127.0.0.1", port), H).serve_forever()
''')
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC); (d / "AI" / "models" / "tiny-Q4.gguf").write_bytes(b"\0" * 60 * 1024 * 1024); (d / "AI" / "models" / "mmproj-x.gguf").write_bytes(b"\0" * 60 * 1024 * 1024); (d / "AI" / "models" / "small.gguf").write_bytes(b"\0" * 10 * 1024 * 1024)
    cfg = {"llm_search_dir": str(d / "AI"), "llm_port": 8793}; m = llm.Manager(d, lambda: dict(cfg), lambda u: cfg.update(u)); st = m.state(rescan=True)
    ok(st["server"].endswith("llama-server") and [x["name"] for x in st["models"]] == ["tiny-Q4.gguf"], "finds llama-server and the model; skips mmproj and tiny files")
    ev = [json.loads(e[5:]) for e in m.chat_events([{"role": "user", "content": "hi"}])]; ok("Choose a .gguf" in ev[0]["error"], "no model chosen -> helpful message")
    for bad in (dict(server="/bin/sh"), dict(model="/etc/passwd")):
        try: m.update(**bad); ok(False, f"{list(bad)[0]} accepted")
        except llm.LlmError: ok(True, f"only a file named llama-server / a .gguf can be configured ({list(bad)[0]})")
    m.update(model=str(d / "AI" / "models" / "tiny-Q4.gguf")); out = [json.loads(e[5:]) for e in m.chat_events([{"role": "user", "content": "make a prompt"}], "Tab: Generate")]
    text = "".join(o.get("token", "") for o in out); ok(any("status" in o for o in out) and "<set field=\"prompt\">red knight</set>" in text and out[-1].get("done"), "loads the model on demand, streams tokens, finishes")
    ok(m.state()["ready"], "server stays loaded after chat"); m.update(ctx=2048); ok(not m.state()["running"], "changing settings stops the running server")
    m.start(); m.settings = (lambda s=m.settings: {**s(), "idle_min": 1}); m.last_used = time.time() - 120
    for _ in range(20):
        time.sleep(1)
        if not m._alive(): break
    ok(not m._alive(), "idle unload stops the server")
    m.settings = llm.Manager.settings.__get__(m); ok(m.selftest()["tokens"] >= 1, "assistant self-test returns load time and speed"); m.stop()
    cc = diag.check_assistant(m.state(rescan=True), d / "llm.log"); ok(any("cuda" in c["detail"].lower() for c in cc if c["name"] == "llama-server"), "diagnostics reports the llama-server version and build")
done("test_diag_llm")
