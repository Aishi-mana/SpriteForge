from _common import *
from engine import full_frame as F, full_frame_export as E, full_frame_directions as D
from PIL import Image
import io,json,zipfile
a=data_url(Image.new("RGBA",(16,16),(100,20,30,255)))
b=data_url(Image.new("RGBA",(16,16),(180,20,30,255)))
d=F.validate({**F.default(),"width":16,"height":16,"pivot":[8,15],"frames":[a,b],"combat":[{"frame":1,"event":"impact"}]})
e=D.switch(d,"E")
e=F.validate({**e,"frames":[b]})
for kind in ("atlas","png","webp"):
    with zipfile.ZipFile(io.BytesIO(E.export(e,kind))) as z:
        manifest=json.loads(z.read("animation.json"))
        ok(set(manifest["directions"])=={"S","E"},"direction export "+kind)
        ok(manifest["directions"]["S"]["combat"][0]["event"]=="impact","event export "+kind)
        ok(manifest["pivot"]==[8,15],"pivot export "+kind)
        for clip in manifest["directions"].values():
            ok(all(v["file"] in z.namelist() for v in clip["frames"]),"assets exist "+kind)
c=E.world_clip({"directions":E.clips(e),"active":"E"},[0,0])
ok(c["active"]=="E" and len(c["directions"]["S"]["frames"])==2,"world directional clip")
ok(c["directions"]["S"]["combat"][0]["event"]=="impact","world event data")
done("test_full_frame_export")
