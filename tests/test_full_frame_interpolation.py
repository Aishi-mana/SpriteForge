from _common import *
from engine import full_frame_interpolation as I, full_frame as F, world
from PIL import Image
import numpy as np
def sprite(x):
    im=Image.new("RGBA",(32,32));im.paste((200,40,20,255),(x,8,x+6,20));return data_url(im)
a,b=sprite(4),sprite(12)
d=F.validate({**F.default(),"width":32,"height":32,"pivot":[16,31],"frames":[a,b],"fps":12})
out=I.interpolate(d,{"mode":"motion","factor":2})
ok(len(out["frames"])==4 and out["fps"]==24,"loop duration preserved")
ok(out["frames"][0]==a and out["frames"][2]==b,"original frames exact")
ok(world.image(out["frames"][1]).getpixel((9,10))==(200,40,20,255),"translated midpoint")
ok(world.image(out["frames"][1]).getpixel((4,10))[3]==0,"no endpoint ghost on pure translation")
non=I.interpolate({**d,"loop":False},{"factor":2})
ok(len(non["frames"])==4 and non["frames"][-1]==b,"nonloop duration with terminal hold")
slow=I.interpolate({**d,"loop":False},{"factor":2,"preserve_duration":False})
ok(len(slow["frames"])==3 and slow["fps"]==12,"slow motion")
hold=I.interpolate(d,{"mode":"hold"})
ok(hold["frames"]==[a,b,b,a],"nearest frame preservation")
x=np.array([[[255,0,0,255]]],dtype=np.uint8);y=np.array([[[0,255,0,0]]],dtype=np.uint8)
ok(tuple(I.blend(x,y,.5)[0,0])==(255,0,0,128),"premultiplied alpha avoids transparent color bleed")
for bad in ({"factor":5},{"mode":"bad"},{"strength":101}):
    try:I.interpolate(d,bad);ok(False,"invalid interpolation")
    except ValueError:ok(True,"invalid interpolation rejected")
try:I.interpolate({**d,"fps":40},{"factor":2});ok(False,"FPS budget")
except ValueError:ok(True,"FPS budget enforced")
# Isolate interpolation decoding from the existing validator's own decoding.
from unittest.mock import patch
with patch.object(F,"validate",side_effect=lambda value:value),patch.object(world,"image",wraps=world.image) as decode:
    I.interpolate(d,{"mode":"hold","factor":2})
    ok(decode.call_count==0,"hold mode avoids decoding artwork")
with patch.object(F,"validate",side_effect=lambda value:value),patch.object(world,"image",wraps=world.image) as decode:
    I.interpolate(d,{"mode":"motion","factor":2})
    ok(decode.call_count==3,"rolling pair reuses next frame and decodes loop endpoint")
done("test_full_frame_interpolation")
