"""Versioned raster world blockout, independent of character and tile grids."""
import base64, binascii, io, re
from PIL import Image
from . import modular

MAX_SIDE=3072
MAX_CANVAS_PIXELS=6_000_000
MAX_SOURCE_PIXELS=24_000_000
MAX_ENCODED=48_000_000
MAX_LAYERS=24
ROLES=("background","ground","ground_detail","objects","foliage","foreground","shadow","lighting","collision","walkable","occlusion")
MASKS=("collision","walkable","occlusion")
VIEWS=("quarter","top_down","side","isometric")
STYLES=("anime","hd2d","painted","pixel","custom")

def integer(value,lo,hi,name):
    return modular.integer(value,lo,hi,name)

def label(value,name,limit=60,empty=False):
    if not isinstance(value,str) or len(value)>limit or (not empty and not value.strip()):
        raise ValueError("Invalid "+name)
    return value.strip()

def boolean(value,name):
    if not isinstance(value,bool):raise ValueError("Invalid "+name)
    return value

def image(value):
    if not isinstance(value,str) or len(value)>MAX_ENCODED or not value.startswith("data:image/png;base64,"):
        raise ValueError("Expected bounded PNG layer")
    try:
        raw=base64.b64decode(value.split(",",1)[1],validate=True)
        with Image.open(io.BytesIO(raw),formats=["PNG"]) as im:
            if max(im.size)>MAX_SIDE or im.width*im.height>MAX_CANVAS_PIXELS or getattr(im,"n_frames",1)!=1:
                raise ValueError("Layer exceeds image dimensions or is animated")
            return im.convert("RGBA")
    except (OSError,binascii.Error,Image.DecompressionBombError) as exc:
        raise ValueError("Invalid layer PNG") from exc

def default():
    return dict(version=1,name="New world",width=1280,height=720,view="quarter",style="anime",
                prompt="",pixel=False,spawn=[640,540],layers=[])

def validate(value):
    if not isinstance(value,dict) or type(value.get("version",1)) is not int or value.get("version",1)!=1:
        raise ValueError("Invalid world project version")
    w=integer(value.get("width",1280),64,MAX_SIDE,"map width")
    h=integer(value.get("height",720),64,MAX_SIDE,"map height")
    if w*h>MAX_CANVAS_PIXELS:raise ValueError("Map exceeds six million pixels")
    view=value.get("view","quarter");style=value.get("style","anime")
    if view not in VIEWS or style not in STYLES:raise ValueError("Invalid map view or style")
    spawn=value.get("spawn",[w//2,3*h//4])
    if not isinstance(spawn,list) or len(spawn)!=2:raise ValueError("Invalid spawn point")
    spawn=[integer(spawn[0],0,w-1,"spawn X"),integer(spawn[1],0,h-1,"spawn Y")]
    layers=value.get("layers",[])
    if not isinstance(layers,list) or len(layers)>MAX_LAYERS:raise ValueError("World supports up to 24 layers")
    if any(not isinstance(l,dict) or not isinstance(l.get("image"),str) for l in layers):
        raise ValueError("Invalid map layer")
    if sum(len(l["image"]) for l in layers)>MAX_ENCODED:raise ValueError("World exceeds 48 MB encoded layer budget")
    out=[];decoded={};pixels=0;ids=set()
    for l in layers:
        key=l.get("id");role=l.get("role","objects")
        if not isinstance(key,str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}",key) or key in ids:
            raise ValueError("Invalid or duplicate map layer ID")
        if role not in ROLES:raise ValueError("Invalid map layer role")
        ids.add(key)
        im=image(l["image"]);pixels+=im.width*im.height
        if pixels>MAX_SOURCE_PIXELS:raise ValueError("World exceeds 24 million source pixels")
        x=integer(l.get("x",0),-MAX_SIDE,MAX_SIDE,"layer X")
        y=integer(l.get("y",0),-MAX_SIDE,MAX_SIDE,"layer Y")
        # Masks have a single map-space alpha coordinate system, independent of visual placement.
        if role in MASKS and (im.size!=(w,h) or x or y):
            raise ValueError("Gameplay masks must match the map dimensions and origin")
        out.append(dict(id=key,name=label(l.get("name",role),"layer name"),role=role,image=l["image"],x=x,y=y,
                        opacity=integer(l.get("opacity",100),0,100,"layer opacity"),
                        visible=boolean(l.get("visible",True),"layer visibility"),locked=boolean(l.get("locked",False),"layer lock")))
        decoded[key]=im
    result=dict(version=1,name=label(value.get("name","New world"),"world name"),width=w,height=h,
                view=view,style=style,prompt=label(value.get("prompt",""),"map prompt",2000,True),
                pixel=boolean(value.get("pixel",style=="pixel"),"map sampling"),spawn=spawn,layers=out)
    if value.get("blockout") is not None:
        from . import world_blockout
        result["blockout"]=world_blockout.settings(value["blockout"])
    if value.get("style_profile") is not None:
        from . import world_style
        result["style_profile"]=world_style.validate(value["style_profile"])
    return result,decoded

def render(value,show_masks=False):
    if not isinstance(show_masks,bool):raise ValueError("Invalid mask display option")
    world,images=validate(value)
    out=Image.new("RGBA",(world["width"],world["height"]))
    def place(im,x,y):
        x0,y0=max(0,x),max(0,y)
        x1,y1=min(out.width,x+im.width),min(out.height,y+im.height)
        if x1>x0 and y1>y0:out.alpha_composite(im.crop((x0-x,y0-y,x1-x,y1-y)),(x0,y0))
    for mask_pass in (False,True):
        if mask_pass and not show_masks:break
        for l in world["layers"]:
            is_mask=l["role"] in MASKS
            if is_mask!=mask_pass or not l["visible"] or not l["opacity"]:continue
            im=images[l["id"]]
            if is_mask:
                rgb={"collision":(255,64,80),"walkable":(50,220,115),"occlusion":(160,100,255)}[l["role"]]
                tinted=Image.new("RGBA",im.size,(*rgb,0))
                tinted.putalpha(im.getchannel("A").point([round(i*l["opacity"]*.0045) for i in range(256)]))
                im=tinted
            elif l["opacity"]!=100:
                im=im.copy();im.putalpha(im.getchannel("A").point([round(i*l["opacity"]/100) for i in range(256)]))
            place(im,l["x"],l["y"])
    return out,world
