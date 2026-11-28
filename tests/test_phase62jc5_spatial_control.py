import sys,base64,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import wan_control as C,wan_video as W

def run():
    raw=b"\x00\x00\x00\x18ftypisom"
    body={"control_video":"data:video/mp4;base64,"+base64.b64encode(raw).decode()}
    q=C.settings(body)
    q.update(control_weight=C.WEIGHTS[0],control_vae=C.VAES[0],prompt="idle",seed=1,fps=16)
    g=C.graph(q,W.CLIP)
    assert g["control"]["class_type"]=="Wan22FunControlToVideo"
    assert g["control"]["inputs"]["ref_image"]==["ref",0]
    assert g["control"]["inputs"]["control_video"]==["components",0]
    assert g["sample"]["inputs"]["steps"]==20
    assert not any("Lora" in x["class_type"] for x in g.values())
    q["control_kind"]="canny"
    assert C.graph(q,W.CLIP)["control"]["inputs"]["control_video"]==["edges",0]
    with tempfile.TemporaryDirectory() as d:
        root=Path(d)
        (root/"unet").mkdir();(root/"vae").mkdir()
        (root/"unet"/C.WEIGHTS[1]).touch();(root/"vae"/C.VAES[1]).touch()
        weight,vae=C.files(root)
        assert weight==C.WEIGHTS[1] and vae in C.VAES
        assert (root/"vae"/vae).is_file()
    for invalid in ({},{**body,"frames":34},{**body,"control_kind":"bad"}):
        try:C.settings(invalid)
        except ValueError:pass
        else:raise AssertionError("invalid control accepted")
    print("ok spatial graph and model discovery")
if __name__=="__main__":run()
