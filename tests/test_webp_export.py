"""CPU-only standalone WebP encoding contract."""
from _common import *
from engine import webp_export as W
from PIL import features
from unittest.mock import patch
install_fastapi_stubs()
from engine import main as M

ok(features.check("webp"),"Pillow includes WebP encoder")
im=Image.new("RGBA",(3,2))
im.putdata([(10,20,30,0),(255,0,0,255),(40,50,60,128),(255,255,255,255),(0,0,0,0),(30,200,90,64)])
uri=data_url(im)
r=M.export_webp(M.WebPExport(image=uri))
raw=base64.b64decode(r["image"].split(",",1)[1])
ok(r["image"].startswith("data:image/webp;base64,") and raw[:4]==b"RIFF" and raw[8:12]==b"WEBP","genuine WebP bytes and MIME")
dec=Image.open(io.BytesIO(raw)).convert("RGBA")
ok(dec.size==im.size and np.array_equal(np.asarray(dec),np.asarray(im)),"lossless exact RGBA roundtrip")
scaled=from_url(W.encode(uri,8))
ok(scaled.size==(24,16) and np.array_equal(np.asarray(scaled),np.asarray(im.resize((24,16),Image.Resampling.NEAREST))),"8x nearest-neighbor preserves all RGBA values")
for bad,scale in ((uri,2),("data:image/png;base64,not-base64",1),("data:image/jpeg;base64,AAAA",1)):
    try:W.encode(bad,scale);ok(False,"reject invalid input")
    except ValueError:ok(True,"reject invalid input")
with patch.object(W,"MAX_PIXELS",5):
    try:W.encode(uri);ok(False,"pixel budget")
    except ValueError:ok(True,"pixel budget before conversion")
with patch.object(W.features,"check",return_value=False):
    try:W.encode(uri);ok(False,"missing WebP support")
    except ValueError:ok(True,"clear unsupported encoder error")
done("test_webp_export")
