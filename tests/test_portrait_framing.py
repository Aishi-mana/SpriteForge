from _common import *
from engine import generate as G
from engine.main import _portrait_aspect, framed_portrait, FramedPortraitParams
from fastapi import HTTPException
for key,(positive,negative) in G.PORTRAIT_FRAMINGS.items():
    for style in ("pixel","anime"):
        ok(positive in G.build_prompt("knight","white",key,style) and negative in G.negative_for(key,style),"framing "+key+" "+style)
im=Image.new("RGBA",(64,64),(200,0,0,255))
for aspect,ratio in (("1:1",(1,1)),("3:4",(3,4)),("2:3",(2,3))):
    out=_portrait_aspect(im,aspect)
    ok(out.width*ratio[1]==out.height*ratio[0] and out.width>=64 and out.height>=64,"aspect "+aspect)
out=_portrait_aspect(im,"2:3",False,"white")
ok(out.getpixel((0,0))==(255,255,255,255),"opaque padding")
out=_portrait_aspect(im,"2:3",True)
ok(out.getpixel((0,0))[3]==0 and out.getpixel((32,48))==(200,0,0,255),"transparent padding preserves artwork")
try:
    framed_portrait(FramedPortraitParams(prompt="knight",checkpoint="unused",framing="invalid"))
    ok(False,"invalid framing")
except HTTPException as e:
    ok(e.status_code==400,"invalid framing rejected")
done("test_portrait_framing")
