"""Shared helpers for the SpriteForge test suite (no GPU, no network, no browser needed)."""
import base64, io, json, sys, tempfile, types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import numpy as np
from PIL import Image

_fails = []


def ok(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        _fails.append(msg)


def done(name):
    print(f"\n{name}: " + ("ALL PASSED" if not _fails else f"{len(_fails)} FAILED"))
    sys.exit(1 if _fails else 0)


def tmpdir():
    return Path(tempfile.mkdtemp())


def mock_sdxl_checkpoint(path):
    """Small structurally valid safetensors fixture, never loaded by a model."""
    header=json.dumps({"conditioner.embedder.1.x":{"dtype":"F16","shape":[4],"data_offsets":[0,8]}}).encode("utf-8")
    header+=b" "*((-len(header))%8)
    Path(path).write_bytes(len(header).to_bytes(8,"little")+header+b"\0"*8)


def png_bytes(im):
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def data_url(im):
    return "data:image/png;base64," + base64.b64encode(png_bytes(im)).decode()


def from_url(u):
    return Image.open(io.BytesIO(base64.b64decode(u.split(",", 1)[1]))).convert("RGBA")


class Up:
    """Stand-in for FastAPI's UploadFile."""
    def __init__(self, im_or_bytes, filename="f.png"):
        self.file = io.BytesIO(im_or_bytes if isinstance(im_or_bytes, bytes) else png_bytes(im_or_bytes))
        self.filename = filename


JOINTS = {"head": [20, 3], "neck": [20, 15], "pelvis": [20, 36], "l_shoulder": [15, 17], "l_elbow": [11, 26], "l_wrist": [11, 34],
          "r_shoulder": [25, 17], "r_elbow": [29, 26], "r_wrist": [29, 34], "l_hip": [16.5, 37], "l_knee": [16.5, 49],
          "l_ankle": [16.5, 61], "r_hip": [23.5, 37], "r_knee": [23.5, 49], "r_ankle": [23.5, 61]}


def synth_sprite():
    """A 40x64 blocky humanoid with a sword above the right hand. Returns (sprite, joints, overrides)."""
    from engine import rig
    a = np.zeros((64, 40, 4), np.uint8)
    def R(x0, x1, y0, y1, c): a[y0:y1, x0:x1] = (*c, 255)
    R(15, 25, 2, 14, (240, 200, 160)); R(15, 25, 2, 6, (120, 60, 30)); R(13, 27, 15, 36, (40, 80, 200))
    R(9, 13, 16, 34, (200, 40, 40)); R(27, 31, 16, 34, (200, 40, 40)); R(14, 19, 36, 62, (60, 60, 70)); R(21, 26, 36, 62, (60, 60, 70))
    R(14, 19, 60, 64, (90, 50, 30)); R(21, 26, 60, 64, (90, 50, 30)); R(30, 32, 6, 18, (220, 220, 230))
    ov = [[x, y, rig.BONE_IDX["r_arm_l"]] for x in (30, 31) for y in range(6, 18)]  # the sword follows the right forearm
    return Image.fromarray(a, "RGBA"), json.loads(json.dumps(JOINTS)), ov


def hero_sprite():
    """Like synth_sprite but with a cape (screen-left of the torso) and a ponytail painted as secondary-motion parts."""
    from engine import rig
    a = np.zeros((64, 40, 4), np.uint8)
    def R(x0, x1, y0, y1, c): a[y0:y1, x0:x1] = (*c, 255)
    R(15, 25, 2, 14, (240, 200, 160)); R(15, 25, 2, 6, (120, 60, 30)); R(13, 27, 15, 36, (40, 80, 200)); R(27, 31, 16, 34, (200, 40, 40))
    R(14, 19, 36, 62, (60, 60, 70)); R(21, 26, 36, 62, (60, 60, 70)); R(14, 19, 60, 64, (90, 50, 30)); R(21, 26, 60, 64, (90, 50, 30))
    R(4, 13, 15, 46, (150, 25, 40)); R(9, 15, 4, 11, (230, 140, 40))
    ov = [[x, y, rig.SEC_LABEL["cape"]] for y in range(15, 46) for x in range(4, 13)] + \
         [[x, y, rig.SEC_LABEL["hair"]] for y in range(4, 11) for x in range(9, 15)]
    return Image.fromarray(a, "RGBA"), json.loads(json.dumps(JOINTS)), ov


def install_fastapi_stubs():
    """The test sandbox has no fastapi/pydantic. If they are missing, install tiny stand-ins so engine.main can be imported and
    its endpoint FUNCTIONS called directly. With the real packages installed nothing is stubbed. Returns True if stubbed."""
    try:
        import fastapi, pydantic  # noqa
        return False
    except ImportError:
        pass
    fa = types.ModuleType("fastapi")
    class HTTPException(Exception):
        def __init__(self, status_code, detail): self.status_code, self.detail = status_code, detail
    class FastAPI:
        def __init__(self, *a, **k): pass
        def _d(self, *a, **k): return lambda f: f
        get = post = delete = mount = exception_handler = _d
    fa.FastAPI, fa.HTTPException = FastAPI, HTTPException
    fa.File = fa.Form = fa.Body = lambda *a, **k: None
    class UploadFile: pass
    fa.UploadFile = UploadFile
    fr = types.ModuleType("fastapi.responses"); fr.FileResponse = object; fr.StreamingResponse = lambda g, **k: g
    fr.JSONResponse = lambda c, status_code=200: (c, status_code)
    fs = types.ModuleType("fastapi.staticfiles"); fs.StaticFiles = lambda **k: None
    se = types.ModuleType("starlette.exceptions"); se.HTTPException = HTTPException
    pm = types.ModuleType("pydantic")
    class BaseModel:
        def __init__(self, **kw):
            for k in getattr(type(self), "__annotations__", {}): setattr(self, k, kw.get(k, getattr(type(self), k, None)))
    pm.BaseModel = BaseModel
    sys.modules.update({"fastapi": fa, "fastapi.responses": fr, "fastapi.staticfiles": fs, "starlette": types.ModuleType("starlette"),
                        "starlette.exceptions": se, "pydantic": pm})
    return True


def http_exception():
    import fastapi
    return fastapi.HTTPException
