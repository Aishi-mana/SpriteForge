import sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import builtin_motion as B,full_frame_guidance as G

def run():
    body={"width":256,"height":256,"frames":9,"fps":16,"strength":80}
    for preset in B.PRESETS:
        frames,fps=B.render({**body,"preset":preset})
        assert len(frames)==9 and fps==16 and frames[0].size==(256,256)
        assert np.array_equal(np.asarray(frames[0]),np.asarray(frames[-1]))
        assert any(not np.array_equal(np.asarray(frames[0]),np.asarray(f)) for f in frames[1:-1]),preset
        assert preset in G.PRESETS
    frames,_=B.render({**body,"strength":0})
    assert all(np.array_equal(np.asarray(frames[0]),np.asarray(f)) for f in frames)
    ui=(Path(__file__).resolve().parents[1]/"ui/index.html").read_text(encoding="utf-8")
    assert 'id="ffEasyMode"' in ui and "await ffPrepareGuide('builtin')" in ui
    assert "(mode===\"guided\"||mode===\"fastloop\")?\"flf\":\"i2v\"" in ui
    print("ok procedural guide library and simple workflow")
if __name__=="__main__":run()
