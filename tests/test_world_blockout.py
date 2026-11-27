"""Shared-layout assembly and prompt routing with synthetic artwork, no GPU."""
from _common import *
from engine import world as W, world_blockout as B, generate as G
from PIL import Image, ImageDraw
import json
d={**W.default(),"width":320,"height":240,"spawn":[160,180],"prompt":"modern anime forest trail with mossy rocks"}
c=B.settings({"seed":12,"rocks":2,"trees":4,"foreground":1})
plan=B.layout(d,c)
ok(plan==B.layout(d,c),"deterministic shared layout")
ok(plan!=B.layout(d,{**c,"seed":13}),"seed controls prop layout")
ok(B.needed({**c,"rocks":0,"trees":0,"foreground":0})==["background","ground","trail"],"optional object passes")
assets={}
for role in B.needed(c):
    if role in ("background","ground","trail"):
        im=Image.new("RGBA",(64,64),{"background":(10,20,30,255),"ground":(20,80,30,255),"trail":(130,90,50,255)}[role])
    else:
        im=Image.new("RGBA",(40,60),(255,255,255,255));ImageDraw.Draw(im).rectangle((10,8,30,50),fill=(80,50,30,255))
    assets[role]=B.normalize(im,role,(255,255,255),40)
out=B.assemble(d,c,assets)
ok(len(out["layers"])==10 and out["spawn"]==plan["spawn"],"separate visual layers and spawn")
ok(out["blockout"]==c and W.validate(json.loads(json.dumps(out)))[0]==out,"portable layout settings")
ok([x["role"] for x in out["layers"][:3]]==["background","ground","ground_detail"],"plates and trail ordered")
ok(out["layers"][-1]["role"]=="foreground","foreground on top")
ok(W.render(out)[0].size==(320,240),"composite renders")
trail=W.image(out["layers"][2]["image"])
ok(trail.getpixel(tuple(plan["spawn"]))[3]>240 and trail.getpixel((0,239))[3]==0,"path geometry and spawn aligned")
for role in B.needed(c):
    p,k=B.prompt(d,c,role);positive,negative=G.prompt_pair(p,"","white",k,"custom")
    ok("modern anime forest trail" in positive and "single character" not in positive,"environment prompt "+role)
    ok(("plain flat solid white background" in positive)==(role in B.ROLES[3:]),"isolated props only "+role)
for bad in ({**d,"view":"side"},{**d,"prompt":""},{**d,"width":2500,"height":2000}):
    try:B.layout(bad,c);ok(False,"reject invalid blockout")
    except ValueError:ok(True,"reject invalid blockout")
try:B.assemble(d,c,{});ok(False,"missing assets")
except ValueError:ok(True,"missing assets rejected")
try:B.normalize(Image.new("RGB",(32,32),"white"),"rock",(255,255,255));ok(False,"blank asset")
except ValueError:ok(True,"blank prop rejected")
done("test_world_blockout")
