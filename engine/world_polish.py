"""Non-destructive map polish operations: persistent mask overrides and local artwork edits."""
from PIL import Image, ImageDraw, ImageOps, ImageChops
from . import world, world_masks, world_blockout, world_style, modular

PROP_ROLES=("objects","foliage","foreground")
ROLE_MAP={"background":"background","ground":"ground","ground_detail":"trail","objects":"rock","foliage":"tree","foreground":"foreground"}
MAX_POINTS=1024

def selected(value,key):
    d,images=world.validate(value)
    layer=next((l for l in d["layers"] if l["id"]==key),None)
    if layer is None:raise ValueError("Select a map layer")
    if layer["locked"]:raise ValueError("Unlock selected layer first")
    return d,layer,images[key]

def unique(d,prefix):
    ids={l["id"] for l in d["layers"]}
    i=1
    while prefix+str(i) in ids:i+=1
    return prefix+str(i)

def stroke(value,request):
    d,images=world.validate(value)
    if not isinstance(request,dict):raise ValueError("Invalid mask stroke")
    role=request.get("role");mode=request.get("mode")
    if role not in world.MASKS or mode not in ("add","erase","reset"):raise ValueError("Invalid mask brush")
    radius=world.integer(request.get("radius",16),1,256,"brush radius")
    points=request.get("points")
    if not isinstance(points,list) or not 1<=len(points)<=MAX_POINTS:raise ValueError("Invalid brush points")
    w,h=d["width"],d["height"]
    if any(not isinstance(p,list) or len(p)!=2 for p in points):raise ValueError("Invalid brush point")
    points=[(world.integer(p[0],0,w-1,"brush X"),world.integer(p[1],0,h-1,"brush Y")) for p in points]
    layer=next((l for l in d["layers"] if l["role"]==role and l.get("mask_override")),None)
    if layer is None:
        if mode=="reset":return d
        if len(d["layers"])>=world.MAX_LAYERS:raise ValueError("No free layer slot for mask corrections")
        layer=dict(id=unique(d,"correction_"),name=role.title()+" corrections",role=role,x=0,y=0,
                   visible=True,locked=False,opacity=100,mask_override=True)
        d["layers"].append(layer);im=Image.new("RGBA",(w,h))
    else:
        if layer["locked"]:raise ValueError("Unlock the correction layer before painting")
        im=images[layer["id"]].copy()
    # Alpha=0 leaves suggestions untouched; opaque white adds, opaque black erases.
    color={"add":(255,255,255,255),"erase":(0,0,0,255),"reset":(0,0,0,0)}[mode]
    paint=ImageDraw.Draw(im)
    if len(points)>1:paint.line(points,fill=color,width=radius*2+1,joint="curve")
    for x,y in points:paint.ellipse((x-radius,y-radius,x+radius,y+radius),fill=color)
    layer["image"]=modular.png_uri(im)
    return world.validate(d)[0]

def transform(value,key,request):
    d,l,im=selected(value,key)
    if l["role"] in world.MASKS:raise ValueError("Select a visual layer")
    if not isinstance(request,dict):raise ValueError("Invalid transform")
    action=request.get("action")
    if action=="duplicate":
        if len(d["layers"])>=world.MAX_LAYERS:raise ValueError("No free layer slot")
        copy={**l,"id":unique(d,"copy_"),"name":(l["name"][:55]+" copy"),"x":min(world.MAX_SIDE,l["x"]+12),"y":min(world.MAX_SIDE,l["y"]+12)}
        d["layers"].insert(d["layers"].index(l)+1,copy)
        return world.validate(d)[0],copy["id"]
    if action not in ("scale","mirror"):raise ValueError("Invalid layer transform")
    old=world_masks.anchor(l);p=l["depth"].copy()
    if action=="scale":
        pct=world.integer(request.get("percent",100),25,200,"scale percentage")
        w,h=max(1,round(im.width*pct/100)),max(1,round(im.height*pct/100))
        if max(w,h)>world.MAX_SIDE or w*h>world.MAX_CANVAS_PIXELS:raise ValueError("Scaled layer exceeds image budget")
        sx,sy=w/im.width,h/im.height
        im=im.resize((w,h),Image.Resampling.NEAREST if d["pixel"] else Image.Resampling.LANCZOS)
        p["anchor"]=[min(w-1,round(p["anchor"][0]*sx)),min(h-1,round(p["anchor"][1]*sy))]
        p["footprint"]=[min(world.MAX_SIDE,round(p["footprint"][0]*sx)),min(world.MAX_SIDE,round(p["footprint"][1]*sy))]
    else:
        im=ImageOps.mirror(im);p["anchor"]=[im.width-1-p["anchor"][0],p["anchor"][1]]
    l.update(image=modular.png_uri(im),depth=p,x=old[0]-p["anchor"][0],y=old[1]-p["anchor"][1])
    return world.validate(d)[0],key

