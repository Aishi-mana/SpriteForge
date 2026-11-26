"""Reference-led character views with shared framing. No identity guarantee."""
import base64, io
from PIL import Image
from . import directions, pixelize as px, styles

IDENTITY = ("Keep the reference character's face, apparent age, body and head proportions, "
            "hair shape and color, eye color, costume, footwear and accessories. "
            "Preserve the same design and illustration style, including asymmetric details. "
            "Draw the whole character from the requested camera angle, not a pasted head or the original camera view. "
            "One subject only, neutral standing pose, arms slightly separated from torso, both feet visible, "
            "no text, no scenery, no contact shadow, no turnaround sheet or duplicate figures.")

FEATURES = {
    "face": "facial structure, apparent age and recognizable facial features",
    "eyes": "eye shape and eye color",
    "hair": "hair color, hairstyle and silhouette",
    "body": "body build, head-to-body ratio and proportions",
    "outfit": "clothing design, colors, footwear and construction",
    "accessories": "accessories and their original placement",
    "style": "illustration style, linework and shading",
    "pose": "body stance and limb gesture, independent of camera angle",
    "expression": "facial expression",
}
DEFAULT_LOCKS = ("face","eyes","hair","body","outfit","accessories","style")

def active_locks(locks=None, target=None):
    if locks is None:
        locks=list(DEFAULT_LOCKS)
    if not isinstance(locks,list) or any(not isinstance(k,str) or k not in FEATURES for k in locks):
        raise ValueError("Invalid appearance lock")
    if target is not None and target not in (*FEATURES,"custom"):
        raise ValueError("Invalid variation target")
    return [k for k in FEATURES if k in locks and k!=target]

def lock_prompt(locks):
    return ("Preserve from the reference: "+ "; ".join(FEATURES[k] for k in locks)+".") if locks else ""

def variation_prompt(description, target, change, locks=None):
    if not isinstance(description,str) or len(description)>1800:
        raise ValueError("Identity description must be at most 1800 characters")
    if not isinstance(change,str) or not change.strip() or len(change)>1200:
        raise ValueError("Describe the desired change (1–1200 characters)")
    if target not in (*FEATURES,"custom"):
        raise ValueError("Invalid variation target")
    effective=active_locks(locks,target)
    if target=="custom" and len(effective)==len(FEATURES):
        raise ValueError("Unlock at least one feature for a custom change")
    requested=("Requested "+(target if target!="custom" else "custom")+" change: "+change.strip()+".")
    return ", ".join(x for x in (requested,description.strip(),lock_prompt(effective),
        "The requested change overrides the original description only for the unlocked target. "
        "Keep the same character and all explicitly preserved features. One complete full-body character, "
        "feet visible, clear silhouette, no text, no duplicate figures, plain background.") if x),effective

def view_prompt(view, description="", locks=None):
    if view not in directions.UNIQUE: raise ValueError("Unknown unique direction")
    if len(description)>1800: raise ValueError("Character description is limited to 1800 characters")
    if locks is None: return ", ".join(x for x in (description.strip(), directions.HINT[view], IDENTITY) if x)
    return ", ".join(x for x in (description.strip(),directions.HINT[view],lock_prompt(active_locks(locks)),
        "Single full-body character from the requested camera angle, both feet visible, neutral stance unless pose is preserved, no text, scenery or duplicate figures.") if x)

def decode_reference(value):
    if not isinstance(value,str) or not value.startswith("data:image/") or ";base64," not in value or len(value)>11_000_000:
        raise ValueError("Use a bounded local reference image")
    with Image.open(io.BytesIO(base64.b64decode(value.split(",",1)[1],validate=True))) as im:
        if max(im.size)>2048 or im.width*im.height>4_194_304:
            raise ValueError("Reference must be at most 2048 px per side")
        return im.convert("RGBA")

def content(im):
    im=im.convert("RGBA")
    bb=im.getchannel("A").point(lambda a:255 if a>=16 else 0).getbbox()
    if not bb: raise ValueError("Character image is empty")
    return im.crop(bb)

def align(im,size,pixel=False):
    """Fit silhouette to a common canvas and baseline without stretching."""
    im=content(im)
    w,h=im.size
    scale=min(size*.86/h,size*.90/w)
    dims=(max(1,round(w*scale)),max(1,round(h*scale)))
    filt=Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS
    im=im.resize(dims,filt)
    out=Image.new("RGBA",(size,size))
    out.paste(im,((size-im.width)//2,round(size*.94)-im.height))
    return out

def finish(raw,anchor,art_style,size,colors=24,lock_palette=True,bg_tol=40):
    pixel=art_style=="pixel"
    if pixel:
        if size not in (32,48,64,96,128): raise ValueError("Pixel canvas must be 32–128 px")
        pal=px.palette_from_sprite(anchor) if lock_palette else None
        sprite,info=px.pixelize(raw,"fixed",size,max(4,min(64,colors)),pal if pal is not None else "none",True,bg_tol)
    else:
        if size!=256: raise ValueError("HD direction canvas currently limited to 256 px")
        sprite,info=styles.finish(raw,512,True,bg_tol)
        pal=None
    out=align(sprite,size,pixel)
    return out,{**info,"size":list(out.size),"pipeline":"pixel" if pixel else "hd",
                "palette_locked":pal is not None,"baseline":round(size*.94),
                "identity_reference":True}


def finish_variation(raw,anchor,art_style,size,colors=24,lock_palette=False,bg_tol=40):
    """Full-body variant for reference/Animate, not a direction slot."""
    pixel=art_style=="pixel"
    if pixel:
        if size not in (32,48,64,96,128): raise ValueError("Choose a pixel size of 32–128")
        pal=px.palette_from_sprite(anchor) if lock_palette else None
        sprite,info=px.pixelize(raw,"fixed",size,max(4,min(64,colors)),pal if pal is not None else "none",True,bg_tol)
    else:
        if size not in (256,512,768,1024): raise ValueError("Choose a supported HD output size")
        sprite,info=styles.finish(raw,size,True,bg_tol)
        pal=None
    # Validate nonempty silhouette before reporting success.
    content(sprite)
    return sprite,{**info,"size":list(sprite.size),"pipeline":"pixel" if pixel else "hd","palette_locked":pal is not None,"identity_reference":True}
