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
ui = (Path(__file__).resolve().parents[1] / "ui/index.html").read_text(encoding="utf-8")
ok('id="ffADControls"' in ui and 'value="animatediff"' in ui and "count<8||count>16" in ui,"visible workflow and frame count")
ok('id="ffADPrepare"' in ui and "function ffADGate()" in ui and "function ffADReport" in ui, "visible setup and readiness gate")
done("test_animatediff_video")
