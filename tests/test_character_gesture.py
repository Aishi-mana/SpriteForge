from _common import *
from engine import main
from fastapi import HTTPException
from unittest.mock import patch
base=dict(prompt="knight",checkpoint="unused",reference="test",framing="half",expression="happy",gesture="wave")
with patch.object(main,"framed_portrait",side_effect=lambda p:p):
    p=main.character_gesture(main.CharacterGestureParams(**base))
    ok("friendly wave" in p.prompt and "smiling" in p.prompt and p.reference=="test","gesture and expression conditioning")
for change in (dict(framing="face"),dict(gesture="bad"),dict(expression="bad"),dict(reference=None),dict(custom="x"*301)):
    try:
        main.character_gesture(main.CharacterGestureParams(**{**base,**change}))
        ok(False,"invalid gesture input")
    except HTTPException as e:
        ok(e.status_code==400,"invalid gesture input rejected")
done("test_character_gesture")
