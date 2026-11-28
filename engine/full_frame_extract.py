"""Bounded video sampling and chroma extraction for complete sprite frames."""
import base64, io, math, tempfile
from pathlib import Path
import numpy as np
from PIL import Image
from . import world, full_frame as F, full_frame_guidance as G

def settings(q):
    if not isinstance(q,dict):raise ValueError("Invalid extraction settings")
    n=world.integer
    bg=q.get("background","green")
    if bg not in (*G.BACKGROUNDS,"none"):raise ValueError("Invalid extraction background")
    return dict(background=bg,fps=n(q.get("fps",12),1,30,"sampling FPS"),
        start=n(q.get("start",0),0,60000,"start milliseconds"),
        end=n(q.get("end",4000),1,60000,"end milliseconds"),
        tolerance=n(q.get("tolerance",45),0,255,"key tolerance"),
        softness=n(q.get("softness",25),0,100,"key softness"),
        trim=world.boolean(q.get("trim",True),"shared trim"))

def key_frame(im,q):
    a=np.asarray(im.convert("RGBA")).copy()
    if q["background"]!="none":
        key=np.array(G.BACKGROUNDS[q["background"]][0],dtype=np.float32)
        dist=np.max(np.abs(a[:,:,:3].astype(np.float32)-key),axis=2)
        alpha=np.clip((dist-q["tolerance"])/max(1,q["softness"]),0,1)
        a[:,:,3]=np.rint(a[:,:,3]*alpha).astype(np.uint8)
        a[a[:,:,3]==0,:3]=0
    return Image.fromarray(a,"RGBA")

def assemble(images,q,doc):
    q=settings(q);d=F.validate(doc)
    images=list(images)
    if not images or len(images)>F.MAX_FRAMES:raise ValueError("Invalid sampled frame count")
    w,h=images[0].size
    if max(w,h)>2048 or w*h*len(images)>F.MAX_PIXELS or any(im.size!=(w,h) for im in images):raise ValueError("Sampled frames exceed canvas budget")
    frames=[key_frame(im,q) for im in images]
    boxes=[b for im in frames if (b:=im.getbbox())]
    if not boxes:raise ValueError("All sampled frames are transparent")
    if q["trim"]:
        box=(min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes))
        frames=[im.crop(box) for im in frames]
    w,h=frames[0].size
    out=[]
    for im in frames:
        buf=io.BytesIO();im.save(buf,"PNG");out.append("data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode())
        if sum(map(len,out))>F.MAX_ENCODED:raise ValueError("Extracted frames exceed encoded budget; reduce range or FPS")
    if d["locked_frames"]:raise ValueError("Unlock frames before replacing the sequence")
    if any(v["frames"] for v in d["directions"].values()) and (w,h,q["fps"])!=(d["width"],d["height"],d["fps"]):raise ValueError("Extraction must match shared directional canvas and FPS; disable trim or choose matching settings")
    return F.validate({**d,"combat":[],"keyframes":[],"locked_frames":[],"width":w,"height":h,"pivot":[w//2,h-1],"fps":q["fps"],"frames":out})

def extract(raw,q,doc):
    q=settings(q)
    if q["end"]<=q["start"]:raise ValueError("End must follow start")
    if not raw or len(raw)>64_000_000:raise ValueError("Video exceeds 64 MB limit")
    count=math.ceil((q["end"]-q["start"])*q["fps"]/1000)
    if count>F.MAX_FRAMES:raise ValueError("Sample at most 120 frames")
    try:import imageio.v2 as imageio
    except ImportError as e:raise RuntimeError("Install imageio and imageio-ffmpeg in the engine environment") from e
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"source.mp4";path.write_bytes(raw)
        reader=imageio.get_reader(str(path),format="FFMPEG")
        try:
            meta=reader.get_meta_data();fps=float(meta["fps"]);w,h=meta["size"]
            if not math.isfinite(fps) or fps<=0 or max(w,h)>2048 or w*h*count>F.MAX_PIXELS:raise ValueError("Video exceeds sampling budget")
            frames=[]
            for i in range(count):
                idx=int((q["start"]/1000+i/q["fps"])*fps)
                try:frame=reader.get_data(idx)
                except IndexError:break
                frames.append(Image.fromarray(frame))
            return assemble(frames,q,doc)
        finally:reader.close()
