from _common import *
from engine import full_frame_extract as E, full_frame as F, world
from PIL import Image
a=Image.new("RGB",(32,32),(0,255,0));a.paste((255,0,0),(4,6,12,22))
b=Image.new("RGB",(32,32),(0,255,0));b.paste((255,0,0),(8,6,16,22))
q=dict(background="green",tolerance=20,softness=20,trim=True,fps=12)
d=E.assemble([a,b],q,F.default())
ok((d["width"],d["height"])==(12,16) and d["pivot"]==[6,15],"shared union crop and pivot")
ok(world.image(d["frames"][0]).getpixel((11,0))[3]==0,"background transparency")
ok(world.image(d["frames"][1]).getpixel((0,0))[3]==0,"relative motion retained")
ok(world.image(d["frames"][0]).getpixel((0,0))[3]==255,"subject preserved")
ok(F.validate(d)==d,"validated frame sequence")
for bad in ({"fps":0},{"background":"bad"},{"softness":101}):
    try:E.settings({**q,**bad});ok(False,"invalid extraction")
    except ValueError:ok(True,"invalid extraction rejected")
try:E.assemble([Image.new("RGB",(32,32),(0,255,0))],q,F.default());ok(False,"empty subject")
except ValueError:ok(True,"empty subject rejected")
done("test_full_frame_extract")
