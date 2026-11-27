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
for name in styles.PRESETS:
    regular=generate.build_prompt("standing subject",art_style=name)
    base=generate.build_prompt("front view, neutral pose",kind="body_base",art_style=name)
    neg=generate.negative_for("body_base",name)
    ok("detailed costume" not in regular and "intricate costume" not in regular,"neutral style "+name)
    ok("featureless mannequin" in base and "front view, neutral pose" in base and "head to toe" in base,"base prompt "+name)
    ok(all(word in neg for word in ("armor","cape","boots","clothing")),"base clothing negatives "+name)
    ok("armor" not in generate.negative_for("sprite",name),"regular negatives unchanged "+name)
ok("featureless mannequin" in generate.build_prompt("",kind="body_base"),"blank mannequin description supported")
ok("blue armor" in generate.build_prompt("blue armor"),"explicitly requested ordinary gear preserved")
for style in styles.PRESETS:
    for kind in ("sprite","body_base","tile","prop","icon","ui"):
        positive,negative=generate.prompt_pair("neutral subject","extra exclusion","magenta",kind,style)
        ok(positive==generate.build_prompt("neutral subject","magenta",kind,style) and negative=="extra exclusion, "+generate.negative_for(kind,style),"prompt pair parity "+style+" "+kind)
ok(generate.prompt_pair("subject")[1]==generate.NEGATIVE,"blank user negative adds no stray delimiter")
for heads,word in zip(range(2,8),("twice","three times","four times","five times","six times","seven times")):
    style="head_"+str(heads)
    text=styles.PRESETS[style]
    ok(word+" head height" in text,"exact head-height wording "+style)
    ok(not any(term in text for term in ("costume","armor","cape","weapon","clothing","outfit","accessories")),"no subject or outfit injection "+style)
    for kind in ("sprite","body_base"):
        positive,negative=generate.prompt_pair("neutral standing pose",kind=kind,art_style=style)
        ok(positive.startswith(text) and "neutral standing pose" in positive and negative==generate.negative_for(kind,style),"proportion prompt "+kind+" "+style)
done("test_styles")
