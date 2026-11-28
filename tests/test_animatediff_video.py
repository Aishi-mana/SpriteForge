from _common import *
from engine import animatediff_video as A
from PIL import Image
from pathlib import Path
import json

root = Path(tmpdir())
base = root / "animatediff/base/anime"
motion = root / "animatediff/motion/v2"
(base / "unet").mkdir(parents=True)
motion.mkdir(parents=True)
(base / "model_index.json").write_text(json.dumps({"_class_name":"StableDiffusionPipeline"}))
(base / "unet/config.json").write_text(json.dumps({"cross_attention_dim":768}))
(motion / "config.json").write_text(json.dumps({"_class_name":"MotionAdapter","block_out_channels":[320,640,1280,1280],"motion_max_seq_length":32}))
ok(not A.readiness(root)["ready"], "incomplete models not advertised")
for name in ("unet/diffusion_pytorch_model.safetensors", "vae/config.json", "vae/diffusion_pytorch_model.safetensors",
             "text_encoder/config.json", "text_encoder/model.safetensors", "tokenizer/vocab.json",
             "tokenizer/merges.txt", "tokenizer/tokenizer_config.json", "scheduler/scheduler_config.json"):
    path = base / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("fixture")
(motion / "diffusion_pytorch_model.safetensors").write_bytes(b"fixture")
(base.parent / "raw.safetensors").write_bytes(b"fixture")
other = root / "fresh"
other.mkdir()
setup = A.prepare_folders(other)
ok((other / "animatediff/base").is_dir() and (other / "animatediff/motion").is_dir() and not setup["ready"], "create empty folders without fake readiness")
ok(A.prepare_folders(other)["can_prepare"], "repeat folder creation")
try:
    A.prepare_folders("")
    ok(False, "unset directory must not be used")
except ValueError:
    ok(True, "unset directory rejected")
ready = A.readiness(root)
model = "animatediff/anime/v2"
ok(ready["ready"] and ready["models"][0]["name"] == model, "discover compatible local models")
ok(not A.readiness(root / "missing")["ready"], "missing folders reported")
ok(ready["raw_files"] == ["raw.safetensors"] and ready["base"][0]["ready"], "standalone weights diagnosed separately")
(base / "vae/config.json").unlink()
ok(not A.readiness(root)["ready"] and "Missing vae/config.json" in A.readiness(root)["base"][0]["issues"], "specific component failure")
(base / "vae/config.json").write_text("fixture")
# The user's layout: both Diffusers components are .bin, text encoder and adapter are safe.
for component in ("unet", "vae"):
    folder = base / component
    (folder / "diffusion_pytorch_model.safetensors").unlink()
    (folder / "diffusion_pytorch_model.bin").write_bytes(b"legacy fixture")
legacy = A.readiness(root)
ok(legacy["ready"] and legacy["models"][0]["legacy"] == ["unet", "vae"], "legacy component pair detected without reading pickle")
import hashlib
from unittest.mock import patch
from types import SimpleNamespace
source = base / "unet/diffusion_pytorch_model.bin"
calls = []
class FakeTensor:
    layout = "strided"
    def detach(self): return self
    def contiguous(self): return self
def fake_load(f, **kw):
    calls.append((f.read(), kw))
    return {"weight": FakeTensor()}
fake_torch = SimpleNamespace(__version__="2.8.0", Tensor=FakeTensor, strided="strided", load=fake_load)
try:
    A._verified_weights(source, A.LEGACY_SHA256["unet"], fake_torch)
    ok(False, "unknown legacy source must be rejected")
except ValueError:
    ok(not calls, "unknown source rejected before deserialization")
def fake_save(weights, path, metadata):
    assert set(weights) == {"weight"} and metadata == {"format":"pt"}
    Path(path).write_bytes(b"converted fixture")
