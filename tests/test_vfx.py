"""Procedural VFX determinism, layering, attachments, validation and persistence."""
from _common import *
from engine import vfx as V,scenes as S,projects
import copy
base={"id":"fx","kind":"magic_circle","radius":12,"x":32,"y":32,"start":0,"end":4,"seed":7}
scene={"name":"fx","width":64,"height":64,"count":5,"fps":10,"actors":[],"effects":[base]}
for kind in V.KINDS:
    p,_=S.validate({**scene,"effects":[{**base,"kind":kind}]})
    e=p["effects"][0];a,_=V.surface(e,2);b,_=V.surface(e,2)
    ok(a.tobytes()==b.tobytes() and a.getchannel("A").getbbox() is not None,kind+" deterministic and visible")
frames,meta=S.render(scene)
one,_=S.render(scene,2)
ok(one[0].tobytes()==frames[2].tobytes(),"single frame matches clip")
ok(frames[0].tobytes()!=frames[2].tobytes(),"animated circle")
actor={"id":"a","clip":{"name":"actor","fps":10,"pivot":[8,8],"frames":[data_url(Image.new("RGBA",(16,16),(255,0,0,255)))]},"x":16,"y":20,"end_x":44,"end_y":20}
attached={**base,"kind":"impact","x":0,"y":0,"radius":8,"actor":"a","z":1}
a,_=S.render({**scene,"actors":[actor],"effects":[attached]},0)
b,_=S.render({**scene,"actors":[actor],"effects":[{**attached,"z":-1}]},0)
ok(a[0].getpixel((16,20))!=b[0].getpixel((16,20)) and b[0].getpixel((16,20))==(255,0,0,255),"effect depth interleaved with actor")
q,_=S.validate({**scene,"actors":[actor],"effects":[attached]})
x,_=S.render({**scene,"actors":[{**actor,"visible":False}],"effects":[attached]},2)
ok(x[0].getbbox() is None,"attachment hidden with actor")
p,_=S.validate(scene)
root=tmpdir();projects.save(root,"FX",{"scene":scene})
ok(projects.load(root,"FX")["scene"]==p,"effect recipe persisted")
for bad in ([{**base,"actor":"missing"}],[{**base,"particles":97}],[base,base]):
    try:S.validate({**scene,"effects":bad});ok(False,"invalid effect")
    except ValueError:ok(True,"invalid effect rejected")
done("test_vfx")
