from _common import *
from engine import instruction_edit as ie, main, generate
from unittest.mock import patch
from fastapi import HTTPException

ok(ie.identity_locks()==list(ie.DEFAULT_LOCKS),"default identity locks")
ok(ie.identity_locks([])==[],"explicitly unlocked")
prompt=ie.edit_prompt("replace armor with mage outfit","green",["face","pose"])
ok("facial features" in prompt and "limb placement" in prompt,"selected guidance included")
ok("hairstyle" not in prompt and "footwear" not in prompt,"unselected guidance omitted")
ok("Preserve" not in ie.edit_prompt("change hairstyle","white",[]),"no implicit lock on unlocked features")
for bad in (["unknown"],["face","face"],"face",[1]):
    try:
        ie.identity_locks(bad)
        ok(False,"invalid locks")
    except ValueError:
        ok(True,"invalid locks rejected")
source=Image.new("RGBA",(64,96),(180,90,50,255))
model={"supported":True,"backend":"qwen","family":"qwen"}
def fake_gen(*args,**kwargs):
    prompt=args[4]
    ok("change hairstyle" in prompt,"requested change reaches model")
    guidance=prompt.split(" Preserve ",1)[1].split(" Keep one character",1)[0]
    ok("facial features" in guidance and "hairstyle" not in guidance,"selected locks reach model")
    ok(prompt==ie.edit_prompt("change hairstyle","green",["face"]),"forwarded prompt matches selected guidance")
    return [(args[11],args[8])]
with patch.object(generate,"generate",side_effect=fake_gen):
    out,info=ie.edit(source,model,"unused","unused","change hairstyle",size=640,locks=["face"])
    ok(info["identity_locks"]==["face"] and info["identity_lock_type"]=="prompt_guidance","honest lock metadata")
with patch.object(main,"_paths",return_value=("unused","unused")),patch.object(main.mf,"describe",return_value=model),patch.object(generate,"generate",side_effect=fake_gen):
    result=main.character_instruction_edit(main.InstructionEditParams(image=main.b64(source),checkpoint="unused",instruction="change hairstyle",locks=["face"],size=640))
    ok(result["info"]["identity_locks"]==["face"],"API forwards locks")
done("test_instruction_identity")
