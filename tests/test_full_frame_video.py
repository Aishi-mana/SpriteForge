from _common import *
from engine import full_frame_video as V
from PIL import Image
from pathlib import Path
import json
root=Path(tmpdir());p=root/"video_models"/"LTX";p.mkdir(parents=True)
(p/"model_index.json").write_text(json.dumps({"_class_name":"LTXImageToVideoPipeline"}))
ok(V.discover(root)==[{"name":"LTX","backend":"ltx"}],"local video discovery")
ref=data_url(Image.new("RGBA",(32,48),(100,50,20,255)))
body=dict(model="LTX",prompt="walk",reference=ref,width=256,height=256,frames=9,seed=42)
def fake(path,im,q):
    ok(path==p and im.size==(256,256) and im.mode=="RGB" and q["seed"]==42,"runner routing and reference")
    return b"fake mp4"
ok(V.generate(root,body,fake)==b"fake mp4","video result")
for change in ({"model":"../LTX"},{"width":257},{"frames":10},{"seed":-2},{"reference":"invalid"},{"prompt":""}):
    try:V.generate(root,{**body,**change},fake);ok(False,"invalid video request")
    except ValueError:ok(True,"invalid video request rejected")
from engine import full_frame_guidance as G, full_frame as F
q=G.settings({"preset":"walk","background":"green","view":"side"})
ok("alternating steps" in G.prompt("",q) and "Fixed camera" in G.prompt("",q) and "Side view" in G.prompt("",q),"preset and camera prompt")
ok("Fixed camera" not in G.prompt("walk",{"camera":False}),"optional camera guidance")
ok(V.prepare_reference(ref,256,256,q).getpixel((0,0))==(0,255,0),"matching chroma reference background")
ok(F.validate({**F.default(),"guidance":q})["guidance"]==q,"guidance persistence")
for bad in ({"preset":"bad"},{"background":"bad"},{"margin":31},{"identity":"true"}):
    try:G.settings(bad);ok(False,"invalid guidance")
    except ValueError:ok(True,"invalid guidance rejected")
done("test_full_frame_video")
