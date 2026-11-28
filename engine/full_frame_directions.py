"""Directional snapshots and conservative loop seam tools."""
import base64, io
import numpy as np
from PIL import Image
from . import full_frame as F, world

DIRECTIONS=("N","NE","E","SE","S","SW","W","NW")
FIELDS=("combat","frames","reference","keyframes","locked_frames","guidance","prompt")
SHARED=("width","height","pivot","fps","pixel","loop")

def validate_library(value,result):
    mode=value.get("direction_mode",8)
    if type(mode) is not int or mode not in (4,8):raise ValueError("Invalid direction mode")
    active=value.get("direction","S")
    allowed=DIRECTIONS if mode==8 else DIRECTIONS[::2]
    if active not in allowed:raise ValueError("Invalid direction")
    library=value.get("directions",{})
    if not isinstance(library,dict) or any(k not in allowed or k==active for k in library):raise ValueError("Invalid directional library")
    out={};total=sum(map(len,result["frames"]))+len(result["reference"] or "")
    pixels=result["width"]*result["height"]*len(result["frames"])
    for key,clip in library.items():
        if not isinstance(clip,dict) or any(k not in FIELDS for k in clip):raise ValueError("Invalid directional clip")
        clean=F.validate({**{k:result[k] for k in SHARED},**clip})
        out[key]={k:clean[k] for k in FIELDS}
        total+=sum(map(len,clean["frames"]))+len(clean["reference"] or "")
        pixels+=result["width"]*result["height"]*len(clean["frames"])
        if clean["reference"]:
            im=world.image(clean["reference"]);pixels+=im.width*im.height
    if result["reference"]:
        im=world.image(result["reference"]);pixels+=im.width*im.height
    if total>F.MAX_ENCODED or pixels>F.MAX_PIXELS:raise ValueError("Directional library exceeds artwork budget")
    return {**result,"direction_mode":mode,"direction":active,"directions":out}

def switch(doc,target):
    d=F.validate(doc)
    allowed=DIRECTIONS if d["direction_mode"]==8 else DIRECTIONS[::2]
    if target not in allowed:raise ValueError("Invalid direction")
    if target==d["direction"]:return d
    library=dict(d["directions"])
    library[d["direction"]]={k:d[k] for k in FIELDS}
    clip=library.pop(target,{"combat":[],"frames":[],"reference":None,"keyframes":[],"locked_frames":[],"guidance":d["guidance"],"prompt":d["prompt"]})
    return F.validate({**d,**clip,"direction":target,"directions":library})

def seam(doc):
    d=F.validate(doc)
    if len(d["frames"])<2:raise ValueError("At least two frames required")
    a,b=[np.array(world.image(s),dtype=np.float32)/255 for s in (d["frames"][0],d["frames"][-1])]
    def premul(x):return np.concatenate([x[:,:,:3]*x[:,:,3:4],x[:,:,3:4]],axis=2)
    return {"difference":round(float(np.mean(np.abs(premul(a)-premul(b))))*100,3),
            "alpha_difference":round(float(np.mean(np.abs(a[:,:,3]-b[:,:,3])))*100,3)}

def loop_edit(doc,mode,count=2):
    d=F.validate(doc);frames=d["frames"]
    if len(frames)<2:raise ValueError("At least two frames required")
    if mode=="pingpong":extra=frames[-2:0:-1]
    elif mode=="bridge":
        from . import full_frame_interpolation as I
        count=world.integer(count,1,8,"bridge frames")
        a,b=[np.array(world.image(s)) for s in (frames[-1],frames[0])]
        extra=[]
        for k in range(1,count+1):
            buf=io.BytesIO();Image.fromarray(I.blend(a,b,k/(count+1)),"RGBA").save(buf,"PNG")
            extra.append("data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode())
    else:raise ValueError("Invalid loop operation")
    return F.validate({**d,"frames":frames+extra,"loop":True})
