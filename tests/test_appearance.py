"""GPU-free appearance prompt, variation and project persistence checks."""
from _common import *
from engine import character as C, projects
import io, base64
p,locks=C.variation_prompt("silver hair","outfit","blue jacket",list(C.FEATURES))
ok("outfit" not in locks and "face" in locks and "hair" in locks,"target temporarily unlocked")
ok("blue jacket" in p and C.FEATURES["face"] in p and C.FEATURES["outfit"] not in p,"target change and retained features explicit")
p,locks=C.variation_prompt("","hair","short brown hair",["hair","eyes","style"])
ok(locks==["eyes","style"] and "short brown hair" in p,"hair change retains eyes and style")
ok(C.FEATURES["hair"] not in C.view_prompt("E","",["face"]),"direction prompt honors selected locks")
ok(C.IDENTITY in C.view_prompt("E"),"legacy direction requests unchanged")
for bad in (["no_such_feature"],"face"):
    try:C.active_locks(bad);ok(False,"invalid locks")
    except ValueError:ok(True,"invalid locks rejected")
try:C.variation_prompt("","custom","new look",list(C.FEATURES));ok(False,"custom all locked")
except ValueError:ok(True,"custom all locked rejected")
a=Image.new("RGBA",(40,64));a.paste((80,120,180,255),(8,4,32,60))
out,info=C.finish_variation(a,a,"anime",512)
ok(max(out.size)==512 and info["pipeline"]=="hd","HD variants keep full resolution")
def uri(im):
    b=io.BytesIO();im.save(b,"PNG");return "data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()
root=tmpdir();master=uri(a);candidate=uri(out)
projects.save(root,"Appearance",{"images":{"characterref":master,"charvariant":candidate},"directions":{"variantInfo":{"target":"hair"}}})
loaded=projects.load(root,"Appearance")
ok(C.decode_reference(loaded["images"]["characterref"]).tobytes()==a.tobytes(),"master preserved")
ok(C.decode_reference(loaded["images"]["charvariant"]).size==out.size and loaded["directions"]["variantInfo"]["target"]=="hair","candidate and metadata restored separately")
done("test_appearance")
