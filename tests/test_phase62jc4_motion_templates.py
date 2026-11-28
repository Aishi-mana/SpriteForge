import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import motion_templates as M,full_frame_guidance as G,full_frame as F

def run():
    for item in M.catalog():
        poses=M.validate(item["poses"])
        assert poses[0]["at"]==0 and poses[-1]["at"]==100
        assert "Ordered motion plan" in G.prompt("",{"poses":poses})
        assert F.validate({**F.default(),"guidance":{"poses":poses}})["guidance"]["poses"]==poses
    assert G.settings()["poses"]==[]
    for bad in [[{"at":0,"pose":"start"}],[{"at":0,"pose":"start"},{"at":0,"pose":"repeat"},{"at":100,"pose":"end"}]]:
        try:M.validate(bad)
        except ValueError:pass
        else:raise AssertionError("invalid plan accepted")
    print("ok reusable motion plans")
if __name__=="__main__":run()
