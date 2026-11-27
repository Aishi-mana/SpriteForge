"""Mask suggestions, manual preservation, stale detection and depth hints."""
from _common import *
from engine import world as W, world_masks as M
from PIL import Image, ImageDraw
import copy,json
def png(size,paint):
    im=Image.new("RGBA",size);paint(ImageDraw.Draw(im));return data_url(im)
trail=png((100,100),lambda d:d.rectangle((30,0,70,99),fill="white"))
tree=png((40,60),lambda d:(d.ellipse((0,0,39,35),fill="green"),d.rectangle((18,30,21,59),fill="brown")))
rock=png((20,12),lambda d:d.ellipse((0,0,19,11),fill="gray"))
manual=png((100,100),lambda d:d.rectangle((49,80,51,82),fill="white"))
doc={**W.default(),"width":100,"height":100,"spawn":[50,90],"layers":[
 dict(id="path",role="ground_detail",image=trail),dict(id="tree",role="foliage",image=tree,x=5,y=5),
 dict(id="rock",role="objects",image=rock,x=45,y=40),
 dict(id="hand",role="collision",image=manual,visible=False,opacity=0,locked=True)]}
d,_=W.validate(doc);t=d["layers"][1];x,y=M.anchor(t)
ok(t["depth"]["footprint"][0]<5 and y==64,"trunk footprint not canopy")
out,status=M.generate(d)
ok(len(out["layers"])==7 and out["layers"][3]==d["layers"][3],"manual mask preserved")
ok(status["spawn_walkable"] and not status["stale"],"spawn and freshness")
mask,has=M.effective(out)
ok(has and mask["collision"].getpixel((x,y))==255 and mask["collision"].getpixel((25,20))==0,"trunk collision separate from canopy")
ok(mask["occlusion"].getpixel((25,20))==255 and mask["occlusion"].getpixel((x,y))==0,"canopy occlusion")
ok(mask["collision"].getpixel((50,81))==255 and mask["walkable"].getpixel((50,81))==0,"hidden manual collision still wins")
ok(mask["walkable"].getpixel((5,90))==0 and mask["walkable"].getpixel((50,90))==255,"path coverage")
ok(W.render(d)[0].tobytes()==W.render(out)[0].tobytes(),"no mask leakage into art")
ok(W.validate(json.loads(json.dumps(out)))[0]==out,"portable mask metadata")
changed=copy.deepcopy(out);changed["layers"][1]["x"]+=10
ok(M.inspect(changed)["stale"],"moving prop marks suggestions stale")
rebuilt,st=M.generate(changed)
ok(not st["stale"] and len(rebuilt["layers"])==7,"rebuild only generated masks")
newmask,_=M.effective(rebuilt)
ok(newmask["collision"].getpixel((x,y))==0 and newmask["collision"].getpixel((x+10,y))==255,"updated footprint")
blocked=copy.deepcopy(out);blocked["spawn"]=[50,81]
ok(M.inspect(blocked)["spawn_blocked"] and not M.inspect(blocked)["spawn_walkable"],"spawn warning")
locked=copy.deepcopy(out);locked["layers"][-1]["locked"]=True
try:M.generate(locked);ok(False,"locked generated mask")
except ValueError:ok(True,"locked mask protected")
ok(M.depth_order(d["layers"][0])<M.depth_order(d["layers"][1]),"ground before depth sorted props")
try:M.generate({**d,"layers":[d["layers"][1]]});ok(False,"missing walkable source")
except ValueError:ok(True,"missing source rejected")
done("test_world_masks")
