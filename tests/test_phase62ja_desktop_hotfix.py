import sys,json,io
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import main as M,full_frame_extract as E,full_frame_guidance as G,wan_video as W
from starlette.datastructures import UploadFile

def run():
    # Exercise the same bounded file path as the browser without GPU inference.
    doc={"frames":["x"*1100000],"locked_frames":[]}
    payload=json.dumps(doc).encode()
    with patch.object(E,"extract",return_value={"frames":["ok"]}) as extract:
        for _ in range(2):
            result=M.full_frame_extract(UploadFile(io.BytesIO(b"mp4")), "{}", None, UploadFile(io.BytesIO(payload)))
            assert result=={"frames":["ok"]}
            assert extract.call_args.args[2]==doc
        assert extract.call_count==2
    idle={"preset":"idle_minimal"}
    assert "lips and jaw remain still" in G.prompt("",idle)
    assert "lip movement" in G.negative(idle)
    assert "lip movement" not in G.negative({"preset":"walk"})
    graph=W.graph(W.settings({"guidance":idle,"conditioning":"flf"}))
    assert "lip movement" in graph["neg"]["inputs"]["text"]
    ui=(Path(__file__).resolve().parents[1]/"ui/index.html").read_text(encoding="utf-8")
    assert "fd.append('document_file',new Blob" in ui
    assert "FF.quickSampling=sampling;FF.quickVideoRev=FF.rev" in ui
    print("ok repeat extraction transport and idle guidance")
if __name__=="__main__":run()
