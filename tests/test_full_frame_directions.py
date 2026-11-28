from _common import *
from engine import full_frame as F, full_frame_directions as D
from PIL import Image
a=data_url(Image.new("RGBA",(16,16),(100,20,30,255)))
b=data_url(Image.new("RGBA",(16,16),(180,20,30,255)))
d=F.validate({**F.default(),"width":16,"height":16,"pivot":[8,15],"frames":[a,b,a],"keyframes":[1],"locked_frames":[1]})
e=D.switch(d,"E")
ok(e["frames"]==[] and e["directions"]["S"]["frames"]==[a,b,a],"independent directional slot")
ok(D.switch(e,"S")["locked_frames"]==[1],"direction lock roundtrip")
ok(D.seam(d)["difference"]==0,"matching loop seam")
p=D.loop_edit(d,"pingpong")
ok(p["frames"]==[a,b,a,b] and p["locked_frames"]==[1],"pingpong preserves originals")
p=D.loop_edit(d,"bridge",2)
ok(len(p["frames"])==5 and p["frames"][:3]==d["frames"],"bridge preserves originals")
try:D.switch({**d,"direction_mode":4},"NE");ok(False,"invalid diagonal")
except ValueError:ok(True,"four direction restriction")
done("test_full_frame_directions")
