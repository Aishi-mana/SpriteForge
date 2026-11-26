from _common import *
from engine import instruction_edit as ie, main, generate
from unittest.mock import patch
from PIL import ImageDraw

source=Image.new("RGBA",(64,96),(17,28,39,0))
ImageDraw.Draw(source).rectangle((10,10,53,85),fill=(180,90,50,200))
mask=Image.new("L",source.size,0)
ImageDraw.Draw(mask).rectangle((20,35,40,70),fill=255)
uri=main.b64(mask)
qwen={"supported":True,"backend":"qwen"}
neta={"supported":True,"backend":"neta"}
sdxl={"supported":True,"family":"sdxl"}
def verify(out):
    ok(out.size==source.size,"source dimensions preserved")
    ok(all(out.getpixel((x,y))==source.getpixel((x,y)) for y in range(source.height) for x in range(source.width) if not mask.getpixel((x,y))),"all protected RGBA pixels exact")
    ok(out.getpixel((30,50))==(30,40,180,255),"selected area changed")
def fake_gen(*args,**kwargs):
    return [(Image.new("RGB",(640,640),(30,40,180)),0)]
for model in (qwen,neta):
    with patch.object(generate,"generate",side_effect=fake_gen):
        out,info=ie.edit(source,model,"unused","unused","change armor",size=640,mask=uri,remove_bg=False)
        verify(out)
        ok(info["regional"] and not info["native_mask"],"composite-only backend metadata")
        ok(info["protected_pixels"]==64*96-21*36,"protected pixel count")
def fake_paint(*args,**kwargs):
    ok(args[7].getextrema()==(0,255),"native SDXL binary mask")
    ok(args[7].getpixel((0,0))==0 and args[7].getpixel((320,320))==255,"native mask mapped into fitted canvas")
    return Image.new("RGB",(640,640),(30,40,180))
with patch.object(generate,"inpaint",side_effect=fake_paint):
    out,info=ie.edit(source,sdxl,"unused","unused","change armor",size=640,mask=uri,remove_bg=False)
    verify(out)
    ok(info["native_mask"],"SDXL native mask metadata")
for bad in ("bad",main.b64(Image.new("L",(2,2),255)),main.b64(Image.new("L",source.size,0))):
    try:
        ie.decode_mask(bad,source.size)
        ok(False,"bad mask")
    except ValueError:
        ok(True,"bad mask rejected")
try:
    ie.edit(source,qwen,"unused","unused","change armor",size=640,mask=uri,keep_canvas=False)
    ok(False,"expanded masked canvas")
except ValueError:
    ok(True,"expanded masked canvas rejected")
done("test_instruction_mask")