def region(value,key,rect=None):
    d,l,im=selected(value,key)
    if l["role"] not in ROLE_MAP:raise ValueError("Choose an environment art layer")
    if rect is None:return d,l,im,(0,0,im.width,im.height)
    if not isinstance(rect,list) or len(rect)!=4:raise ValueError("Invalid map rectangle")
    x,y,w,h=[world.integer(v,0,world.MAX_SIDE,"region coordinate") for v in rect]
    if w<1 or h<1 or x+w>d["width"] or y+h>d["height"]:raise ValueError("Region must be inside map")
    box=(max(0,x-l["x"]),max(0,y-l["y"]),min(im.width,x+w-l["x"]),min(im.height,y+h-l["y"]))
    if box[2]<=box[0] or box[3]<=box[1]:raise ValueError("Region does not intersect selected layer")
    if l["role"] in PROP_ROLES:raise ValueError("Regenerate the entire isolated prop, not part of its silhouette")
    return d,l,im,box

def prompt(value,key,rect,instruction):
    d,l,im,box=region(value,key,rect)
    instruction=world.label(instruction,"regeneration instruction",800)
    role=ROLE_MAP[l["role"]];style=world_blockout.STYLE_TEXT[d["style"]]
    common=", ".join(v for v in (style,d["prompt"],world_style.guidance(d.get("style_profile")),instruction,
         "consistent elevated three-quarter game camera and environment lighting") if v)
    if role in ("rock","tree","foreground"):
        return common+", one isolated complete object, base visible, no scenery or ground plane, generous margins", "world_prop"
    return common+", continuous environmental surface or scenery plate, fills frame, no character, no border", "world_plate"

def replace(value,key,uri,rect=None,feather=8,generated=False):
    d,l,im,box=region(value,key,rect)
    new=world.image(uri)
    feather=world.integer(feather,0,64,"patch feather")
    if not isinstance(generated,bool):raise ValueError("Invalid generation flag")
    sampling=Image.Resampling.NEAREST if d["pixel"] else Image.Resampling.LANCZOS
    if l["role"] in PROP_ROLES:
        # Fit new silhouette inside original canvas; preserve map contact anchor and depth metadata.
        if generated and new.getchannel("A").getextrema()[0]==255:raise ValueError("Generated prop needs transparent background")
        if not new.getchannel("A").getbbox():raise ValueError("Replacement is transparent")
        new=new.crop(new.getchannel("A").getbbox());new.thumbnail(im.size,sampling)
        target=Image.new("RGBA",im.size)
        target.alpha_composite(new,((im.width-new.width)//2,im.height-new.height))
        l["image"]=modular.png_uri(target)
    else:
        x0,y0,x1,y1=box;w,h=x1-x0,y1-y0
        patch=ImageOps.fit(new.convert("RGB"),(w,h),sampling).convert("RGBA")
        old=im.crop(box);patch.putalpha(old.getchannel("A"))
        if rect is not None and feather:
            # Feather strictly inside the rectangle; never change pixels outside it.
            import numpy as np
            yy,xx=np.ogrid[:h,:w]
            edge=np.minimum(np.minimum(xx,w-1-xx),np.minimum(yy,h-1-yy))
            blend=Image.fromarray(np.uint8(np.clip(edge/max(1,feather),0,1)*255))
            patch=Image.composite(patch,old,blend)
        im=im.copy();im.paste(patch,(x0,y0));l["image"]=modular.png_uri(im)
    return world.validate(d)[0]
