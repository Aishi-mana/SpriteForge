"""GPU-free character reference, direction prompt and alignment checks."""
from _common import *
from engine import character as C, directions
from PIL import Image
import numpy as np, base64, io
a=Image.new("RGBA",(80,160))
a.paste((40,100,200,255),(20,10,60,150))
b=Image.new("RGBA",(100,80))
b.paste((40,100,200,255),(10,5,90,75))
for size in (64,256):
    out=C.align(a,size,size==64)
    ok(out.size==(size,size) and out.getchannel("A").getbbox()[3]==round(size*.94),"shared canvas and baseline")
    wide=C.align(b,size,size==64)
    ok(wide.getchannel("A").getbbox()[2]<=size and wide.getchannel("A").getbbox()[3]==round(size*.94),"wide view fits without clipping")
p=C.view_prompt("N","blue armor")
ok("blue armor" in p and directions.HINT["N"] in p and "same design" in p,"view and identity prompt combined")
try:C.view_prompt("W");ok(False,"mirror not independently generated")
except ValueError:ok(True,"mirror handled by directions renderer")
buf=io.BytesIO();a.save(buf,"PNG");u="data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode()
ok(C.decode_reference(u).tobytes()==a.tobytes(),"master image round trip")
try:C.align(Image.new("RGBA",(32,32)),64);ok(False,"empty image rejected")
except ValueError:ok(True,"empty image rejected")
out,info=C.finish(a,a,"anime",256)
ok(out.size==(256,256) and info["pipeline"]=="hd" and info["identity_reference"],"HD direction pipeline")
done("test_character")
