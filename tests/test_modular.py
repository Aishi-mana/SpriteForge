"""CPU-only layer order, swapping, transparency, portable recipe and project persistence."""
from _common import *
from engine import modular as M, projects
import io,zipfile,json
body=Image.new("RGBA",(16,16),(255,0,0,255))
shirt=Image.new("RGBA",(8,8),(0,0,255,128))
hat=Image.new("RGBA",(4,4),(0,255,0,255))
recipe={"width":32,"height":32,"pixel":True,"layers":[
    {"name":"Base","category":"body","image":M.png_uri(body),"x":4,"y":4},
    {"name":"Shirt","category":"outfit","image":M.png_uri(shirt),"x":4,"y":4},
    {"name":"Hat","category":"accessory","image":M.png_uri(hat),"x":-2,"y":0,"visible":False}]}
im=M.render(recipe)
ok(im.getpixel((4,4))==(127,0,128,255),"alpha composite in layer order")
ok(im.getpixel((0,0))==(0,0,0,0),"hidden layer leaves transparency")
recipe["layers"][2]["visible"]=True
ok(M.render(recipe).getpixel((0,0))==(0,255,0,255),"negative offset clips correctly")
recipe["layers"][1]["visible"]=False
ok(M.render(recipe).getpixel((4,4))==(255,0,0,255),"swap clothing without changing base")
clean,images=M.validate(recipe)
ok(images[0].tobytes()==body.tobytes(),"source layer unchanged")
with zipfile.ZipFile(io.BytesIO(M.bundle(recipe))) as z:
    restored=json.loads(z.read("recipe.json"))
    ok(M.render(restored).tobytes()==M.render(recipe).tobytes(),"portable recipe round trip")
    ok("layers/01_outfit.png" in z.namelist() and "character.png" in z.namelist(),"bundle includes source layers and composite")
root=tmpdir();projects.save(root,"Modular",{"modular":recipe})
ok(projects.load(root,"Modular")["modular"]==clean,"project round trip")
recipe["layers"][0]["scale"]=1000
try:M.render(recipe);ok(False,"oversize scale")
except ValueError:ok(True,"oversize scale rejected")
done("test_modular")
