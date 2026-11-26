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
ATTACHMENTS = ("auto","root","torso","head","l_arm_u","l_arm_l","r_arm_u","r_arm_l","l_leg_u","l_leg_l","r_leg_u","r_leg_l")
DEFAULT_ATTACH = {"hair_back":"head","hair_front":"head","outfit":"auto","footwear":"auto","accessory":"torso","other":"root","body":"auto"}

def integer(v, lo, hi, name):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or int(v)!=v or not lo<=v<=hi:
        raise ValueError(f"Invalid {name}: expected integer {lo}–{hi}")
    return int(v)

def weight_settings(value=None):
    """Two-bone skinning with bounded normalized brush strokes in rest-canvas space."""
    if value is None:value={}
    if not isinstance(value,dict):raise ValueError("Invalid manual weights")
    a,b=value.get("bone_a","torso"),value.get("bone_b","r_arm_l")
    if a not in ATTACHMENTS[1:] or b not in ATTACHMENTS[1:] or a==b:
        raise ValueError("Choose two distinct attachment bones")
    def number(v,lo,hi):
        if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or not lo<=v<=hi:
            raise ValueError("Invalid weight brush value")
        return float(v)
    strokes=value.get("strokes",[])
    if not isinstance(strokes,list) or len(strokes)>192:raise ValueError("At most 192 weight brush stamps per layer")
    out=[]
    for s in strokes:
        if not isinstance(s,list) or len(s)!=4:raise ValueError("Invalid brush stamp")
        out.append([number(s[0],0,1),number(s[1],0,1),number(s[2],.01,.75),number(s[3],0,1)])
    return {"bone_a":a,"bone_b":b,"base":number(value.get("base",0),0,1),"strokes":out}


def occlusion_settings(value=None):
    if value is None:value={}
    if not isinstance(value,dict):raise ValueError("Invalid layer occlusion")
    depth=value.get("depth","stack")
    if depth not in ("stack","behind","front"):raise ValueError("Unknown layer depth")
    bones=value.get("bones",[])
    if not isinstance(bones,list) or len(bones)>10 or any(b not in ATTACHMENTS[2:] for b in bones):
        raise ValueError("Invalid body occlusion bones")
    return {"depth":depth,"bones":[b for b in ATTACHMENTS[2:] if b in bones]}


def layer_order(layers,indices,body):
    """Explicit behind/front overrides stack position; preserve order within passes."""
    def behind(i):
        d=layers[i].get("occlusion",{}).get("depth","stack")
        return d=="behind" or (d=="stack" and i<body)
    return [i for i in sorted(indices) if behind(i)]+[body]+[i for i in sorted(indices) if not behind(i)]


def motion_settings(value=None):
    """Opt-in per-layer deformation. Legacy recipes retain rigid behavior."""
    if value is None:value={}
    if not isinstance(value,dict):raise ValueError("Invalid layer motion settings")
    mode=value.get("mode","rigid")
    if mode not in ("rigid","soft","spring","weighted"):raise ValueError("Unknown layer motion mode")
    def number(k,default,lo,hi):
        v=value.get(k,default)
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError("Invalid motion "+k)
        return float(v)
    preset=value.get("preset","cape")
    if preset not in ("cape","hair","tail"):raise ValueError("Invalid spring preset")
    out=dict(mode=mode,softness=number("softness",50,0,100),preset=preset,
                segments=integer(value.get("segments",3),1,6,"spring segments"),
                anchor_x=number("anchor_x",.5,0,1),anchor_y=number("anchor_y",.05,0,1),
                flutter=number("flutter",1,0,2),stiffness=number("stiffness",1,.4,2),
                damping=number("damping",.35,.1,.9))
    if mode=="weighted":out["weights"]=weight_settings(value.get("weights"))
    return out


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
        attachment=l.get("attachment",DEFAULT_ATTACH[category])
        if attachment not in ATTACHMENTS:raise ValueError("Invalid bone attachment")
        motion=motion_settings(l.get("motion"))
        if motion["mode"] in ("soft","weighted") and attachment!="auto":raise ValueError("Soft/manual garment motion requires Auto split attachment")
        if motion["mode"]=="spring" and attachment=="auto":raise ValueError("Spring motion requires a single attachment bone or root")
        row=dict(name=name.strip(),category=category,image=png_uri(im),attachment=attachment,motion=motion,
                 x=integer(l.get("x",0),-2048,2048,"X"),y=integer(l.get("y",0),-2048,2048,"Y"),
                 scale=integer(l.get("scale",100),10,200,"scale"),
                 opacity=integer(l.get("opacity",100),0,100,"opacity"),visible=visible,flip=flip)
        if l.get("occlusion") is not None:
            row["occlusion"]=occlusion_settings(l["occlusion"])
        if category=="body" and motion["mode"]=="weighted":raise ValueError("Manual two-bone weights apply to non-body layers")
        out.append(row);images.append(im)
    if sum(len(l["image"]) for l in out)>MAX_ENCODED:raise ValueError("Normalized PNG layers exceed 24 MB encoded budget")
    clean=dict(version=1,width=w,height=h,pixel=pixel,layers=out)
    if recipe.get("rig") is not None:
        from . import modular_rig
        clean["rig"]=modular_rig.validate_profile(recipe["rig"])
    return clean,images

def composite(recipe, images):
    canvas=Image.new("RGBA",(recipe["width"],recipe["height"]))
    resample=Image.Resampling.NEAREST if recipe["pixel"] else Image.Resampling.LANCZOS
    layers=recipe["layers"]
    visible=[i for i,l in enumerate(layers) if l["visible"] and l["opacity"]]
    bodies=[i for i in visible if layers[i]["category"]=="body"]
    indices=layer_order(layers,[i for i in visible if i!=bodies[0]],bodies[0]) if len(bodies)==1 else visible
    for i in indices:
        layer,source=layers[i],images[i]
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
