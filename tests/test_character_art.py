from _common import *
from engine import generate as G, projects
for style in ("pixel","anime","custom"):
    p=G.build_prompt("red cape, back view", "white", "character_art", style)
    neg=G.negative_for("character_art",style)
    ok("head to toe" in p and "back view" in p and "feet out of frame" in neg and "full body" not in neg,"full body prompt "+style)
root=tmpdir()
im=Image.new("RGBA",(64,128),(255,0,0,255))
from engine.modular import png_uri
u=png_uri(im)
projects.save(root,"master",{"images":{"characterart":u}})
ok(projects.load(root,"master")["images"]["characterart"] is not None,"master artwork survives project roundtrip")
projects.save(root,"master",{"images":{}})
ok(projects.load(root,"master")["images"]["characterart"] is None,"master artwork clears")
done("test_character_art")
