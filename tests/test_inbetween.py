"""GPU-free endpoint invariants and mocked redraw."""
from _common import *
from engine import inbetween
from PIL import Image
a=Image.new("RGBA",(32,32),(255,0,0,255))
b=Image.new("RGBA",(32,32),(0,0,255,128))
calls=[]
def redraw(guide,t,i):
    calls.append((t,i))
    return Image.new("RGBA",guide.size,(0,255,0,90))
fr=inbetween.frames(a,b,5,redraw)
ok(fr[0].tobytes()==a.tobytes() and fr[-1].tobytes()==b.tobytes(),"exact RGBA endpoints locked")
ok(len(calls)==3 and len(fr)==5,"only in-betweens redrawn")
ok(fr[2].getpixel((0,0))==(0,255,0,90),"mocked in-between returned")
ok(inbetween.frames(a,b,2,redraw)[-1].tobytes()==b.tobytes() and len(calls)==3,"two frames do not invoke model")
try:
    inbetween.frames(a,Image.new("RGBA",(16,16)),4)
    ok(False,"mismatched canvas rejected")
except ValueError:
    ok(True,"mismatched canvas rejected")
c=inbetween.blend(Image.new("RGBA",(1,1),(255,0,0,0)),Image.new("RGBA",(1,1),(0,0,255,255)),.5)
ok(c.getpixel((0,0))==(0,0,255,128),"alpha-correct blend")
done("test_inbetween")
