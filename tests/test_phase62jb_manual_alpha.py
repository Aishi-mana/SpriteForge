import sys,io,base64
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import manual_alpha as A, full_frame as F, world

def uri(im):
    b=io.BytesIO();im.save(b,"PNG")
    return "data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()

def run():
    src=uri(Image.new("RGBA",(16,16),(240,210,190,255)))
    d=F.validate({**F.default(),"width":16,"height":16,"pivot":[8,15],"frames":[src,src]})
    opts={"index":0,"mode":"erase","points":[[4,8],[12,8]],"radius":2,"strength":100}
    erased=A.apply(d,opts)
    assert world.image(erased["frames"][0]).getpixel((8,8))==(240,210,190,0)
    assert world.image(erased["frames"][0]).getpixel((0,0))==(240,210,190,255)
    assert erased["frames"][1]==src
    restored=A.apply(erased,{**opts,"mode":"restore","source":src})
    assert world.image(restored["frames"][0]).getpixel((8,8))==(240,210,190,255)
    for doc,opt in [(dict(d,keyframes=[0],locked_frames=[0]),opts),(erased,{**opts,"mode":"restore"}),(d,{**opts,"points":[[100,0]]})]:
        try:A.apply(doc,opt)
        except ValueError:pass
        else:raise AssertionError("invalid brush accepted")
    print("ok manual alpha brush")
if __name__=="__main__":run()
