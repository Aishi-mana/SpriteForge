"""CPU-only prompt routing, fitting and non-destructive preview."""
from _common import *
from engine import modular as M, modular_assets as A, generate
from PIL import Image
body=Image.new("RGBA",(64,128));body.paste((80,120,180,255),(12,8,52,120))
recipe={"width":64,"height":128,"pixel":False,"layers":[{"name":"Base","category":"body","image":M.png_uri(body)}]}
clean,images,ref,bb=A.reference(recipe)
ok(bb==(12,8,52,120),"placement uses body silhouette")
p=A.prompt("outfit","blue coat","front")
ok("blue coat" in p and "only the detachable asset" in p,"asset prompt asks for isolated item")
ok("single character, full body" not in generate.build_prompt(p,"magenta","modular_asset","anime"),"asset prompt avoids character-generation suffix")
rect=A.region("outfit",bb,body.size)
raw=Image.new("RGB",(128,128),"magenta");raw.paste((20,80,220),(30,20,98,108))
asset,info=A.finish(raw,rect,False)
ok(asset.width<=rect[2]-rect[0] and asset.height<=rect[3]-rect[1],"asset fits approximate region")
layer={"name":"Coat","category":"outfit","image":M.png_uri(asset),"x":info["x"],"y":info["y"],"visible":True,"scale":100,"opacity":100,"flip":False}
preview=A.candidate_preview(clean,images,layer)
ok(preview.size==body.size and preview.tobytes()!=body.tobytes(),"preview overlays separate asset")
ok(len(clean["layers"])==1 and images[0].tobytes()==body.tobytes(),"master remains unchanged")
try:A.finish(Image.new("RGB",(64,64),"magenta"),rect,False);ok(False,"empty rejected")
except ValueError:ok(True,"empty rejected")
try:A.reference({"width":64,"height":128,"layers":[]});ok(False,"missing body")
except ValueError:ok(True,"missing body rejected")
registered,meta=A.register_asset(asset,info,body.size)
ok(registered.size==body.size and meta["x"]==meta["y"]==0,"registered layer uses full source canvas and origin")
ok(registered.crop((info["x"],info["y"],info["x"]+asset.width,info["y"]+asset.height)).tobytes()==asset.tobytes(),"registration preserves fitted RGBA")
full={**layer,"image":M.png_uri(registered),"x":0,"y":0}
ok(A.candidate_preview(clean,images,full).tobytes()==preview.tobytes(),"registered preview equivalent to legacy fitted preview")
ok("fixed pose" in A.registered_prompt("hair_front","short hair","front"),"registered reference prompt")
try:A.register_asset(asset,{**info,"x":-1},body.size);ok(False,"invalid registration rejected")
except ValueError:ok(True,"invalid registration rejected")
# Body-derived guides retain the original canvas and follow asymmetric silhouettes.
shaped=Image.new("RGBA",(80,100))
shaped.paste((80,100,120,255),(30,5,50,30))
shaped.paste((80,100,120,255),(10,30,55,45))
shaped.paste((80,100,120,255),(32,45,48,75))
shaped.paste((80,100,120,255),(35,75,58,96))
marks=A.body_landmarks(shaped)
ok(marks["body"]==[10,5,58,96] and marks["head"][0]>marks["shoulders"][0],"silhouette bands detect asymmetric width")
hair_rect,hair_mask,_=A.placement_guide(shaped,"hair_front")
boot_rect,boot_mask,_=A.placement_guide(shaped,"footwear")
ok(hair_mask.size==boot_mask.size==shaped.size and hair_rect[3]<boot_rect[1],"category guides share canvas but distinct bands")
probe=Image.new("RGBA",shaped.size)
probe.putpixel((40,15),(255,0,0,255))
probe.putpixel((40,90),(255,0,0,255))
review=A.placement_review(probe,hair_mask)
ok(review["visible_pixels"]==2 and review["outside_guide"]==1 and review["outside_fraction"]==.5,"guide review reports spill without clipping")
ok(probe.getpixel((40,90))[3]==255,"guide review non-destructive")
try:A.body_landmarks(Image.new("RGBA",(16,16)));ok(False,"empty silhouette rejected")
except ValueError:ok(True,"empty silhouette rejected")
# Registered extraction preserves changed pixels at their exact coordinates.
from engine import instruction_edit
edited=shaped.copy()
edited.paste((20,50,200,255),(32,45,48,60))
edited.putpixel((29,4),(50,20,10,255))
isolated,meta=A.extract_edit(shaped,edited,hair_mask,30)
ok(isolated.size==shaped.size and isolated.getpixel((35,50))==edited.getpixel((35,50)) and isolated.getpixel((40,15))[3]==0,"difference extraction excludes unchanged pixels")
ok(isolated.getpixel((29,4))[3]==255 and meta["placement"]["outside_guide"]>0,"outside-guide changes reported not clipped")
try:A.extract_edit(shaped,shaped,hair_mask);ok(False,"no-change extraction rejected")
except ValueError:ok(True,"no-change extraction rejected")
original_run=instruction_edit.run_edit
try:
    def fake(source,model,ckpt,lora_dir,**kw):
        assert source.tobytes()==shaped.tobytes() and kw["keep_canvas"]
        return edited.copy(),{"seed":1,"backend":"qwen_instruction"}
    instruction_edit.run_edit=fake
    out,raw,meta=A.qwen_asset(shaped,hair_mask,{"supported":True,"backend":"qwen"},"qwen","", "outfit","blue coat","front",tolerance=30)
    ok(out.tobytes()==isolated.tobytes() and raw.tobytes()==edited.tobytes(),"mocked Qwen extraction route")
