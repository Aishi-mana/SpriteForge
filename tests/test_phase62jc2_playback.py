import sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import controlled_idle as I,world

def run():
    ui=(Path(__file__).resolve().parents[1]/"ui/index.html").read_text(encoding="utf-8")
    draw=ui.split("function ffDraw(){",1)[1].split("async function ffImport(",1)[0]
    assert "if(c.width!==d.width)" in draw
    assert "if(entry.ready)paint(entry.image)" in draw
    assert "Promise.all(entries.map(v=>v.promise))" in ui
    assert "ticket!==FF.playTicket" in ui
    im=Image.new("RGBA",(120,160))
    d=ImageDraw.Draw(im);d.rectangle((20,10,99,149),fill=(220,190,160,255))
    d.rectangle((35,76,84,92),fill=(20,40,80,255))
    frames=I.render(im,32,3,10000000)
    a,b=[np.array(world.image(frames[i])) for i in (0,16)]
    assert np.array_equal(a[:65],b[:65])
    assert np.array_equal(a[120:],b[120:])
    assert np.count_nonzero(np.any(a!=b,axis=2))>30
    assert frames[1]==frames[-1]
    print("ok playback contract and visible torso deformation")
if __name__=="__main__":run()
