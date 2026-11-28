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
(motion / "diffusion_pytorch_model.safetensors").touch()
ready = A.readiness(root)
model = "animatediff/anime/v2"
ok(ready["ready"] and ready["models"][0]["name"] == model, "discover compatible local models")
ok(not A.readiness(root / "missing")["ready"], "missing folders reported")
body = dict(model=model, reference=data_url(Image.new("RGBA",(32,48),(50,80,120,255))), guidance={"preset":"idle_minimal"}, seed=42)
def fake(b,m,im,q):
    ok(b == base and m == motion and im.size == (512,512), "selected model and prepared reference")
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
done("test_animatediff_video")