finally:
    instruction_edit.run_edit=original_run
# Shared extraction backend routing, including SDXL native guide mask.
try:
    calls=[]
    def fake_shared(source,model,ckpt,lora_dir,**kw):
        calls.append(kw)
        candidate=edited.copy()
        if kw.get("mask"):
            mask=instruction_edit.decode_mask(kw["mask"],source.size)
            candidate=instruction_edit.protected_composite(source,candidate,mask)
        return candidate,{"seed":1,"backend":instruction_edit.capability(model)}
    instruction_edit.run_edit=fake_shared
    out,raw,meta=A.edit_asset(shaped,hair_mask,{"supported":True,"backend":"neta"},"neta","","outfit","coat","front",tolerance=30)
    ok(out.tobytes()==isolated.tobytes() and "mask" not in calls[-1],"Neta registered extraction uses unmasked edit")
    out,raw,meta=A.edit_asset(shaped,hair_mask,{"supported":True,"family":"sdxl"},"sdxl","","hair_front","hair","front",tolerance=30)
    ok(bool(calls[-1].get("mask")) and out.getpixel((35,50))[3]==0 and meta["placement"]["outside_guide"]==0,"SDXL native mask limits extraction to guide")
    out,raw,meta=A.edit_asset(shaped,hair_mask,{"supported":True,"backend":"qwen"},"qwen","","outfit","coat","front",tolerance=30)
    ok(out.tobytes()==isolated.tobytes(),"shared adapter preserves Qwen behavior")
    try:A.edit_asset(shaped,hair_mask,{"supported":False},"unsupported","","outfit","coat","front");ok(False,"unsupported backend rejected")
    except ValueError:ok(True,"unsupported backend rejected")
finally:
    instruction_edit.run_edit=original_run
# Profiles map onto existing recipe categories and depth/attachment settings.
for name,category in (("armor","outfit"),("long_hair","hair_back"),("fringe","hair_front"),("boots","footwear"),("weapon","accessory"),("wings","accessory"),("cape","accessory")):
    spec=A.asset_profile(category,name)
    ok(spec["category"]==category and spec["description"] and spec["attachment"] in M.ATTACHMENTS,"specialized profile "+name)
