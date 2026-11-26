"""CPU-only synchronized independent layer sheet export."""
from _common import *
from engine import modular as M, layer_export as E
from PIL import Image
body,joints,_=synth_sprite()
w,h=body.size
hat=Image.new("RGBA",(w,h));hat.paste((251,2,199,255),(16,0,24,6))
cape=Image.new("RGBA",(w,h));cape.paste((10,230,40,255),(4,15,11,46))
recipe={"width":w,"height":h,"pixel":True,"layers":[
 {"name":"Cape","category":"other","attachment":"torso","image":M.png_uri(cape),"motion":{"mode":"spring"}},
 {"name":"Base","category":"body","image":M.png_uri(body)},
 {"name":"Hat","category":"accessory","attachment":"head","image":M.png_uri(hat),"visible":False}]}
root=tmpdir()
d=E.export(recipe,"walk",4,10,"right","r","r",1,0,0,"test",root,columns=2,individual=True)
p=Path(d["dir"]);m=json.loads((p/"manifest.json").read_text())
ok(len(m["layers"])==3 and m["frame_count"]==4,"hidden alternative exported with same frame count")
ok(m["layers"][2]["visible"] is False,"default visibility recorded")
combined=Image.new("RGBA",tuple(d["sheet"]))
for l in m["layers"]:
    im=Image.open(p/l["sheet"]).convert("RGBA")
    ok(im.size==tuple(d["sheet"]),"matching sheet size")
    if l["visible"]:combined=Image.alpha_composite(combined,im)
    ok(len(list((p/l["frames_dir"]).glob("*.png")))==4,"individual frames")
ok(combined.tobytes()==Image.open(p/"assembled.png").convert("RGBA").tobytes(),"default assembly reconstructs exactly")
ok(Image.open(p/m["layers"][2]["sheet"]).getchannel("A").getbbox() is not None,"hidden alternative rendered")
ok(recipe["layers"][2]["visible"] is False,"source recipe unchanged")
d2=E.export(recipe,"idle",2,8,"right","r","r",1,0,0,"test",root,include_hidden=False)
ok(d2["layers"]==2 and d2["dir"]!=d["dir"],"visible-only export and unique folders")
done("test_layer_export")
