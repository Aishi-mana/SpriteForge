from _common import *
from engine import character_sprite as S, projects, main
from engine.modular import png_uri
from fastapi import HTTPException
from PIL import ImageDraw
im=Image.new("RGBA",(128,192))
d=ImageDraw.Draw(im)
d.rectangle((32,20,95,170),fill=(40,70,190,255))
d.rectangle((42,40,85,80),fill=(200,40,60,255))
pal=S.palette_from_art(im,8)
ok(len(pal)==2,"master foreground palette excludes transparency")
res=main.character_sprite(main.CharacterSpriteParams(prompt="knight",checkpoint="",reference=png_uri(im),conversion="direct",art_style="pixel",size=64,colors=8))
out=main._dec_img(res["results"][0]["sprite"])
ok(max(out.size)<=64 and res["results"][0]["info"]["palette_locked"],"direct pixel conversion without model")
ok(out.getchannel("A").getbbox() is not None,"sprite retains visible foreground")
hd=main.character_sprite(main.CharacterSpriteParams(prompt="knight",checkpoint="",reference=png_uri(im),conversion="direct",art_style="anime",hd_size=256))
ok(hd["results"][0]["info"]["art_style"]=="anime","direct HD conversion")
root=tmpdir()
projects.save(root,"sprite",{"images":{"characterart":png_uri(im),"charactersprite":png_uri(out)}})
saved=projects.load(root,"sprite")["images"]
ok(saved["characterart"] and saved["charactersprite"],"master and approved sprite persist separately")
try:
    main.character_sprite(main.CharacterSpriteParams(prompt="knight",checkpoint="",conversion="direct"))
    ok(False,"missing master")
except HTTPException as e:
    ok(e.status_code==400,"missing master rejected")
done("test_character_sprite")