ok(A.asset_profile("accessory","weapon","left")["attachment"]=="l_arm_l","left-hand weapon attachment")
ok(A.asset_profile("accessory","wings")["depth"]=="behind","wings behind body")
try:A.asset_profile("outfit","wings");ok(False,"profile mismatch rejected")
except ValueError:ok(True,"profile mismatch rejected")
wide_rect,wide_mask,_=A.specialized_guide(shaped,"accessory","wings")
normal_rect,normal_mask,_=A.placement_guide(shaped,"accessory")
ok(wide_mask.size==shaped.size and wide_rect[0]<normal_rect[0] and wide_rect[2]>normal_rect[2],"wings allowance expands laterally")
# A behind-body candidate must not cover the source body on the assembled preview.
rear=Image.new("RGBA",body.size)
rear.paste((255,0,0,255),(0,20,32,60))
rear_layer={"name":"Wing","category":"accessory","image":M.png_uri(rear),"x":0,"y":0,"scale":100,"opacity":100,"visible":True,"flip":False,"attachment":"torso","occlusion":{"depth":"behind","bones":[]}}
back_preview=A.candidate_preview(clean,images,rear_layer,False)
ok(back_preview.getpixel((20,30))==body.getpixel((20,30)) and back_preview.getpixel((2,30))==(255,0,0,255),"rear profile depth respects body")
# Review applies transforms without changing the recipe or candidate source.
import copy
before=copy.deepcopy(recipe)
source_layer=copy.deepcopy(rear_layer)
adjusted={**rear_layer,"x":5,"y":3,"scale":100,"opacity":100}
guide=Image.new("L",body.size,255)
row,assembled,placed,review=A.review_candidate(recipe,adjusted,False,guide)
ok(recipe==before and rear_layer==source_layer,"review leaves approved recipe and original candidate unchanged")
ok(placed.size==body.size and placed.getpixel((5,23))==(255,0,0,255),"registered export bakes reviewed placement")
ok(assembled.getpixel((20,30))==body.getpixel((20,30)) and assembled.getpixel((5,23))==(255,0,0,255),"review retains behind-body occlusion")
ok(review["placement"]["outside_guide"]==0 and row["x"]==5,"review recalculates guide statistics")
try:A.review_candidate(recipe,{**adjusted,"x":2048},False);ok(False,"off-canvas candidate rejected")
except ValueError:ok(True,"off-canvas candidate rejected")
try:A.review_candidate(recipe,{**adjusted,"category":"body"},False);ok(False,"body replacement rejected")
except ValueError:ok(True,"body replacement rejected")
from engine import main
response=main.modular_review_asset(main.ModularCandidateReview(recipe=recipe,layer=adjusted,replace_category=False,placement_mask=M.png_uri(guide)))
ok(M.decode(response["registered"]).tobytes()==placed.tobytes(),"review endpoint registered export")
# Stabilization: large extraction, clipping, and exact threshold equivalence.
import numpy as np
rng=np.random.default_rng(61)
a=rng.integers(0,256,(128,128,4),dtype=np.uint8)
b=rng.integers(0,256,(128,128,4),dtype=np.uint8)
expect=(b[:,:,3]>=32)&((a[:,:,3]<32)|(np.max(np.abs(a.astype(np.int16)-b.astype(np.int16)),axis=2)>30))
expected=np.zeros_like(b)
expected[expect]=b[expect]
actual,_=A.extract_edit(Image.fromarray(a),Image.fromarray(b),Image.new("L",(128,128),255),30)
ok(actual.tobytes()==expected.tobytes(),"channelwise extraction equivalent to original RGBA threshold")
large=Image.new("RGBA",(1024,1024))
large.paste((90,120,150,255),(300,50,720,990))
dressed=large.copy()
dressed.paste((30,60,190,255),(300,350,720,650))
_,lg,_=A.specialized_guide(large,"outfit","armor")
asset,meta=A.extract_edit(large,dressed,lg)
ok(asset.size==large.size and meta["placement"]["visible_pixels"]==420*300,"maximum canvas extraction remains registered")
_,_,clipped,meta=A.review_candidate(recipe,{**rear_layer,"x":-5},False)
ok(meta["clipping_warning"] and clipped.getchannel("A").getbbox(),"partial clipping warning without destructive rejection")
_,_,_,meta=A.review_candidate(recipe,adjusted,False)
ok(not meta["clipping_warning"],"in-canvas candidate does not warn")
try:A.extract_edit(large,dressed,lg,0);ok(False,"invalid extraction tolerance rejected")
except ValueError:ok(True,"invalid extraction tolerance rejected")
# Validate review decodes recipe exactly once.
original_validate=M.validate
calls=[]
try:
    def count_validate(value):
        calls.append(1)
        return original_validate(value)
    M.validate=count_validate
    A.review_candidate(recipe,adjusted,False)
    ok(len(calls)==1,"candidate review single recipe validation")
finally:
    M.validate=original_validate
done("test_modular_assets")
