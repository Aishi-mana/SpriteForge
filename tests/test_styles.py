"""GPU-free Phase 23 regression checks."""
from _common import *
from engine import styles, generate
import numpy as np
from PIL import Image
ok(generate.build_prompt("knight").startswith("pixel art"), "default pixel prompt unchanged")
ok(generate.negative_for("sprite") == generate.NEGATIVE, "default pixel negatives unchanged")
for name in styles.PRESETS:
    if name != "pixel":
        ok("pixel art" not in generate.build_prompt("knight", art_style=name), name + " prompt does not force pixels")
        ok("gradient" not in generate.negative_for("sprite", name), name + " allows smooth shading")
a = np.full((256, 256, 3), 255, dtype=np.uint8)
a[64:192, 64:192] = np.arange(128, dtype=np.uint8)[None,:,None]
im, info = styles.finish(Image.fromarray(a), 256)
ok(im.size == (256,256) and info["pipeline"] == "hd", "HD output dimensions")
ok(im.getpixel((0,0))[3] == 0 and im.getpixel((100,100))[3] == 255, "background transparent and subject opaque")
ok(len(set(im.getpixel((x,100)) for x in range(70,180))) == 110, "full colour gradient retained")
opaque, _ = styles.finish(Image.fromarray(a), 256, False)
ok(opaque.getpixel((0,0))[3] == 255, "background removal optional")
done("test_styles")
