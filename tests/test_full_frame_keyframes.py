from _common import *
from engine import full_frame as F, full_frame_consistency as C, full_frame_interpolation as I
from PIL import Image
a=data_url(Image.new("RGBA",(16,16),(100,20,30,255)))
b=data_url(Image.new("RGBA",(16,16),(180,20,30,255)))
d=F.validate({**F.default(),"width":16,"height":16,"pivot":[8,15],"frames":[a,b,a],"keyframes":[1],"locked_frames":[1]})
ok(C.correct(d,{"color":100})["frames"][1]==b,"locked frame exact")
out=I.interpolate(d,{"factor":2})
ok(out["keyframes"]==[2] and out["locked_frames"]==[2] and out["frames"][2]==b,"interpolation remaps locks")
for q in ({"keyframes":[3]},{"locked_frames":[0]},{"keyframes":[1,1]}):
    try:F.validate({**d,**q});ok(False,"invalid marker")
    except ValueError:ok(True,"invalid marker rejected")
done("test_full_frame_keyframes")
