"""Persistent manual corrections, prop transforms, exact local patch bounds."""
from _common import *
from engine import world as W, world_masks as M, world_polish as P
from PIL import Image, ImageDraw
import json
ground=Image.new("RGBA",(100,100),(30,80,40,255))
rock=Image.new("RGBA",(20,20));ImageDraw.Draw(rock).rectangle((3,2,16,18),fill="gray")
d={**W.default(),"width":100,"height":100,"spawn":[50,50],"prompt":"forest trail","layers":[
 dict(id="ground",role="ground_detail",image=data_url(ground)),
 dict(id="rock",role="objects",image=data_url(rock),x=40,y=40)]}
d,_=M.generate(d)
r=d["layers"][1];x,y=M.anchor(r)
ok(M.effective(d)[0]["collision"].getpixel((x,y))==255,"initial collision")
def stroke(doc,role,mode,points,radius=3):
    return P.stroke(doc,dict(role=role,mode=mode,points=points,radius=radius))
edited=stroke(d,"collision","erase",[[x,y]])
ok(M.effective(edited)[0]["collision"].getpixel((x,y))==0 and M.effective(edited)[0]["walkable"].getpixel((x,y))==255,"erase restores raw walk coverage")
rebuilt,_=M.generate(edited)
ok(M.effective(rebuilt)[0]["collision"].getpixel((x,y))==0,"override survives rebuild")
added=stroke(rebuilt,"collision","add",[[10,10],[20,10]])
ok(M.effective(added)[0]["collision"].getpixel((15,10))==255,"continuous brush")
reset=stroke(added,"collision","reset",[[x,y]])
ok(M.effective(reset)[0]["collision"].getpixel((x,y))==255,"reset restores suggestion")
ok(W.validate(json.loads(json.dumps(reset)))[0]==reset,"correction roundtrip")
scaled,key=P.transform(d,"rock",{"action":"scale","percent":150})
ok(M.anchor(scaled["layers"][1])==(x,y) and W.image(scaled["layers"][1]["image"]).size==(30,30),"scale preserves contact")
mir,_=P.transform(d,"rock",{"action":"mirror"})
ok(M.anchor(mir["layers"][1])==(x,y),"mirror preserves anchor")
dup,key=P.transform(d,"rock",{"action":"duplicate"})
ok(len(dup["layers"])==len(d["layers"])+1 and key!="rock","duplicate independent")
replacement=data_url(Image.new("RGBA",(32,32),(200,20,30,255)))
patched=P.replace(d,"ground",replacement,[10,20,20,20],0)
a=W.image(patched["layers"][0]["image"])
ok(a.getpixel((15,25))==(200,20,30,255),"patch applied")
ok(a.crop((0,0,100,20)).tobytes()==ground.crop((0,0,100,20)).tobytes() and a.getpixel((30,25))==ground.getpixel((30,25)),"outside patch unchanged")
ok(patched["layers"][1:]==d["layers"][1:],"all other layers unchanged")
ok(M.inspect(patched)["stale"],"patch flags stale masks")
try:P.replace(d,"rock",replacement,[40,40,10,10]);ok(False,"partial prop rejected")
except ValueError:ok(True,"partial prop rejected")
locked={**d,"layers":[{**d["layers"][0],"locked":True},*d["layers"][1:]]}
try:P.replace(locked,"ground",replacement);ok(False,"locked layer rejected")
except ValueError:ok(True,"locked layer rejected")
done("test_world_polish")
