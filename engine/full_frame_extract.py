"""Bounded video sampling and chroma extraction for complete sprite frames."""
import base64, io, math, tempfile
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage
from . import world, full_frame as F, full_frame_guidance as G

def settings(q):
    if not isinstance(q,dict):raise ValueError("Invalid extraction settings")
    n=world.integer
    bg=q.get("background","green")
    if bg not in (*G.BACKGROUNDS,"none"):raise ValueError("Invalid extraction background")
    method=q.get("method","chroma")
    if method not in ("chroma","birefnet","none"):raise ValueError("Invalid alpha method")
    return dict(method=method,cleanup=n(q.get("cleanup",0),0,100,"background cleanup"),temporal=n(q.get("temporal",0),0,100,"alpha consistency"),background=bg,fps=n(q.get("fps",12),1,30,"sampling FPS"),
        start=n(q.get("start",0),0,60000,"start milliseconds"),
        end=n(q.get("end",4000),1,60000,"end milliseconds"),
        tolerance=n(q.get("tolerance",24),0,255,"key tolerance"),
        softness=n(q.get("softness",12),0,100,"key softness"),
        trim=world.boolean(q.get("trim",True),"shared trim"))

def key_frame(im,q):
    a=np.asarray(im.convert("RGBA")).copy()
    if q["background"]!="none":
        key=np.array(G.BACKGROUNDS[q["background"]][0],dtype=np.float32)
        dist=np.max(np.abs(a[:,:,:3].astype(np.float32)-key),axis=2)
        alpha=np.clip((dist-q["tolerance"])/max(1,q["softness"]),0,1)
        # Only remove background-like pixels connected to the canvas border.
        # Enclosed matching colors (skin, armor, eyes) retain their original alpha.
        candidate=alpha<1
        seeds=np.zeros_like(candidate)
        seeds[0,:]=candidate[0,:];seeds[-1,:]=candidate[-1,:]
        seeds[:,0]=candidate[:,0];seeds[:,-1]=candidate[:,-1]
        connected=ndimage.binary_propagation(seeds,mask=candidate)
        alpha=np.where(connected,alpha,1.0)
        a[:,:,3]=np.rint(a[:,:,3]*alpha).astype(np.uint8)
        a[a[:,:,3]==0,:3]=0
    return Image.fromarray(a,"RGBA")

def cleanup_mask(alpha,image,q):
    """Remove only low-confidence pixels that also match the known background."""
    if not q["cleanup"] or q["background"]=="none":return alpha
    a=np.asarray(alpha,dtype=np.float32)
    rgb=np.asarray(image.convert("RGB"),dtype=np.float32)
    key=np.array(G.BACKGROUNDS[q["background"]][0],dtype=np.float32)
    dist=np.max(abs(rgb-key),axis=2)
    # Strong foreground is protected, even in enclosed matching-color regions.
    confidence=np.clip((128-a)/96,0,1)
    similarity=np.clip((18-dist)/12,0,1)
    weight=confidence*similarity*q["cleanup"]/100
    return Image.fromarray(np.rint(a*(1-weight)).astype(np.uint8),"L")

def stabilize(alphas,images,strength):
    # Only repair isolated alpha fluctuations where adjacent RGB agrees.
    if not strength or len(alphas)<3:return alphas
    out=list(alphas)
    for i in range(1,len(alphas)-1):
        a,b,c=[np.asarray(x,dtype=np.float32) for x in alphas[i-1:i+2]]
        x,y,z=[np.asarray(im.convert('RGB'),dtype=np.float32) for im in images[i-1:i+2]]
        stable=(np.max(abs(x-y),axis=2)<12)&(np.max(abs(z-y),axis=2)<12)&(abs(a-c)<24)
        # A stronger setting can also repair uncertain edge alpha, but never
        # propagate over changing RGB or contradictory adjacent masks.
        if strength>50:
            edge=(b>0)&(b<255)&(np.max(abs(x-y),axis=2)<20)&(np.max(abs(z-y),axis=2)<20)&(abs(a-c)<16)
            stable|=edge
        result=np.where(stable,b+(np.median(np.stack([a,b,c]),axis=0)-b)*strength/100,b)
        out[i]=Image.fromarray(np.rint(result).astype(np.uint8),'L')
    return out

def assemble(images,q,doc,root=None):
    q=settings(q);d=F.validate(doc)
    images=list(images)
    if not images or len(images)>F.MAX_FRAMES:raise ValueError("Invalid sampled frame count")
    w,h=images[0].size
    if max(w,h)>2048 or w*h*len(images)>F.MAX_PIXELS or any(im.size!=(w,h) for im in images):raise ValueError("Sampled frames exceed canvas budget")
    if d["locked_frames"]:raise ValueError("Unlock frames before replacing the sequence")
    if q["method"]=="birefnet":
        from . import semantic_alpha
        alphas=semantic_alpha.masks(images,root)
        alphas=stabilize(alphas,images,q["temporal"])
        alphas=[cleanup_mask(alpha,im,q) for im,alpha in zip(images,alphas)]
        frames=[]
        for im,alpha in zip(images,alphas):
            frame=im.convert("RGBA");frame.putalpha(alpha);frames.append(frame)
    elif q["method"]=="none":frames=[im.convert("RGBA") for im in images]
    else:frames=[key_frame(im,q) for im in images]
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

def extract(raw,q,doc,root=None):
    q=settings(q)
    if q["end"]<=q["start"]:raise ValueError("End must follow start")
    if not raw or len(raw)>64_000_000:raise ValueError("Video exceeds 64 MB limit")
    count=math.ceil((q["end"]-q["start"])*q["fps"]/1000)
    if count>F.MAX_FRAMES:raise ValueError("Sample at most 120 frames")
    try:
        import imageio.v2 as imageio
        import imageio_ffmpeg
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
            return assemble(frames,q,doc,root)
        finally:reader.close()
