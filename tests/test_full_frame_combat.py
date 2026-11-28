from _common import *
from engine import full_frame as F, full_frame_directions as D, full_frame_interpolation as I, full_frame_guidance as G
from PIL import Image
a=data_url(Image.new("RGBA",(16,16),(100,20,30,255)))
d=F.validate({**F.default(),"width":16,"height":16,"pivot":[8,15],"frames":[a,a],"combat":[{"frame":1,"phase":"active","event":"impact","hitbox":[2,3,4,5],"anchor":[8,4],"root":[3,-2]}]})
ok(d["combat"][0]["hitbox"]==[2,3,4,5],"combat metadata")
ok(D.switch(D.switch(d,"E"),"S")["combat"]==d["combat"],"direction metadata roundtrip")
ok(I.interpolate(d,{"factor":2})["combat"][0]["frame"]==2,"interpolation event remap")
ok("windup" in G.prompt("",{"preset":"slash"}),"combat prompt")
for bad in ({"frame":2},{"hitbox":[15,0,2,1]},{"event":"bad"},{"anchor":[16,0]}):
    try:F.validate({**d,"combat":[{**d["combat"][0],**bad}]});ok(False,"invalid metadata")
    except ValueError:ok(True,"invalid metadata rejected")
done("test_full_frame_combat")
