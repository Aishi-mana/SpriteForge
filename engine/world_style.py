"""Portable environment art direction inferred from a bounded character reference."""
import re, math
import numpy as np
from PIL import Image
from . import world, modular, alpha_cleanup

CHOICES={"saturation":("muted","balanced","vivid"),"contrast":("soft","balanced","strong"),
         "detail":("simple","balanced","detailed"),"shading":("auto","cel","soft","painted","pixel"),
         "linework":("auto","clean","subtle","bold","none")}
GUIDES={"saturation":{"muted":"restrained saturation","balanced":"balanced saturation","vivid":"rich saturation"},
        "contrast":{"soft":"soft tonal contrast","balanced":"balanced tonal contrast","strong":"strong light-dark contrast"},
        "detail":{"simple":"readable simple shapes","balanced":"moderate visual detail","detailed":"rich controlled detail"},
        "shading":{"auto":"","cel":"clean cel shading","soft":"soft gradient shading","painted":"painterly shading","pixel":"deliberate pixel clusters"},
        "linework":{"auto":"","clean":"refined clean edges and linework","subtle":"subtle outlines","bold":"strong deliberate outlines","none":"no drawn outlines"}}
MAX_REF=1_000_000

def validate(value):
    if value is None:return None
    if not isinstance(value,dict) or type(value.get("version",1)) is not int or value.get("version",1)!=1:
        raise ValueError("Invalid environment style profile")
    out=dict(version=1,name=world.label(value.get("name","Environment style"),"profile name"),
             source=world.label(value.get("source","Manual"),"reference source",100),
             notes=world.label(value.get("notes",""),"style notes",600,True),
             enabled=world.boolean(value.get("enabled",True),"style guidance"),
             accents=world.boolean(value.get("accents",False),"palette accents"),
             image_condition=world.boolean(value.get("image_condition",False),"image conditioning"))
    strength=value.get("strength",.35)
    if isinstance(strength,bool) or not isinstance(strength,(float,int)) or not math.isfinite(strength) or not 0<=strength<=1:
        raise ValueError("Invalid reference strength")
    out["strength"]=float(strength)
    for field,choices in CHOICES.items():
        v=value.get(field,"balanced" if field in ("saturation","contrast","detail") else "auto")
        if v not in choices:raise ValueError("Invalid style "+field)
        out[field]=v
    palette=value.get("palette",[])
    if not isinstance(palette,list) or len(palette)>8 or any(not isinstance(c,str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}",c) for c in palette):
        raise ValueError("Use up to eight hex colors")
    out["palette"]=list(dict.fromkeys(c.lower() for c in palette))
    ref=value.get("reference")
    if ref is not None:
        if not isinstance(ref,str) or len(ref)>MAX_REF:raise ValueError("Style thumbnail exceeds budget")
        im=world.image(ref)
        if max(im.size)>256 or not im.getchannel("A").getbbox():raise ValueError("Invalid style thumbnail")
    if out["image_condition"] and ref is None:raise ValueError("Image conditioning requires a reference")
    out["reference"]=ref
    metrics=value.get("metrics")
    if metrics is not None:
        if not isinstance(metrics,dict):raise ValueError("Invalid style metrics")
        out["metrics"]={k:world.integer(metrics.get(k),0,100,k) for k in ("saturation","contrast","edge_density")}
    return out

def analyze(uri,name="Environment style",source="Character reference",remove_bg=False,pixel=False):
    im=world.image(uri)
    if not isinstance(remove_bg,bool) or not isinstance(pixel,bool):raise ValueError("Invalid style analysis option")
    if remove_bg and im.getchannel("A").getextrema()==(255,255):
        im,_=alpha_cleanup.clean(im,30,mode="edge",soft=False)
    box=im.getchannel("A").getbbox()
    if not box:raise ValueError("Reference has no visible pixels")
    im=im.crop(box)
    im.thumbnail((256,256),Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS)
    a=np.asarray(im);valid=a[:,:,3]>=128
    rgb=a[:,:,:3].astype(np.float32)/255
    colors=rgb[valid]
    if len(colors)<4:raise ValueError("Reference has too few visible pixels")
    hi=colors.max(axis=1);lo=colors.min(axis=1)
    sat=float(np.mean((hi-lo)/np.maximum(hi,1e-6)))
    luminance=rgb@np.array([.2126,.7152,.0722],dtype=np.float32)
    contrast=float(np.percentile(luminance[valid],90)-np.percentile(luminance[valid],10))
    pairs=[(np.abs(np.diff(luminance,axis=1)),valid[:,1:]&valid[:,:-1]),
           (np.abs(np.diff(luminance,axis=0)),valid[1:,:]&valid[:-1,:])]
    count=sum(int(v.sum()) for _,v in pairs)
    edge=sum(int(((diff>.10)&v).sum()) for diff,v in pairs)/max(1,count)
    # Quantize only visible sample colors, never the actual artwork.
    sample=(colors*255).round().astype(np.uint8)
    q=Image.fromarray(sample.reshape((len(sample),1,3))).quantize(colors=6,method=Image.Quantize.MEDIANCUT)
    table=q.getpalette();counts=sorted(q.getcolors(),reverse=True)
    palette=["#%02x%02x%02x"%tuple(table[3*i:3*i+3]) for _,i in counts]
    def category(v,low,high,names):return names[0] if v<low else names[2] if v>high else names[1]
    return validate(dict(name=name,source=source,reference=modular.png_uri(im),palette=palette,
                         saturation=category(sat,.24,.62,CHOICES["saturation"]),
                         contrast=category(contrast,.24,.65,CHOICES["contrast"]),
                         detail=category(edge,.035,.18,CHOICES["detail"]),
                         shading="pixel" if pixel else "auto",
                         metrics=dict(saturation=round(sat*100),contrast=round(contrast*100),edge_density=round(edge*100))))

def guidance(value):
    p=validate(value)
    if not p or not p["enabled"]:return ""
    parts=[GUIDES[k][p[k]] for k in CHOICES if GUIDES[k][p[k]]]
    if p["accents"] and p["palette"]:
        parts.append("optional accent colors inspired by reference "+", ".join(p["palette"])+", retain natural environment material colors")
    if p["notes"]:parts.append(p["notes"])
    if p["image_condition"]:parts.append("use image reference for rendering style only, do not depict its character or costume")
    return ", ".join(parts)
