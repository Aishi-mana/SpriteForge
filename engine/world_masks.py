"""Editable raster gameplay masks and map-space depth hints (CPU only)."""
import hashlib, json, re
from PIL import Image, ImageDraw, ImageChops
from . import world, modular

MODES=("ground","sorted","foreground")
WALK_SOURCES=("trail","ground")
THRESHOLD=128

def default_depth(layer,im):
    role=layer["role"];w,h=im.size
    alpha=im.getchannel("A").point(lambda a:255 if a>=THRESHOLD else 0)
    box=alpha.getbbox() or (0,0,w,h)
    x0,y0,x1,y1=box
    # Estimate base width from the bottom 12% of the visible silhouette.
    band=max(1,round((y1-y0)*.12))
    base=alpha.crop((x0,max(y0,y1-band),x1,y1)).getbbox()
    bx0,bx1=(x0+base[0],x0+base[2]) if base else (x0,x1)
    width=max(1,bx1-bx0)
    solid=role in ("objects","foliage")
    mode="sorted" if solid else "foreground" if role=="foreground" else "ground"
    rx=max(1,round(width*(.42 if role=="objects" else .35))) if solid else 0
    ry=max(1,round(rx*.45)) if solid else 0
    return dict(mode=mode,anchor=[min(w-1,(bx0+bx1)//2),max(0,y1-1)],
                footprint=[rx,ry],solid=solid,occludes=role in ("objects","foliage","foreground"))

def depth(value,layer,im):
    if value is None:return default_depth(layer,im)
    if not isinstance(value,dict):raise ValueError("Invalid depth hint")
    # Avoid rescanning large plates when a complete saved hint already exists.
    base=value if all(k in value for k in ('mode','anchor','footprint','solid','occludes')) else default_depth(layer,im)
    w,h=im.size
    mode=value.get("mode",base["mode"])
    if mode not in MODES:raise ValueError("Invalid depth mode")
    anchor=value.get("anchor",base["anchor"]);fp=value.get("footprint",base["footprint"])
    if not isinstance(anchor,list) or len(anchor)!=2 or not isinstance(fp,list) or len(fp)!=2:
        raise ValueError("Invalid depth anchor or footprint")
    return dict(mode=mode,anchor=[world.integer(anchor[0],0,w-1,"anchor X"),world.integer(anchor[1],0,h-1,"anchor Y")],
                footprint=[world.integer(fp[0],0,world.MAX_SIDE,"footprint X radius"),world.integer(fp[1],0,world.MAX_SIDE,"footprint Y radius")],
                solid=world.boolean(value.get("solid",base["solid"]),"solid footprint"),
                occludes=world.boolean(value.get("occludes",base["occludes"]),"occlusion hint"))

def settings(value=None):
    if value is None:value={}
    if not isinstance(value,dict):raise ValueError("Invalid gameplay settings")
    source=value.get("walk_source","trail")
    if source not in WALK_SOURCES:raise ValueError("Invalid walkable source")
    return dict(walk_source=source,threshold=world.integer(value.get("threshold",128),1,255,"alpha threshold"))

def metadata(value):
    c=settings(value)
    sig=value.get("signature","")
    if not isinstance(sig,str) or (sig and not re.fullmatch(r"[a-f0-9]{64}",sig)):
        raise ValueError("Invalid gameplay signature")
    return dict(c,signature=sig)

def signature(d,c):
    """Fingerprint relevant visual inputs, not mask display flags or project metadata."""
    h=hashlib.sha256(json.dumps([d["width"],d["height"],settings(c)],sort_keys=True).encode())
    for l in d["layers"]:
        if l["role"] in world.MASKS:continue
        info={k:l[k] for k in ("id","role","x","y","visible","opacity","depth")}
        h.update(json.dumps(info,sort_keys=True).encode());h.update(l["image"].encode())
    return h.hexdigest()

def anchor(layer):
    x,y=layer["depth"]["anchor"]
    return layer["x"]+x,layer["y"]+y

def depth_order(layer,index=0):
    mode=layer["depth"]["mode"]
    return (MODES.index(mode),anchor(layer)[1] if mode=="sorted" else 0,index)

def _place_max(target,mask,x,y):
    x0,y0=max(0,x),max(0,y);x1,y1=min(target.width,x+mask.width),min(target.height,y+mask.height)
    if x1<=x0 or y1<=y0:return
    region=mask.crop((x0-x,y0-y,x1-x,y1-y))
    target.paste(ImageChops.lighter(target.crop((x0,y0,x1,y1)),region),(x0,y0))

def _binary(im,threshold):
    return im.getchannel("A").point([255 if a>=threshold else 0 for a in range(256)])

def _rgba(mask):
    im=Image.new("RGBA",mask.size,(255,255,255,0));im.putalpha(mask);return im

def effective(value):
    """Mask visibility/opacity is editor-only; collision always wins over walkable."""
    d,images=world.validate(value);size=(d["width"],d["height"])
    result={r:Image.new("L",size) for r in world.MASKS}
    has_walk=False
    for l in d["layers"]:
        if l["role"] not in world.MASKS:continue
        if l["role"]=="walkable":has_walk=True
        result[l["role"]]=ImageChops.lighter(result[l["role"]],_binary(images[l["id"]],THRESHOLD))
    result["walkable"]=ImageChops.subtract(result["walkable"],result["collision"])
    return result,has_walk

def inspect(value):
    d,_=world.validate(value);c=d.get("gameplay")
    masks,has_walk=effective(d);x,y=d["spawn"];size=d["width"]*d["height"]
    auto={l["role"] for l in d["layers"] if l.get("generated_mask")}
    stale=bool(c and (c["signature"]!=signature(d,c) or auto!=set(world.MASKS)))
    return dict(stale=stale,generated=bool(c),has_walkable=has_walk,
                spawn_blocked=bool(masks["collision"].getpixel((x,y))),
                spawn_walkable=bool(masks["walkable"].getpixel((x,y))) if has_walk else None,
                walkable_pixels=masks["walkable"].histogram()[255],collision_pixels=masks["collision"].histogram()[255],
                occlusion_pixels=masks["occlusion"].histogram()[255],total_pixels=size)

def generate(value,options=None):
    d,images=world.validate(value);c=settings(options if options is not None else d.get("gameplay"))
    keep=[]
    for l in d["layers"]:
        if l.get("generated_mask"):
            if l["locked"]:raise ValueError("Unlock generated masks before rebuilding")
        else:keep.append(l)
    if len(keep)+3>world.MAX_LAYERS:raise ValueError("Three free layer slots required for generated masks")
    size=(d["width"],d["height"]);collision=Image.new("L",size);walk=Image.new("L",size);occlusion=Image.new("L",size)
    paint=ImageDraw.Draw(collision);found=False
    walk_role="ground_detail" if c["walk_source"]=="trail" else "ground"
    for l in keep:
        if l["role"] in world.MASKS or not l["visible"] or not l["opacity"]:continue
        im=images[l["id"]];hint=l["depth"]
        if l["role"]==walk_role:
            _place_max(walk,_binary(im,c["threshold"]),l["x"],l["y"]);found=True
        x,y=anchor(l);rx,ry=hint["footprint"]
        if hint["solid"] and rx and ry:
            paint.ellipse((x-rx,y-ry,x+rx,y+ry),fill=255)
        if hint["occludes"]:
            alpha=_binary(im,c["threshold"])
            if hint["mode"]=="sorted":
                # Above ground-contact zone, not a collision silhouette.
                ImageDraw.Draw(alpha).rectangle((0,max(0,hint["anchor"][1]-ry),im.width,im.height),fill=0)
            _place_max(occlusion,alpha,l["x"],l["y"])
    if not found or not walk.getbbox():raise ValueError("No visible walkable source; choose trail/ground with visible alpha")
    walk=ImageChops.subtract(walk,collision)
    ids={l["id"] for l in keep}
    for role,mask in (("collision",collision),("walkable",walk),("occlusion",occlusion)):
        key="auto_"+role;i=2
        while key in ids:key="auto_"+role+"_"+str(i);i+=1
        ids.add(key)
        keep.append(dict(id=key,name="Suggested "+role,role=role,image=modular.png_uri(_rgba(mask)),
                         x=0,y=0,visible=True,locked=False,opacity=100,generated_mask=True))
    result=world.validate({**d,"layers":keep,"gameplay":{**c,"signature":signature(d,c)}})[0]
    return result,inspect(result)
