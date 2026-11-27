"""Versioned reusable game UI artwork library and editable layout foundation."""
import re
from . import world, world_style

MAX_ASSETS=32
MAX_COMPONENTS=64
MAX_ENCODED=24_000_000
MAX_SOURCE_PIXELS=12_000_000
ROLES=("panel","frame","button","tab","toggle","slider","icon","slot","bar_track","bar_fill","portrait","dialogue","marker","decoration","custom")
ICON_CATEGORIES=("item","weapon","armor","accessory","consumable","skill","spell","status")
ICON_SIZES=(32,48,64,96,128,256)
STYLES=("anime","hd2d","painted","pixel","custom")
FONTS=("sans","serif","mono")
KINDS=("image","text","rect")

def color(v,name):
    if not isinstance(v,str) or not re.fullmatch(r"#[0-9a-fA-F]{6}",v):
        raise ValueError("Invalid "+name+" color")
    return v.lower()

def key(v,used,name):
    if not isinstance(v,str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}",v) or v in used:
        raise ValueError("Invalid or duplicate "+name+" ID")
    used.add(v)
    return v

def default():
    return dict(version=1,name="New UI theme",width=1280,height=720,style="anime",pixel=False,
                prompt="",palette=[],assets=[],components=[])

def validate(value):
    if not isinstance(value,dict) or type(value.get("version",1)) is not int or value.get("version",1)!=1:
        raise ValueError("Invalid system theme version")
    n=world.integer
    w=n(value.get("width",1280),64,3072,"preview width");h=n(value.get("height",720),64,3072,"preview height")
    if w*h>6_000_000:raise ValueError("Preview exceeds six million pixels")
    style=value.get("style","anime")
    if style not in STYLES:raise ValueError("Invalid theme style")
    palette=value.get("palette",[])
    if not isinstance(palette,list) or len(palette)>8:raise ValueError("Use up to eight palette suggestions")
    palette=list(dict.fromkeys(color(c,"palette") for c in palette))
    assets=value.get("assets",[]);components=value.get("components",[])
    if not isinstance(assets,list) or len(assets)>MAX_ASSETS:raise ValueError("Theme supports up to 32 artwork assets")
    if not isinstance(components,list) or len(components)>MAX_COMPONENTS:raise ValueError("Theme supports up to 64 layout components")
    if any(not isinstance(a,dict) or not isinstance(a.get("image"),str) for a in assets):
        raise ValueError("Invalid UI artwork")
    if sum(len(a["image"]) for a in assets)>MAX_ENCODED:raise ValueError("Theme exceeds 24 MB encoded artwork budget")
    ids=set();clean=[];pixels=0
    for a in assets:
        aid=key(a.get("id"),ids,"asset")
        role=a.get("role","custom")
        if role not in ROLES:raise ValueError("Invalid UI artwork role")
        im=world.image(a["image"]);pixels+=im.width*im.height
        if pixels>MAX_SOURCE_PIXELS:raise ValueError("Theme exceeds 12 million source pixels")
        clean.append(dict(id=aid,name=world.label(a.get("name",role),"asset name"),role=role,
                          image=a["image"],width=im.width,height=im.height))
        if a.get("icon") is not None:
            meta=a["icon"]
            if role!="icon" or not isinstance(meta,dict):raise ValueError("Invalid icon metadata")
            category=meta.get("category")
            if category not in ICON_CATEGORIES:raise ValueError("Invalid icon category")
            size=meta.get("size")
            if type(size) is not int or size not in ICON_SIZES or im.size!=(size,size):raise ValueError("Invalid icon dimensions")
            clean[-1]["icon"]=dict(category=category,size=size,subject=world.label(meta.get("subject"),"icon subject",240))
    used=set();parts=[]
    for c in components:
        if not isinstance(c,dict):raise ValueError("Invalid layout component")
        cid=key(c.get("id"),used,"component");kind=c.get("kind")
        if kind not in KINDS:raise ValueError("Invalid component type")
        part=dict(id=cid,kind=kind,name=world.label(c.get("name",kind),"component name"),
                  x=n(c.get("x",0),-3072,3072,"component X"),y=n(c.get("y",0),-3072,3072,"component Y"),
                  width=n(c.get("width",128),1,3072,"component width"),height=n(c.get("height",48),1,3072,"component height"),
                  visible=world.boolean(c.get("visible",True),"component visibility"),
                  locked=world.boolean(c.get("locked",False),"component lock"),opacity=n(c.get("opacity",100),0,100,"opacity"))
        if kind=="image":
            aid=c.get("asset")
            if not isinstance(aid,str) or aid not in ids:raise ValueError("Component references missing artwork")
            part["asset"]=aid
            if c.get("slice") is not None:
                a=next(a for a in clean if a["id"]==aid)
                margins=c["slice"]
                if not isinstance(margins,dict):raise ValueError("Invalid nine-slice margins")
                margins={k:n(margins.get(k,0),0,a["width"] if k in ("left","right") else a["height"],"slice "+k) for k in ("left","top","right","bottom")}
                if margins["left"]+margins["right"]>=a["width"] or margins["top"]+margins["bottom"]>=a["height"]:
                    raise ValueError("Nine-slice requires a nonempty source center")
                part["slice"]=margins
        elif kind=="text":
            font=c.get("font","sans");align=c.get("align","left")
            if font not in FONTS or align not in ("left","center","right"):raise ValueError("Invalid text style")
            part.update(text=world.label(c.get("text","Label"),"component text",500,True),font=font,align=align,
                        font_size=n(c.get("font_size",20),6,256,"font size"),color=color(c.get("color","#ffffff"),"text"))
        else:
            part.update(color=color(c.get("color","#263449"),"rectangle"),border=color(c.get("border","#9aa9bf"),"border"),
                        border_width=n(c.get("border_width",1),0,32,"border width"))
        if c.get("control") is not None:
            control=c["control"]
            if kind=="text" or not isinstance(control,dict):raise ValueError("Invalid control")
            mode=control.get("mode","button")
            if mode not in ("button","toggle","tab","slider"):raise ValueError("Invalid control mode")
            states=control.get("states",{})
            if not isinstance(states,dict) or any(k not in ("hovered","pressed","selected","disabled") for k in states):raise ValueError("Invalid control states")
            variants={}
            for state,v in states.items():
                if kind=="image":
                    if not isinstance(v,str) or v not in ids:raise ValueError("Missing state artwork")
                    if "slice" in part:
                        a=next(a for a in clean if a["id"]==v)
                        m=part["slice"]
                        if m["left"]+m["right"]>=a["width"] or m["top"]+m["bottom"]>=a["height"]:raise ValueError("State artwork too small for nine-slice")
                else:v=color(v,"state fill")
                variants[state]=v
            part["control"]=dict(mode=mode,enabled=world.boolean(control.get("enabled",True),"control enabled"),selected=world.boolean(control.get("selected",False),"control selected"),states=variants)
        parts.append(part)
    result = dict(version=1,name=world.label(value.get("name","New UI theme"),"theme name"),width=w,height=h,
                style=style,pixel=world.boolean(value.get("pixel",style=="pixel"),"theme sampling"),
                prompt=world.label(value.get("prompt",""),"theme direction",2000,True),palette=palette,assets=clean,components=parts)

    if value.get("style_profile") is not None:
        result["style_profile"] = world_style.validate(value["style_profile"])
    return result
