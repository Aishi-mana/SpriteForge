"""GPU-free tests of Phase 24 HD rendering."""
from _common import *
from engine import rig, exporter
from PIL import Image
import numpy as np
import tempfile
from pathlib import Path

sp, j, ov = synth_sprite()
hd = sp.resize((sp.width * 4, sp.height * 4), Image.Resampling.LANCZOS)
hj = {k: [v[0]*4, v[1]*4] for k,v in j.items()}
a, meta = rig.render(hd, hj, [], "walk", 2, overlap=0)
ok(meta["render_mode"] == "hd" and len(a) == 2, "HD path selected")
ok(any(((np.asarray(im)[...,3] > 0) & (np.asarray(im)[...,3] < 255)).any() for im in a), "HD render preserves fractional alpha")
ok(len(np.unique(np.asarray(a[0]).reshape(-1,4), axis=0)) > 64, "HD render retains full colour")
p, pm = rig.render(sp, j, ov, "walk", 2)
ok(pm["render_mode"] == "pixel" and set(np.unique(np.asarray(p[0])[...,3])) <= {0,255}, "pixel alpha stays binary")
try:
    rig.render(Image.new("RGBA",(1024,1024)), hj, [], "death", 32)
    ok(False, "HD budget")
except ValueError:
    ok(True, "HD budget rejects oversized clip before allocation")
with tempfile.TemporaryDirectory() as tmp:
    result = exporter.export_pack([dict(name="walk", fps=10, loop=True, frames=a, pivot=meta["pivot"])], {"smooth":True,"gif":False}, "hd", tmp)
    root = Path(result["dir"])
    ok("texture_filter = 2" in (root/"hd.tscn").read_text(), "Godot linear filter")
    ok("FilterMode.Bilinear" in (root/"SpriteForgeImporter.cs").read_text(), "Unity linear filter")
done("test_hd_rig")
