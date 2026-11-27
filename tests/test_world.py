"""CPU raster world, gameplay mask separation and project persistence."""
from _common import *
from engine import world as W, projects
from PIL import Image
import copy, json

red=data_url(Image.new("RGBA",(64,64),(255,0,0,255)))
blue=data_url(Image.new("RGBA",(16,16),(0,0,255,255)))
mask=Image.new("RGBA",(64,64));mask.putpixel((4,4),(255,255,255,255))
doc={**W.default(),"width":64,"height":64,"spawn":[20,30],"layers":[
    dict(id="g",role="ground",image=red),
    dict(id="o",role="objects",image=blue,x=8,y=9),
    dict(id="c",role="collision",image=data_url(mask))]}
d,_=W.validate(doc)
ok(W.validate(json.loads(json.dumps(d)))[0]==d,"normalized world roundtrip")
out,_=W.render(d)
ok(out.getpixel((8,9))==(0,0,255,255) and out.getpixel((4,4))==(255,0,0,255),"layer order and masks excluded")
overlay,_=W.render(d,True)
ok(overlay.getpixel((4,4))!=out.getpixel((4,4)) and overlay.getpixel((3,4))==out.getpixel((3,4)),"alpha mask overlay isolated")
changed=copy.deepcopy(d);changed["layers"][1].update(x=-8,y=-8,opacity=50)
im,_=W.render(changed)
ok(im.getpixel((0,0))==(127,0,128,255),"negative clipping and opacity")
changed["layers"][1]["visible"]=False
ok(W.render(changed)[0].tobytes()==W.render({**d,"layers":[d["layers"][0]]})[0].tobytes(),"hidden layer")
for bad in ({**d,"width":3072,"height":3072},{**d,"spawn":[64,0]},{**d,"layers":[d["layers"][0]]*2},{**d,"layers":[{**d["layers"][2],"x":1}]},{**d,"layers":[{**d["layers"][1],"role":"walkable"}]},{**d,"layers":[{**d["layers"][0],"image":"bad"}]}):
    try:W.validate(bad);ok(False,"invalid world rejected")
    except ValueError:ok(True,"invalid world rejected")
root=tmpdir()
projects.save(root,"World",{"world":d,"tab":18})
ok(projects.load(root,"World")["world"]==d,"world survives project save/load")
projects.restore_bundle(root,"Copy",projects.bundle(root,"World"))
ok(projects.load(root,"Copy")["world"]==d,"world survives portable project bundle")
projects.save(root,"Legacy",{})
ok(projects.load(root,"Legacy").get("world") is None,"legacy project compatible")
done("test_world")
