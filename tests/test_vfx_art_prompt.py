"""VFX prompt composition without loading a model."""
from _common import *
from engine import generate as gen
for style in ("pixel","custom"):
    positive,negative=gen.prompt_pair("golden flame","green", "white","vfx_art",style)
    ok("golden flame" in positive and "single isolated visual effect" in positive,"effect prompt")
    ok("single character" not in positive and "full body" not in positive,"no character framing")
    ok("green" in negative and "sprite sheet" in negative,"effect negative prompt")
done("test_vfx_art_prompt")
