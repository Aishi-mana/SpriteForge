from _common import *
from engine import instruction_edit as ie, main, generate
from unittest.mock import patch
from PIL import ImageDraw

source=Image.new("RGBA",(64,96))
ImageDraw.Draw(source).rectangle((10,10,53,85),fill=(180,90,50,255))
mask=Image.new("L",source.size,0)
ImageDraw.Draw(mask).rectangle((20,35,40,70),fill=255)
uri=main.b64(mask)
models=[{"supported":True,"backend":"qwen"},{"supported":True,"backend":"neta"},{"supported":True,"family":"sdxl"}]
def blank(*args,**kwargs):
    return Image.new("RGB",(640,640),(0,255,0))
for model in models:
    with patch.object(generate,"generate",side_effect=lambda *a,**k:[(blank(),0)]),patch.object(generate,"inpaint",side_effect=blank):
        out,info=ie.run_edit(source,model,"unused","unused","remove equipment",size=640,mask=uri,pixel=True,locks=["face"])
        ok(out.getpixel((30,50))[3]==0,"regional removal can erase editable content")
        ok(all(out.getpixel((x,y))==source.getpixel((x,y)) for y in range(96) for x in range(64) if not mask.getpixel((x,y))),"protected pixels unchanged")
        ok(info["elapsed_seconds"]>=0 and info["identity_locks"]==["face"],"timing and identity metadata")
        try:
            ie.run_edit(source,model,"unused","unused","remove all",size=640)
            ok(False,"empty whole image")
        except ValueError:
            ok(True,"empty whole image rejected")
ok(not ie.EDIT_LOCK.locked(),"lock released after errors")
with patch.object(generate,"generate",return_value=[(Image.new("RGB",(1025,640)),0)]):
    try:
        ie.run_edit(source,models[0],"unused","unused","edit",size=640)
        ok(False,"oversized result")
    except ValueError:
        ok(True,"oversized result rejected")
ie.EDIT_LOCK.acquire()
try:
    try:
        ie.run_edit(source,models[0],"unused","unused","edit",size=640)
        ok(False,"overlapping edit")
    except RuntimeError:
        ok(True,"overlapping edit rejected")
finally:
    ie.EDIT_LOCK.release()
with patch.object(generate,"generate",side_effect=RuntimeError("CUDA out of memory")),patch.object(main,"_paths",return_value=("unused","unused")),patch.object(main.mf,"describe",return_value=models[0]):
    try:
        main.character_instruction_edit(main.InstructionEditParams(image=main.b64(source),checkpoint="unused",instruction="edit",size=640))
        ok(False,"OOM")
    except main.HTTPException as e:
        ok(e.status_code==500 and "640" in e.detail,"OOM recovery hint")
ok(not ie.EDIT_LOCK.locked(),"lock released after OOM")
done("test_instruction_integration")
