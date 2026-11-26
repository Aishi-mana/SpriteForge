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
done("test_modular_assets")
