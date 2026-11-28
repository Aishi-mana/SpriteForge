"""CPU selective paired replacement regression."""
from _common import *
from engine import paired_replace as R, scenes
def clip(color):
    return dict(name="actor",frames=[data_url(Image.new("RGBA",(8,8),color))]*2,pivot=[4,8],fps=4,pixel=True,loop=True)
a=dict(id="actor_A",clip=clip((255,0,0,255)),x=12,y=14,z=0)
b=dict(id="actor_B",clip=clip((0,0,255,255)),x=18,y=14,z=1,offset=1,speed=50,frame_overrides=[dict(frame=1,x=20,y=16,z=2)])
scene=dict(version=1,name="pair",width=32,height=32,count=4,fps=4,actors=[a,b])
original=scenes.validate(scene)[0]
doc=R.prepare(dict(scene=scene,actor="actor_B"))
ok(doc["pivot"]==[4,7] and doc["frames"]==b["clip"]["frames"],"prepare motion document with bounded pivot")
frames=clip((0,255,0,255))["frames"]
result=R.replace(dict(scene=scene,actor="actor_B",frames=frames))
ok(result["actors"][0]==original["actors"][0],"partner unchanged")
expected=original["actors"][1].copy();expected["clip"]={**expected["clip"],"frames":frames}
ok(result["actors"][1]==expected,"target timing and transforms retained")
ok(result["count"]==original["count"] and result["fps"]==original["fps"],"scene timeline retained")
ok(b["clip"]["frames"]!=frames,"input unmodified")
try:R.replace(dict(scene=scene,actor="actor_B",frames=frames[:1]));ok(False,"reject changed frame count")
except ValueError:ok(True,"reject changed frame count")
try:R.replace(dict(scene=scene,actor="actor_B",frames=[data_url(Image.new("RGBA",(9,8),(255,0,0,255)))]*2));ok(False,"reject changed canvas")
except ValueError:ok(True,"reject changed canvas")
done("test_paired_replace")
