import sys,io,base64
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import controlled_idle as I, full_frame_extract as E, full_frame as F, world

def uri(im):
    b=io.BytesIO();im.save(b,"PNG")
    return "data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()

def run():
    im=Image.new("RGBA",(48,64))
    draw=ImageDraw.Draw(im)
    draw.rectangle((10,4,37,59),fill=(220,190,160,255))
    draw.rectangle((14,28,34,34),fill=(40,80,160,255))
    d=F.validate({**F.default(),"reference":uri(im)})
    out=I.generate(d,{"frames":16,"fps":16,"amplitude":2})
    frames=[np.asarray(world.image(v)) for v in out["frames"]]
    assert len(frames)==16 and out["loop"]
    assert np.array_equal(frames[0],np.asarray(im))
    assert np.array_equal(frames[0][:25],frames[8][:25])
    assert np.array_equal(frames[0][47:],frames[8][47:])
    assert not np.array_equal(frames[0],frames[8])
    assert len(set(I.generate(d,{"frames":8,"amplitude":0})["frames"]))==1
    alpha=Image.new("L",(3,1));alpha.putdata([32,255,32])
    rgb=Image.new("RGB",(3,1),(240,240,240));rgb.putpixel((2,0),(30,30,30))
    cleaned=E.cleanup_mask(alpha,rgb,E.settings({"background":"neutral","cleanup":100}))
    assert list(cleaned.getdata())==[0,255,32]
    assert E.cleanup_mask(alpha,rgb,E.settings({})).tobytes()==alpha.tobytes()
    print("ok controlled idle and conservative cleanup")
if __name__=="__main__":run()
