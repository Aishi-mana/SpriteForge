import sys, tempfile, json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import wan_video as W

def run():
    with tempfile.TemporaryDirectory() as t:
        root=Path(t);models=root/"models";comfy=root/"comfy";python=comfy/"python.exe"
        (comfy/"custom_nodes/ComfyUI-GGUF").mkdir(parents=True)
        (comfy/"main.py").touch();python.touch()
        models.mkdir()
        with patch.object(W.local_runtime,"runtime",return_value=(comfy,python)):
            assert not W.readiness(str(models))[0]["ready"]
            for folder,name in (("unet",W.HIGH),("diffusion_models",W.LOW),("loras",W.LH),("loras",W.LL),("text_encoders",W.CLIP),("vae",W.VAE)):
                (models/folder).mkdir(exist_ok=True);(models/folder/name).touch()
            assert W.readiness(str(models))[0]["ready"]
            (models/"loras"/W.LL).unlink()
            assert W.LL in W.readiness(str(models))[0]["missing"]
    q=W.settings({"prompt":"idle breathing","seed":42})
    g=W.graph(q)
    assert g["i2v"]["inputs"]["length"]==33 and g["vid"]["inputs"]["fps"]==16
    assert g["ks1"]["inputs"]["end_at_step"]==2 and g["ks2"]["inputs"]["start_at_step"]==2
    assert g["unet_l"]["inputs"]["unet_name"]==W.LOW
    assert "%MODEL%" not in json.dumps(g)
    try: W.settings({"prompt":"idle","frames":34})
    except ValueError: pass
    else: raise AssertionError("invalid frame count accepted")
    print("ok Wan readiness and workflow substitution")

if __name__=="__main__":
    run()
