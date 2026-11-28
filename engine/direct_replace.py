"""Prepare visual motion transfer and restore generated candidates to source timing/canvas."""
import math
from PIL import Image, ImageOps
from . import world, direct_motion as M, full_frame as F, modular

def plan(body):
    d,first,last=M.source(body)
    if any(first<=i<=last for i in d["locked_frames"]):raise ValueError("Selected range includes locked frames")
    fps=max(8,min(30,d["fps"]))
    # Cover the timestamp of every original frame; never truncate the selected tail.
    needed=math.ceil((last-first)*fps/d["fps"])+1
    count=max(9,1+4*math.ceil((needed-1)/4))
    size=world.integer(body.get("size",384),256,768,"guide size")
    if size%16 or count>97 or size*size*count>24_000_000:raise ValueError("Selected range is too long for this guide size; choose a shorter range or smaller size")
    reference=body.get("reference")
    world.image(reference)
    kind=body.get("kind","silhouette")
    if kind not in ("silhouette","edges","artwork"):raise ValueError("Invalid guide kind")
    return dict(first=first,last=last,width=size,height=size,fps=fps,frames=count,kind=kind,source_fps=d["fps"],source_size=[d["width"],d["height"]])

def restore(body):
    d,first,last=M.source(body)
    if any(first<=i<=last for i in d["locked_frames"]):raise ValueError("Selected range includes locked frames")
    generated=F.validate(body.get("generated"))
    if not generated["frames"]:raise ValueError("No generated frames")
    fps=generated["fps"]
    indices=[round((i-first)*fps/d["fps"]) for i in range(first,last+1)]
    if indices[-1]>=len(generated["frames"]):raise ValueError("Generated sequence is shorter than original range; do not silently repeat missing frames")
    w,h=d["width"],d["height"]
    gw,gh=generated["width"],generated["height"]
    # Reverse the guide's aspect-ratio padding, keeping its spatial coordinates.
    factor=min(gw/w,gh/h)
    cw,ch=max(1,round(w*factor)),max(1,round(h*factor))
    left,top=(gw-cw)//2,(gh-ch)//2
    out=[];cache={};total=0
    for j in indices:
        if j not in cache:
            im=world.image(generated["frames"][j])
            im=im.crop((left,top,left+cw,top+ch)).resize((w,h),Image.Resampling.NEAREST if d["pixel"] else Image.Resampling.LANCZOS)
            if not im.getchannel("A").getbbox():raise ValueError("Replacement contains an empty frame")
            cache[j]=modular.png_uri(im)
        uri=cache[j];total+=len(uri)
        if total>F.MAX_ENCODED:raise ValueError("Replacement exceeds artwork budget")
        out.append(uri)
    # Validate the entire eventual document, including unchanged directions and metadata.
    frames=d["frames"][:];frames[first:last+1]=out
    F.validate({**d,"frames":frames})
    return dict(first=first,last=last,frames=out,source_indices=indices,fps=d["fps"],pivot=d["pivot"])
