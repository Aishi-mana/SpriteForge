"""Deterministic reference analysis and environment prompt integration."""
from _common import *
from engine import world as W, world_style as S, world_blockout as B
from PIL import Image, ImageDraw
import json
im=Image.new("RGBA",(64,64),(0,255,0,0))
draw=ImageDraw.Draw(im);draw.rectangle((8,8,39,55),fill=(200,40,40,255));draw.rectangle((40,8,55,55),fill=(20,20,20,255))
profile=S.analyze(data_url(im),source="Approved sprite")
ok(profile==S.analyze(data_url(im),source="Approved sprite"),"deterministic reference analysis")
ok("#00ff00" not in profile["palette"] and "#c82828" in profile["palette"],"transparent pixels excluded")
ok(profile["reference"] and not profile["image_condition"] and not profile["accents"],"safe default text-only guidance")
ok(S.validate(json.loads(json.dumps(profile)))==profile,"profile portable")
d={**W.default(),"prompt":"forest trail","style_profile":profile}
ok(W.validate(d)[0]["style_profile"]==profile,"world profile persists")
p,_=B.prompt(d,{},"rock")
ok("forest trail" in p and S.guidance(profile) in p and "#c82828" not in p,"style guidance without forced palette")
edited={**profile,"accents":True,"notes":"subtle blue shadows","shading":"cel","linework":"clean"}
for role in B.needed({}):
    prompt,_=B.prompt({**d,"style_profile":edited},{},role)
    ok("#c82828" in prompt and "subtle blue shadows" in prompt and "clean cel shading" in prompt,"shared profile "+role)
ok(S.guidance({**profile,"enabled":False})=="","disabled profile no effect")
ok("do not depict its character" in S.guidance({**profile,"image_condition":True}),"reference style intent")
for bad in ({**profile,"strength":2},{**profile,"palette":["red"]},{**profile,"shading":"invalid"},{**profile,"image_condition":True,"reference":None}):
    try:S.validate(bad);ok(False,"reject invalid profile")
    except ValueError:ok(True,"reject invalid profile")
try:S.analyze(data_url(Image.new("RGBA",(64,64))));ok(False,"reject blank reference")
except ValueError:ok(True,"reject blank reference")
done("test_world_style")
