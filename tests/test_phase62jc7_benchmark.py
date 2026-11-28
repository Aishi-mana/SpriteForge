import sys,io,base64
from pathlib import Path
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import animation_benchmark as B,full_frame as F

def sprite(x=None,opaque=False):
    im=Image.new("RGBA",(64,64),(0,0,0,255 if opaque else 0))
    if x is not None:ImageDraw.Draw(im).rectangle((x,20,x+10,40),fill=(255,100,50,255))
    b=io.BytesIO();im.save(b,"PNG")
    return "data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()

def run():
    a,b=sprite(10),sprite(15)
    doc={**F.default(),"width":64,"height":64,"pivot":[32,40],"reference":a,"frames":[a,a,a]}
    m=B.measure(doc)
    assert m["unique_frames"]==1 and m["adjacent_change_pct"]==0
    assert m["seam_change_pct"]==0 and m["adjacent_mask_iou_pct"]==100
    m=B.measure({**doc,"frames":[a,b,a]})
    assert m["unique_frames"]==2 and m["adjacent_change_pct"]>0
    assert m["seam_change_pct"]==0 and m["centroid_drift_px"]==5
    assert m["adjacent_mask_iou_pct"]<100 and m["bottom_edge_range_px"]==0
    m=B.measure({**doc,"frames":[a,sprite(),sprite(10,True)]})
    assert m["empty_frames"]==1 and m["opaque_frames"]==1
    try:B.measure({**doc,"frames":[a]})
    except ValueError:pass
    else:raise AssertionError("Accepted single frame")
    print("ok benchmark diagnostics")
if __name__=="__main__":run()
