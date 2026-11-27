"""Playtest snapshots enforce effective masks, depth ordering and actor budgets."""
from _common import *
from engine import world as W, world_masks as M, world_polish as P, world_playtest as T
from PIL import Image, ImageDraw
im=Image.new("RGBA",(64,64),"green")
prop=Image.new("RGBA",(8,16),"brown")
collision=Image.new("RGBA",(64,64));ImageDraw.Draw(collision).rectangle((30,0,30,63),fill="white")
walk=Image.new("RGBA",(64,64));ImageDraw.Draw(walk).rectangle((4,4,59,59),fill="white")
doc={**W.default(),"width":64,"height":64,"spawn":[12,32],"layers":[
 dict(id="ground",role="ground",image=data_url(im)),dict(id="tree",role="foliage",image=data_url(prop),x=18,y=20),
 dict(id="front",role="foreground",image=data_url(prop),x=40,y=40),
 dict(id="col",role="collision",image=data_url(collision),visible=False,opacity=0),
 dict(id="walk",role="walkable",image=data_url(walk))]}
clip=dict(name="idle",frames=[data_url(prop)],fps=4,pivot=[4,16],pixel=True,loop=True)
out=T.prepare(doc,{"idle":clip},{"radius":2})
ok(out["has_walkable"] and out["spawn"]==[12,32],"valid playtest")
ok([l["mode"] for l in out["layers"]]==["ground","sorted","foreground"],"depth metadata")
m,has=M.effective(doc)
ok(T.clear(m,has,[12,32],2) and not T.clear(m,has,[28,32],2),"radius and hidden collision")
ok(not T.clear(m,has,[5,5],2),"walkable boundary")
edited=P.stroke(doc,dict(role="collision",mode="erase",radius=5,points=[[30,32]]))
ok(T.clear(*M.effective(edited),[30,32],2),"manual erase respected")
for d in ({**doc,"spawn":[30,32]},{**doc,"spawn":[0,0]}):
    try:T.prepare(d,{"idle":clip},{"radius":2});ok(False,"invalid spawn")
    except ValueError:ok(True,"invalid spawn rejected")
generated,_=M.generate(doc,{"walk_source":"ground"})
generated["layers"][1]["x"]+=1
try:T.prepare(generated,{"idle":clip});ok(False,"stale masks")
except ValueError:ok(True,"stale masks rejected")
ok(T.prepare(generated,{"idle":clip},{"allow_stale":True,"radius":0})["status"]["stale"],"explicit stale override")
saved=T.saved_clips({"results":{"walk":{**clip,"pivot":[4.2,15.8],"accept":[False],"raw":[data_url(prop)]}},"images":{"charactersprite":data_url(prop)}})
ok(saved["walk"]["pivot"]==[4,16] and "idle" in saved,"saved standard clip and static fallback")
done("test_world_playtest")
