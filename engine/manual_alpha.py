"""Manual alpha correction on a selected frame; source RGB is authoritative."""
import base64,io
import numpy as np
from PIL import Image
from . import world,full_frame as F

def apply(doc,options):
    d=F.validate(doc)
    if not isinstance(options,dict) or not d["frames"]:raise ValueError("Select a frame")
    n=world.integer
    i=n(options.get("index"),0,len(d["frames"])-1,"frame index")
    if i in d["locked_frames"]:raise ValueError("Unlock this frame before editing")
    mode=options.get("mode")
    if mode not in ("erase","restore"):raise ValueError("Invalid brush mode")
    radius=n(options.get("radius",12),1,128,"brush radius")
    strength=n(options.get("strength",100),1,100,"brush strength")
    points=options.get("points")
    if not isinstance(points,list) or not 1<=len(points)<=1024:raise ValueError("Invalid brush path")
    w,h=d["width"],d["height"]
    coords=[]
    for point in points:
        if not isinstance(point,list) or len(point)!=2:raise ValueError("Invalid brush point")
        coords.append((n(point[0],0,w-1,"brush X"),n(point[1],0,h-1,"brush Y")))
    im=world.image(d["frames"][i]).convert("RGBA")
    source=options.get("source")
    if mode=="restore":
        if not isinstance(source,str) or len(source)>F.MAX_ENCODED:raise ValueError("Import the original unmasked frame to restore artwork")
        original=world.image(source).convert("RGBA")
        if original.size!=im.size:raise ValueError("Original frame must match the canvas exactly")
    a=np.array(im);coverage=np.zeros((h,w),dtype=np.float32)
    # Draw continuous stroke via distance to each segment, clipped to its bounding box.
    budget=0
    for (x0,y0),(x1,y1) in zip(coords,coords[1:]+[coords[-1]]):
        l=max(0,min(x0,x1)-radius);r=min(w,max(x0,x1)+radius+1)
        t=max(0,min(y0,y1)-radius);b=min(h,max(y0,y1)+radius+1)
        budget+=(r-l)*(b-t)
        if budget>40_000_000:raise ValueError("Brush stroke too large; use shorter strokes")
        yy,xx=np.ogrid[t:b,l:r]
        dx=x1-x0;dy=y1-y0
        u=np.clip(((xx-x0)*dx+(yy-y0)*dy)/max(1,dx*dx+dy*dy),0,1)
        dist=np.sqrt((xx-x0-u*dx)**2+(yy-y0-u*dy)**2)
        np.maximum(coverage[t:b,l:r],np.clip(radius-dist,0,1),out=coverage[t:b,l:r])
    weight=coverage*strength/100
    old=a[:,:,3].astype(np.float32)
    if mode=="erase":a[:,:,3]=np.rint(old*(1-weight)).astype(np.uint8)
    else:
        src=np.asarray(original)
        target=np.maximum(old,src[:,:,3])
        new=np.rint(old+(target-old)*weight).astype(np.uint8)
        changed=new>old
        a[changed,:3]=src[changed,:3]
        a[:,:,3]=new
    buf=io.BytesIO();Image.fromarray(a,"RGBA").save(buf,format="PNG")
    frames=list(d["frames"]);frames[i]="data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode()
    return F.validate({**d,"frames":frames})
