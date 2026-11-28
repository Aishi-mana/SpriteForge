import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import wan_video as W

def run():
    body={"prompt":"quiet breathing","guidance":{"preset":"idle_minimal"}}
    normal=W.settings(body)
    assert normal["conditioning"]=="i2v"
    guided=W.settings({**body,"conditioning":"flf"})
    assert "identical starting pose" in guided["prompt"]
    g=W.graph(guided)
    assert g["i2v"]["class_type"]=="WanFirstLastFrameToVideo"
    assert g["i2v"]["inputs"]["start_image"]==["ref1",0]
    assert g["i2v"]["inputs"]["end_image"]==["ref2",0]
    assert g["ref2"]["inputs"]["image"]=="end.png"
    assert g["save"]["inputs"]["format"]=="mp4"
    custom=W.settings({**body,"conditioning":"flf","end_reference":"example"})
    assert custom["end_reference"]=="example"
    assert "identical starting pose" not in custom["prompt"]
    try:W.settings({**body,"conditioning":"unknown"})
    except ValueError:pass
    else:raise AssertionError("invalid conditioning accepted")
    print("ok Wan first-last conditioning")
if __name__=="__main__":run()