fake_safe = types.ModuleType("safetensors.torch")
fake_safe.save_file = fake_save
fixture_hash = hashlib.sha256(b"legacy fixture").hexdigest()
with patch.dict(sys.modules, {"torch":fake_torch, "safetensors.torch":fake_safe}), patch.dict(A.LEGACY_SHA256, {"unet":fixture_hash,"vae":fixture_hash}):
    A.convert_legacy(base)
    ok(len(calls)==2 and all(kw=={"map_location":"cpu","weights_only":True} for _,kw in calls), "verified conversion uses restricted CPU tensor loading")
    ok(all((base / c / "diffusion_pytorch_model.bin").read_bytes()==b"legacy fixture" for c in ("unet","vae")), "original weights preserved")
    ok(all((base / c / "diffusion_pytorch_model.safetensors").read_bytes()==b"converted fixture" for c in ("unet","vae")), "converted files published")
    A.convert_legacy(base)
    ok(len(calls)==2 and not A.readiness(root)["models"][0]["legacy"], "converted files reused without repeat conversion")
body = dict(model=model, reference=data_url(Image.new("RGBA",(32,48),(50,80,120,255))), guidance={"preset":"idle_minimal"}, seed=42)
def fake(b,m,im,q):
    ok(b.samefile(base) and m.samefile(motion) and im.size == (512,512), "selected model and prepared reference")
    ok(q["frames"] == 16 and q["fps"] == 8 and q["steps"] == 12 and q["seed"] == 42, "short loop defaults")
    return b"fake mp4"
ok(A.generate(root,body,fake) == b"fake mp4", "video result handed off")
for change in ({"model":"animatediff/../v2"},{"frames":17},{"width":257},{"reference":"bad"}):
    try:
        A.generate(root,{**body,**change},fake)
        ok(False,"invalid request")
    except ValueError:
        ok(True,"invalid request rejected")
idle = A.settings(body)
ok(idle["strength"] == 0.5 and idle["cfg"] == 5.0 and "blinking" in idle["negative"], "default idle guidance and balanced sampling")
blink = A.settings({**body, "prompt":"Blink once, keep the mouth still", "ad_profile":"preserve"})
ok("Blink once" in blink["prompt"] and "blinking" not in blink["negative"] and "tiny periodic breathing only" not in blink["prompt"], "typed motion overrides conflicting idle preset")
ok(blink["strength"] == 0.35 and blink["cfg"] == 4.0 and "changing lighting" in blink["negative"], "preserve profile and lighting guidance")
motion = A.settings({**body, "ad_profile":"motion"})
ok(motion["strength"] == 0.65 and motion["cfg"] == 6.0, "more movement profile")
for profile in ("unknown", [], None):
    try:
        A.settings({**body, "ad_profile":profile})
        ok(False, "invalid profile accepted")
    except ValueError:
        ok(True, "invalid profile rejected")
ui = (Path(__file__).resolve().parents[1] / "ui/index.html").read_text(encoding="utf-8")
ok('id="ffADControls"' in ui and 'value="animatediff"' in ui and "count<8||count>16" in ui,"visible workflow and frame count")
ok('id="ffADPrepare"' in ui and "function ffADGate()" in ui and "function ffADReport" in ui, "visible setup and readiness gate")
ok('id="ffADProfile"' in ui and 'id="ffADReuseSeed"' in ui and "FF.adLastSeed=seed" in ui, "visible preservation controls and seed reuse")
# Exercise both current and older Diffusers memory API layouts without model weights.
memory_calls = []
def called(name):
    return lambda: memory_calls.append(name)
current = SimpleNamespace(vae=SimpleNamespace(enable_slicing=called("vae")),
                          unet=SimpleNamespace(enable_forward_chunking=called("chunk")),
                          enable_model_cpu_offload=called("offload"))
A.configure_memory(current)
ok(memory_calls == ["offload","vae","chunk"], "current component-level VAE API")
memory_calls.clear()
older = SimpleNamespace(vae=SimpleNamespace(), unet=SimpleNamespace(),
                        enable_model_cpu_offload=called("offload"),
                        enable_vae_slicing=called("legacy"))
A.configure_memory(older)
ok(memory_calls == ["offload","legacy"], "legacy pipeline VAE API fallback")
memory_calls.clear()
minimal = SimpleNamespace(vae=SimpleNamespace(), unet=SimpleNamespace(),
                          enable_model_cpu_offload=called("offload"))
A.configure_memory(minimal)
ok(memory_calls == ["offload"], "optional memory helpers absent without crashing")
ok('<option value="birefnet" selected>BiRefNet AI (local)</option>' in ui, "BiRefNet default transparency")
done("test_animatediff_video")
