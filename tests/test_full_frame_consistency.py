from _common import *
from engine import full_frame_consistency as C, full_frame as F, world
from PIL import Image
def sprite(x,color):
    im=Image.new("RGBA",(32,32));im.paste(color,(x,8,x+8,24));return data_url(im)
a=sprite(8,(100,80,60,255));b=sprite(14,(140,80,60,255))
d=F.validate({**F.default(),"width":32,"height":32,"pivot":[16,31],"frames":[a,b,a]})
ok(C.inspect(d)[1]["flag"],"local outlier detected")
ok(C.correct(d,{})==d,"zero correction preserves exact data")
out=C.correct(d,{"color":100,"position":100,"max_shift":4})
ok(C.inspect(out)[1]["position"]<C.inspect(d)[1]["position"],"bounded position correction")
ok(C.inspect(out)[1]["color"]<C.inspect(d)[1]["color"],"bounded color correction")
ok(out["frames"][0]==a and d["frames"][1]==b,"original and stable neighbor unchanged")
for bad in ({"color":101},{"max_shift":17},{"background":"bad"}):
    try:C.settings(bad);ok(False,"invalid consistency")
    except ValueError:ok(True,"invalid consistency rejected")
done("test_full_frame_consistency")
