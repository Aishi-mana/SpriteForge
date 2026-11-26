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
done("test_modular_assets")
