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


def registered_prompt(category,description,view):
    return prompt(category,description,view)+(
        " Use the supplied body as a fixed pose and registration template. "
        "Match its exact head, shoulders, waist, limbs and feet as appropriate. "
        "Keep the item at the corresponding position in the same framed canvas; "
        "do not center, enlarge, rotate, redesign or redraw the body. "
        "Return the isolated wearable on a solid contrasting background.")


def register_asset(asset,info,canvas):
    """Embed an already fitted asset without resampling or changing its placement."""
    W,H=canvas
    x,y=info["x"],info["y"]
    asset=asset.convert("RGBA")
    if not (0<=x and 0<=y and x+asset.width<=W and y+asset.height<=H):
        raise ValueError("Fitted asset lies outside the fixed canvas")
    if not asset.getchannel("A").getbbox():
        raise ValueError("Registered asset has no visible pixels")
    layer=Image.new("RGBA",(W,H))
    layer.paste(asset,(x,y))
    return layer,{**info,"size":[W,H],"x":0,"y":0,"asset_bounds":list(layer.getchannel("A").getbbox()),
                  "registration":"fixed_canvas","fit_method":"approximate_region",
                  "review_required":True}


def body_landmarks(body):
    """Estimate horizontal silhouette bands in original canvas coordinates.

    These are geometric hints, not detected joints or a pose estimator.
    """
    mask=np.asarray(body.convert("RGBA"))[:,:,3]>=32
    ys,xs=np.nonzero(mask)
    if not len(xs):
        raise ValueError("Body reference is empty")
    x,y,r,b=int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)
    h=b-y
    def band(lo,hi):
        t=y+min(h-1,int(h*lo))
        bot=max(t+1,min(b,y+int(np.ceil(h*hi))))
        yy,xx=np.nonzero(mask[t:bot])
        if not len(xx):
            return [x,t,r,bot]
        return [int(xx.min()),int(yy.min()+t),int(xx.max()+1),int(yy.max()+t+1)]
    return {"body":[x,y,r,b],"head":band(0,.27),"shoulders":band(.27,.44),
            "waist":band(.44,.62),"legs":band(.62,.86),"feet":band(.86,1),
            "method":"silhouette_bands","review_required":True}


def placement_guide(body,category):
    """Return a permissive, canvas-aligned placement guide; never clip an asset."""
    if category not in REGIONS:
        raise ValueError("Invalid asset category")
    marks=body_landmarks(body)
    W,H=body.size
    x,y,r,b=marks["body"]
    h=b-y
    pad=max(1,round(h*.04))
    def union(*keys):
        rects=[marks[k] for k in keys]
        return (min(v[0] for v in rects),min(v[1] for v in rects),
                max(v[2] for v in rects),max(v[3] for v in rects))
    if category=="hair_front":
        rect=union("head")
    elif category=="hair_back":
        rect=union("head","shoulders","waist")
    elif category=="outfit":
        rect=union("shoulders","waist","legs")
    elif category=="footwear":
        rect=union("feet")
    else:
        rect=tuple(marks["body"])
    l,t,rr,bb=rect
    rect=(max(0,l-pad),max(0,t-pad),min(W,rr+pad),min(H,bb+pad))
    # Nonrectangular mask follows silhouette row extents with garment allowance.
    src=np.asarray(body.convert("RGBA"))[:,:,3]>=32
    guide=np.zeros((H,W),dtype=np.uint8)
    for row in range(rect[1],rect[3]):
        near=src[max(0,row-pad):min(H,row+pad+1)]
        cols=np.flatnonzero(near.any(axis=0))
        if len(cols):
            left=max(rect[0],int(cols[0])-pad)
            right=min(rect[2],int(cols[-1])+pad+1)
        else:
            left,right=rect[0],rect[2]
        if right>left:
            guide[row,left:right]=255
    return rect,Image.fromarray(guide),marks


def placement_review(asset,guide):
    if asset.size!=guide.size:
        raise ValueError("Placement guide must match registered canvas")
    visible=np.asarray(asset.convert("RGBA"))[:,:,3]>=32
    count=int(visible.sum())
    outside=int((visible & (np.asarray(guide)==0)).sum())
    return {"visible_pixels":count,"outside_guide":outside,
            "outside_fraction":round(outside/max(1,count),4),
            "review_required":True}


def extract_edit(body,edited,guide,tolerance=30):
    """Extract changed visible pixels in original coordinates; no semantic guarantee."""
    if body.size!=edited.size or body.size!=guide.size:
        raise ValueError("Edited body and guide must share the reference canvas")
    src=np.asarray(body.convert("RGBA"))
    dst=np.asarray(edited.convert("RGBA"))
    delta=np.max(np.abs(src.astype(np.int16)-dst.astype(np.int16)),axis=2)
    changed=(dst[:,:,3]>=32)&((src[:,:,3]<32)|(delta>tolerance))
    if not changed.any():
        raise ValueError("No changed asset pixels found; retry the edit")
    out=np.zeros_like(dst)
    out[changed]=dst[changed]
    layer=Image.fromarray(out)
    return layer,{"size":list(body.size),"x":0,"y":0,"registration":"fixed_canvas",
                  "fit_method":"registered_edit_difference","asset_bounds":list(layer.getchannel("A").getbbox()),
                  "placement":placement_review(layer,guide),"review_required":True}


def qwen_asset_instruction(category,description,view):
    prompt(category,description,view)  # validate category, length and view
    return ("Equip the reference mannequin with "+description.strip()+". Category: "+LABELS[category]+
            ". Keep the exact "+view+" view, pose, framing, body proportions and all uncovered body pixels unchanged. "
            "Add only the requested wearable, without shifting or resizing the mannequin. "
            "Do not change the background or add shadows. Keep the mannequin visible for comparison.")


def qwen_asset(body,guide,model,ckpt,lora_dir,category,description,view,**settings):
    from . import instruction_edit
    if instruction_edit.capability(model)!="qwen_instruction":
        raise ValueError("Registered Qwen extraction requires Qwen Rapid")
    edited,meta=instruction_edit.run_edit(body,model,ckpt,lora_dir,
        instruction=qwen_asset_instruction(category,description,view),locks=["body","pose","style"],
        keep_canvas=True,remove_bg=True,**settings)
    layer,info=extract_edit(body,edited,guide,settings.get("tolerance",30))
    return layer,edited,{**meta,**info}
