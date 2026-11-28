"""Independent actor sheets and timeline export regressions."""
from _common import *
from engine import paired_export as E
import io,json,zipfile
def actor(key,color,z):
    im=Image.new("RGBA",(8,8),color)
    return dict(id="actor_"+key,clip=dict(name=key,frames=[data_url(im)],pivot=[4,7],fps=4,pixel=True,loop=True),x=12,y=14,z=z)
a=actor("A",(255,0,0,255),0)
b=actor("B",(0,0,255,255),1)
a["frame_overrides"]=[dict(frame=1,x=16,y=18,z=2)]
b["start"]=1
scene=dict(version=1,name="hug",width=32,height=32,count=4,fps=4,actors=[a,b])
body=dict(scene=scene,contact=dict(label="Hands",anchors=dict(A=[1,-2],B=[-1,-2])),stages=dict(enabled=True,preset="hug",loopStart=1,exitStart=3))
with zipfile.ZipFile(io.BytesIO(E.export(body))) as z:
    m=json.loads(z.read("interaction.json"))
    ok(len(m["actors"])==2 and m["stages"]["loop"]==[1,3],"independent actors and stage range")
    ok(m["timeline"][0]["actors"]["actor_B"]["visible"] is False,"delayed entry")
    ok(m["timeline"][1]["actors"]["actor_A"]["position"]==[16,18] and m["timeline"][1]["actors"]["actor_A"]["depth"]==2,"override exported")
    for key,color in [("A",(255,0,0,255)),("B",(0,0,255,255))]:
        atlas=json.loads(z.read("character_"+key+".json"))
        im=Image.open(io.BytesIO(z.read(atlas["pages"][0])))
        ok(im.getpixel((0,0))==color and atlas["pivot"]==[4,7],"independent source artwork and pivot")
with zipfile.ZipFile(io.BytesIO(E.export({**body,"format":"webp"}))) as z:
    ok("character_A.webp" in z.namelist(),"WebP export")
try:E.export({**body,"stages":dict(enabled=True,loopStart=3,exitStart=3)});ok(False,"invalid stage")
except ValueError:ok(True,"invalid stage rejected")
done("test_paired_export")
