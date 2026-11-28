"""Small torso-only warp of a transparent reference; no AI redraw."""
import base64,io,math
import numpy as np
from scipy.ndimage import map_coordinates
from PIL import Image
from . import full_frame as F,world

def generate(doc,options):
    d=F.validate(doc)
    if d["locked_frames"]:raise ValueError("Unlock frames before replacement")
    if not d["reference"]:raise ValueError("Choose transparent character reference")
    if not isinstance(options,dict):raise ValueError("Invalid idle options")
    n=world.integer
    count=n(options.get("frames",32),8,97,"idle frames")
    fps=n(options.get("fps",16),8,30,"idle FPS")
    amplitude=n(options.get("amplitude",1),0,4,"breathing pixels")
    im=world.image(d["reference"]).convert("RGBA")
    if im.getchannel("A").getextrema()[0]==255:raise ValueError("Controlled idle requires a transparent reference")
    if not im.getchannel("A").getbbox():raise ValueError("Reference is empty")
    w,h=im.size
    if w*h*count>F.MAX_PIXELS:raise ValueError("Reduce reference size or frame count")
    if any(v["frames"] for v in d["directions"].values()) and (w,h,fps)!=(d["width"],d["height"],d["fps"]):raise ValueError("Idle must match directional canvas and FPS")
    x0,y0,x1,y1=im.getchannel("A").getbbox()
    y,x=np.mgrid[:h,:w].astype(np.float32)
    v=(y-y0)/max(1,y1-y0);u=(x-(x0+x1-1)/2)/max(1,(x1-x0)/2)
    # Default chibi torso band; zero displacement in upper head and lower feet.
    band=np.sin(np.pi*np.clip((v-.43)/.32,0,1))**2
    band[(v<=.43)|(v>=.75)]=0
    weight=band*np.maximum(0,1-u*u)**2
    a=np.asarray(im,dtype=np.float32)/255
    prem=a.copy();prem[:,:,:3]*=prem[:,:,3:4]
    out=[]
    for i in range(count):
        phase=(1-math.cos(2*math.pi*i/count))/2
        if not amplitude or not i:
            frame=im
        else:
            coords=[y+amplitude*phase*weight,x]
            warped=np.stack([map_coordinates(prem[:,:,c],coords,order=1,mode="constant",cval=0) for c in range(4)],axis=2)
            alpha=warped[:,:,3:4]
            rgb=np.divide(warped[:,:,:3],alpha,out=np.zeros_like(warped[:,:,:3]),where=alpha>1e-6)
            rgba=np.rint(np.clip(np.concatenate([rgb,alpha],axis=2),0,1)*255).astype(np.uint8)
            rgba[weight==0]=np.asarray(im)[weight==0]
            frame=Image.fromarray(rgba,"RGBA")
        b=io.BytesIO();frame.save(b,"PNG")
        out.append("data:image/png;base64,"+base64.b64encode(b.getvalue()).decode())
        if sum(map(len,out))>F.MAX_ENCODED:raise ValueError("Idle exceeds artwork budget")
    return F.validate({**d,"width":w,"height":h,"pivot":[w//2,y1-1],"fps":fps,"loop":True,"frames":out,"keyframes":[],"locked_frames":[],"combat":[]})
