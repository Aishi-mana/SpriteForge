"""CPU-only non-destructive character layer compositor and portable recipes."""
import base64
import io
import json
import math
import zipfile
from PIL import Image, ImageOps

CATEGORIES = ("hair_back", "body", "outfit", "footwear", "hair_front", "accessory", "other")
MAX_LAYERS = 24
MAX_SOURCE_PIXELS = 16_000_000
MAX_ENCODED = 24_000_000

def integer(v, lo, hi, name):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or int(v)!=v or not lo<=v<=hi:
        raise ValueError(f"Invalid {name}: expected integer {lo}–{hi}")
    return int(v)

def png_uri(im):
    buf=io.BytesIO()
    im.save(buf,"PNG")
    return "data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode("ascii")

def decode(value):
    if not isinstance(value,str) or not value.startswith("data:image/") or ";base64," not in value or len(value)>11_000_000:
        raise ValueError("Invalid or oversized layer image")
    try:
        raw=base64.b64decode(value.split(",",1)[1],validate=True)
        with Image.open(io.BytesIO(raw)) as im:
            if max(im.size)>1024:raise ValueError("Layer image exceeds 1024 px per side")
            return im.convert("RGBA")
    except (OSError,ValueError) as e:
        raise ValueError(f"Cannot read layer image: {e}") from e

def validate(recipe):
    if not isinstance(recipe,dict):raise ValueError("Invalid character recipe")
    w=integer(recipe.get("width",256),16,1024,"canvas width")
    h=integer(recipe.get("height",256),16,1024,"canvas height")
    pixel=recipe.get("pixel",True)
    if not isinstance(pixel,bool):raise ValueError("Invalid sampling mode")
    layers=recipe.get("layers",[])
    if not isinstance(layers,list) or len(layers)>MAX_LAYERS:raise ValueError("At most 24 layers per character")
    if any(not isinstance(l,dict) or not isinstance(l.get("image"),str) for l in layers):raise ValueError("Invalid layer")
    if sum(len(l["image"]) for l in layers)>MAX_ENCODED:raise ValueError("Layer library exceeds 24 MB encoded budget")
    out=[];images=[];total=0
    for l in layers:
        im=decode(l["image"]);total+=im.width*im.height
        if total>MAX_SOURCE_PIXELS:raise ValueError("Layer library exceeds 16 million source pixels")
        name=l.get("name","Layer")
        category=l.get("category","other")
        if not isinstance(name,str) or not name.strip() or len(name)>80 or category not in CATEGORIES:raise ValueError("Invalid layer name/category")
        visible=l.get("visible",True);flip=l.get("flip",False)
        if not isinstance(visible,bool) or not isinstance(flip,bool):raise ValueError("Invalid layer flag")
        row=dict(name=name.strip(),category=category,image=png_uri(im),
                 x=integer(l.get("x",0),-2048,2048,"X"),y=integer(l.get("y",0),-2048,2048,"Y"),
                 scale=integer(l.get("scale",100),10,200,"scale"),
                 opacity=integer(l.get("opacity",100),0,100,"opacity"),visible=visible,flip=flip)
        out.append(row);images.append(im)
    if sum(len(l["image"]) for l in out)>MAX_ENCODED:raise ValueError("Normalized PNG layers exceed 24 MB encoded budget")
    return dict(version=1,width=w,height=h,pixel=pixel,layers=out),images

def composite(recipe, images):
    canvas=Image.new("RGBA",(recipe["width"],recipe["height"]))
    resample=Image.Resampling.NEAREST if recipe["pixel"] else Image.Resampling.LANCZOS
    for layer,source in zip(recipe["layers"],images):
        if not layer["visible"] or not layer["opacity"]:continue
        im=source
        if layer["flip"]:im=ImageOps.mirror(im)
        if layer["scale"]!=100:
            im=im.resize(tuple(max(1,round(s*layer["scale"]/100)) for s in im.size),resample)
        if layer["opacity"]!=100:
            im=im.copy()
            im.putalpha(im.getchannel("A").point(lambda v:round(v*layer["opacity"]/100)))
        x,y=layer["x"],layer["y"]
        l,t=max(0,-x),max(0,-y)
        r,b=min(im.width,canvas.width-x),min(im.height,canvas.height-y)
        if l<r and t<b:
            canvas.alpha_composite(im.crop((l,t,r,b)),(x+l,y+t))
    return canvas

def render(recipe):
    clean,images=validate(recipe)
    return composite(clean,images)

def bundle(recipe):
    clean,images=validate(recipe)
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("recipe.json",json.dumps(clean,ensure_ascii=False,indent=2))
        im=composite(clean,images);b=io.BytesIO();im.save(b,"PNG")
        z.writestr("character.png",b.getvalue())
        manifest={**clean,"layers":[]}
        for i,(layer,source) in enumerate(zip(clean["layers"],images)):
            name=f"layers/{i:02d}_{layer['category']}.png"
            b=io.BytesIO();source.save(b,"PNG");z.writestr(name,b.getvalue())
            manifest["layers"].append({**{k:v for k,v in layer.items() if k!="image"},"file":name})
        z.writestr("manifest.json",json.dumps(manifest,ensure_ascii=False,indent=2))
    return buf.getvalue()
