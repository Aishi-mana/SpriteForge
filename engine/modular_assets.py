"""Reference-guided isolated accessory generation and approximate fitting.
No semantic segmentation or automatic garment extraction.
"""
import numpy as np
from PIL import Image
from . import modular, pixelize as px, styles

# Fractional placement relative to the visible body bounding box (left, top, right, bottom).
REGIONS = {
    "outfit": (.10,.28,.90,.90),
    "footwear": (.18,.80,.82,1.0),
    "hair_front": (.12,-.05,.88,.40),
    "hair_back": (.03,-.04,.97,.72),
    "accessory": (.60,.05,1.03,.40),
    "other": (.20,.20,.80,.80),
}
LABELS = {"outfit":"clothing outfit, garment only, empty neckline and sleeves",
          "footwear":"matching pair of shoes or boots, footwear only",
          "hair_front":"front hairstyle piece, hair only, empty face opening",
          "hair_back":"back hairstyle piece, hair only, no face or head",
          "accessory":"one wearable accessory or held game item",
          "other":"one isolated character customization item"}

def prompt(category,description,view):
    if category not in REGIONS:raise ValueError("Choose an asset category other than body")
    if not isinstance(description,str) or not description.strip() or len(description)>1200:raise ValueError("Describe an asset (1–1200 characters)")
    if view not in ("front","side","back","three-quarter"):raise ValueError("Invalid viewing angle")
    return (f"{description.strip()}, {LABELS[category]}, {view} view matching the reference character's angle, "
            "matching the reference art style, proportions, perspective and lighting. Draw only the detachable asset, "
            "without the character, mannequin, skin, face, body, hands or background scenery. "
            "Isolated item, complete silhouette, plain solid background, no cast shadow, no text, no extra items.")

def reference(recipe,source="body"):
    clean,images=modular.validate(recipe)
    if source not in ("body","composite"):raise ValueError("Invalid reference source")
    # Always measure the body, not hats or long accessories, for fitting.
    body={**clean,"layers":[{**l,"visible":l["visible"] and l["category"]=="body"} for l in clean["layers"]]}
    base=modular.composite(body,images)
    bb=base.getchannel("A").point(lambda a:255 if a>=32 else 0).getbbox()
    if not bb:raise ValueError("Add a visible body base before generating an asset")
    ref=base if source=="body" else modular.composite(clean,images)
    return clean,images,ref,bb

def region(category,bb,canvas):
    if category not in REGIONS:raise ValueError("Invalid asset category")
    x,y,r,b=bb;w,h=r-x,b-y
    a,c,d,e=REGIONS[category];W,H=canvas
    left=max(0,min(W-1,round(x+a*w)));top=max(0,min(H-1,round(y+c*h)))
    right=max(left+1,min(W,round(x+d*w)));bottom=max(top+1,min(H,round(y+e*h)))
    return left,top,right,bottom

def finish(raw,rect,pixel,colors=24,bg_tol=40):
    """Border key, reject empty/uncut outputs, crop, then fit without stretching."""
    tolerance=max(1,min(100,int(bg_tol)))
    im=px.remove_bg(raw,tolerance) if pixel else styles.finish(raw,max(raw.size),True,tolerance)[0]
    a=np.asarray(im.getchannel("A"))
    if not np.any(a>=32):raise ValueError("Generated asset is empty after background removal; retry with different background")
    if not np.any(a==0):raise ValueError("Background could not be removed; retry with a contrasting background")
    bb=im.getchannel("A").point(lambda v:255 if v>=16 else 0).getbbox()
    im=im.crop(bb)
    x,y,r,b=rect
    scale=min((r-x)/im.width,(b-y)/im.height)
    dims=(max(1,round(im.width*scale)),max(1,round(im.height*scale)))
    if pixel:
        # Quantize at target scale without enforcing the old outfit palette.
        im,_=px.pixelize(im,"fixed",max(dims),max(4,min(64,int(colors))),"none",False,tolerance,
                         remove_shadow=False,clean=False,outline="none")
        im=im.resize(dims,Image.Resampling.NEAREST)
    else:im=im.resize(dims,Image.Resampling.LANCZOS)
    if not im.getchannel("A").getbbox():raise ValueError("Asset vanished at target resolution; enlarge the canvas")
    return im,{"size":list(im.size),"pipeline":"pixel" if pixel else "hd",
               "x":x+(r-x-im.width)//2,"y":y+(b-y-im.height)//2,
               "fit_region":list(rect),"review_required":True}

def candidate_preview(recipe,images,layer,replace_category=True):
    # Compose a temporary alternative only; original recipe and images stay unchanged.
    rows=[dict(l) for l in recipe["layers"]]
    if replace_category:
        for l in rows:
            if l["category"]==layer["category"]:l["visible"]=False
    order=modular.CATEGORIES
    index=next((i for i,l in enumerate(rows) if order.index(l["category"])>order.index(layer["category"])),len(rows))
    rows.insert(index,dict(layer))
    ims=list(images);ims.insert(index,modular.decode(layer["image"]))
    return modular.composite({**recipe,"layers":rows},ims)
