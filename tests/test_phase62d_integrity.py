from _common import *
from engine import projects as P, full_frame as F, full_frame_directions as D, full_frame_interpolation as I, full_frame_export as E
from PIL import Image
import io,json,zipfile
a=data_url(Image.new("RGBA",(16,16),(100,20,30,255)))
b=data_url(Image.new("RGBA",(16,16),(180,20,30,255)))
with tmpdir() as root:
    P.save(root,"integrity",{"images":{"ref":a}})
    sid=P.add_sprite(root,"integrity",a)
    before=P.list_sprites(root,"integrity")[0]["data"]
    try:P.replace_sprite(root,"integrity",sid,"invalid");ok(False,"bad replacement rejected")
    except ValueError:ok(P.list_sprites(root,"integrity")[0]["data"]==before,"bad replacement preserves original")
    P.replace_sprite(root,"integrity",sid,b)
    ok(P.list_sprites(root,"integrity")[0]["id"]==sid and P.list_sprites(root,"integrity")[0]["data"]!=before,"replacement retains ID")
    try:P.save(root,"integrity",{"images":{"ref":b},"tileset":{"tiles":[{"image":"invalid"}]}});ok(False,"bad save rejected")
    except ValueError:ok(P.load(root,"integrity")["images"]["ref"]==before,"invalid secondary asset leaves reference unchanged")
d=F.validate({**F.default(),"width":16,"height":16,"pivot":[8,15],"frames":[a,b],"keyframes":[1],"locked_frames":[1]})
v=D.switch(d,"E");v=F.validate({**v,"frames":[a,b]})
try:I.interpolate(v,{"factor":2});ok(False,"shared FPS protected")
except ValueError:ok(True,"shared FPS protected")
with zipfile.ZipFile(io.BytesIO(E.export(v))) as z:
    ok(json.loads(z.read("animation.json"))["directions"]["S"]["locked_frames"]==[1],"export locks retained")
done("test_phase62d_integrity")
