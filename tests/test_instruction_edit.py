from _common import *
from engine import instruction_edit as ie, main, generate
from unittest.mock import patch
from PIL import ImageDraw
from fastapi import HTTPException

source=Image.new("RGBA",(64,96))
ImageDraw.Draw(source).rectangle((10,10,53,85),fill=(180,90,50,255))
qwen={"supported":True,"backend":"qwen","family":"qwen"}
neta={"supported":True,"backend":"neta","family":"lumina2"}
sdxl={"supported":True,"family":"sdxl"}
ok(ie.capability(qwen)=="qwen_instruction","Qwen route")
ok(ie.capability(neta)=="neta_img2img","Neta route")
ok(ie.capability(sdxl)=="sdxl_inpaint","SDXL route")
ok(ie.capability({"supported":True,"family":"flux"}) is None,"unsupported model rejected")
ok(ie.capability({"supported":False,"backend":"qwen"}) is None,"unready model rejected")
ok(generate.build_prompt("add wings",kind="instruction_edit")=="add wings","instruction prompt not wrapped in costume template")

def fake_gen(*args,**kwargs):
    ok(kwargs["kind"]=="instruction_edit" and "mage outfit" in args[4],"native instruction forwarded")
    ok(args[11].size==(640,640),"native source canvas forwarded")
    return [(args[11],args[8])]

for model in (qwen,neta):
    with patch.object(generate,"generate",side_effect=fake_gen):
        out,info=ie.edit(source,model,"unused","unused","mage outfit",size=640,pixel=True)
        ok(out.size==source.size and out.getpixel((0,0))[3]==0,"preserved canvas and alpha")
        ok(info["strength_supported"]==(model is neta),"backend strength metadata")
def fake_paint(*args,**kwargs):
    ok(args[7].getextrema()==(255,255),"full canvas inpaint mask")
    ok(kwargs["kind"]=="instruction_edit","SDXL instruction route")
    return args[6]
with patch.object(generate,"inpaint",side_effect=fake_paint):
    out,info=ie.edit(source,sdxl,"unused","unused","mage outfit",size=640,keep_canvas=False)
    ok(out.size==(640,640),"expanded canvas option")
with patch.object(main,"_paths",return_value=("unused","unused")),patch.object(main.mf,"describe",return_value=qwen),patch.object(generate,"generate",side_effect=fake_gen):
    result=main.character_instruction_edit(main.InstructionEditParams(image=main.b64(source),checkpoint="unused",instruction="mage outfit",size=640))
    ok(result["info"]["backend"]=="qwen_instruction","endpoint route")
for opts in ({"size":2048},{"instruction":""},{"bg":"bad"},{"strength":1}):
    try:
        main.character_instruction_edit(main.InstructionEditParams(**{**dict(image=main.b64(source),checkpoint="unused",instruction="mage outfit"),**opts}))
        ok(False,"bad input")
    except HTTPException as e:
        ok(e.status_code==400,"bad input rejected")
done("test_instruction_edit")
