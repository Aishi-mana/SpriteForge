from _common import *
from engine import main, projects
from engine.modular import png_uri
from unittest.mock import patch
from fastapi import HTTPException
from PIL import ImageDraw

im=Image.new("RGBA",(128,192))
ImageDraw.Draw(im).rectangle((25,15,102,170),fill=(30,90,200,255))
master=png_uri(im)
identity={"name":"Knight","hair":"red hair","outfits":[{"name":"Armor","description":"blue armor"}],"active_outfit":"Armor","locks":["hair"]}
ok(main._character_reference(master).size==(128,192),"reference dimensions preserved")
for bad in ("not png",png_uri(Image.new("RGBA",(1025,1),(0,0,0,255))),png_uri(Image.new("RGBA",(16,16)))):
    try:
        main._character_reference(bad)
        ok(False,"invalid reference")
    except HTTPException as e:
        ok(e.status_code==400,"invalid reference rejected")
for aspect,(x,y) in (("1:1",(1,1)),("3:4",(3,4)),("2:3",(2,3))):
    out=main._portrait_aspect(Image.new("RGBA",(1024,1024)),aspect,False,"white")
    ok(out.width*y==out.height*x and max(out.size)<=1024 and out.getchannel("A").getextrema()==(255,255),"bounded exact opaque aspect "+aspect)
base=dict(prompt="knight",checkpoint="unused",reference=master,identity=identity)
for change in (dict(n=4),dict(steps=101),dict(reference_strength=2),dict(colors=65)):
    try:
        main._character_budget(main.CharacterArtParams(**{**base,**change}))
        ok(False,"invalid budget")
    except HTTPException as e:
        ok(e.status_code==400,"invalid budget rejected")
def fake_run(*args,**kwargs):
    post=args[13]
    img,info=post(im)
    info.update(art_style=kwargs["art_style"])
    return {"results":[{"sprite":png_uri(img),"info":info}],"prompt":args[4]}
with patch.object(main,"_paths",return_value=("unused","unused")),patch.object(main,"_run",side_effect=fake_run),patch("engine.local_runtime.route",return_value=False):
    art=main.character_artwork(main.CharacterArtParams(**base,art_style="anime"))
    ok("red hair" in art["prompt"] and "blue armor" in art["prompt"],"art uses shared identity")
    port=main.character_gesture(main.CharacterGestureParams(**base,framing="half",gesture="wave",aspect="3:4"))
    ok("friendly wave" in port["prompt"] and "red hair" in port["prompt"],"gesture uses shared identity")
    ok(port["results"][0]["info"]["framing"]=="half","gesture retains framing metadata")
sprite=main.character_sprite(main.CharacterSpriteParams(**base,conversion="direct",art_style="pixel"))["results"][0]["sprite"]
root=tmpdir()
projects.save(root,"knight",{"character_identity":identity,"images":{"characterart":master,"charactersprite":sprite}})
saved=projects.load(root,"knight")
ok(saved["character_identity"]["active_outfit"]=="Armor" and saved["images"]["characterart"] and saved["images"]["charactersprite"],"character lifecycle project roundtrip")
done("test_character_integration")
