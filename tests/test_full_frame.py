"""Full-frame animation document and project roundtrip."""
from _common import *
from engine import full_frame as F, projects
from PIL import Image
import copy
frame=data_url(Image.new("RGBA",(32,48),(90,20,60,180)))
doc=F.validate({**F.default(),"width":32,"height":48,"pivot":[16,47],"reference":frame,"frames":[frame,frame],"fps":24})
ok(len(doc["frames"])==2 and doc["reference"]==frame,"full frame sequence")
ok(F.validate(doc)==doc,"stable validation")
for bad in ({"fps":0},{"pivot":[32,0]},{"width":31},{"frames":[frame]*121},{"frames":["invalid"]},{"loop":"true"},{"version":2}):
    try:F.validate({**doc,**bad});ok(False,"invalid animation")
    except ValueError:ok(True,"invalid animation rejected")
root=tmpdir()
projects.save(root,"FullFrames",{"full_frame":doc,"tab":20})
ok(projects.load(root,"FullFrames")["full_frame"]==doc,"project roundtrip")
projects.restore_bundle(root,"Restored",projects.bundle(root,"FullFrames"))
ok(projects.load(root,"Restored")["full_frame"]==doc,"archive roundtrip")
projects.save(root,"Legacy",{})
ok(projects.load(root,"Legacy").get("full_frame") is None,"legacy project")
done("test_full_frame")
