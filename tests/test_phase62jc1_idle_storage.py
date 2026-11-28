import sys,io,base64
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import controlled_idle as I,full_frame as F

def run():
    rng=np.random.default_rng(4)
    a=rng.integers(0,256,(256,256,4),dtype=np.uint8)
    a[:,:,3]=255
    a[:8,:,3]=0
    b=io.BytesIO();Image.fromarray(a,"RGBA").save(b,"PNG")
    ref="data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()
    d=F.validate({**F.default(),"reference":ref})
    with patch.object(F,"MAX_ENCODED",len(ref)+350000):
        out=I.generate(d,{"frames":16,"fps":8,"amplitude":1,"max_side":256,"auto_fit":True})
        assert out["width"]<256
        assert out["reference"]==ref
        assert len(out["frames"])==16 and out["fps"]==8
        assert out["frames"][1]==out["frames"][-1]
        assert sum(map(len,out["frames"]))+len(ref)<=F.MAX_ENCODED
    print("ok idle automatic output fit and timing")
if __name__=="__main__":run()
