"""Local silent video editing, preserving source bytes and explicit sampling."""
import math,tempfile
from pathlib import Path
from PIL import Image,ImageOps
from . import world,visual_motion

def sampling(start,end,fps,source_fps):
    if end<=start:raise ValueError("End must follow start")
    count=math.ceil((end-start)*fps/1000)
    if count>120:raise ValueError("Sample at most 120 frames")
    return [math.floor((start/1000+i/fps)*source_fps+1e-7) for i in range(count)]

def edit(raw,body):
    if not raw or len(raw)>64_000_000 or raw[4:8]!=b"ftyp":raise ValueError("Choose an MP4 under 64 MB")
    n=world.integer
    start=n(body.get("start",0),0,60000,"start ms")
    end=n(body.get("end",1000),1,60000,"end ms")
    fps=n(body.get("fps",12),1,30,"FPS")
    mode=body.get("mode","trim")
    if mode not in ("trim","reverse","guide"):raise ValueError("Invalid video mode")
    size=n(body.get("size",384),256,768,"guide size")
    if mode=="guide" and (size%16 or fps<8):raise ValueError("Guide requires divisible-by-16 size and 8–30 FPS")
    import imageio.v2 as imageio
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/"source.mp4";path.write_bytes(raw)
        reader=imageio.get_reader(str(path),format="FFMPEG")
        try:
            meta=reader.get_meta_data();sf=float(meta["fps"]);w,h=meta["size"]
            if not math.isfinite(sf) or not 0<sf<=120 or min(w,h)<1 or max(w,h)>2048:raise ValueError("Invalid video dimensions or FPS")
            indices=sampling(start,end,fps,sf)
            if w*h*len(indices)>24_000_000:raise ValueError("Video exceeds sampling budget")
            frames=[]
            for i in indices:
                try:im=Image.fromarray(reader.get_data(i)).convert("RGB")
                except IndexError:raise ValueError("Selected range exceeds source duration")
                if mode=="guide":im=ImageOps.pad(im,(size,size),method=Image.Resampling.BILINEAR,color=(0,0,0))
                frames.append(im)
        finally:reader.close()
        if mode=="reverse":frames.reverse()
        if mode=="guide":
            count=max(9,1+4*math.ceil((len(frames)-1)/4))
            if count>97 or size*size*count>24_000_000:raise ValueError("Guide exceeds Wan frame budget; shorten range")
            frames.extend([frames[-1]]*(count-len(frames)))
        else:
            # H264 yuv420p requires even dimensions; pad without stretching.
            frames=[ImageOps.expand(im,(0,0,im.width%2,im.height%2),fill=(0,0,0)) for im in frames]
        return visual_motion.encode(frames,fps,Path(tmp)/"edited.mp4")
