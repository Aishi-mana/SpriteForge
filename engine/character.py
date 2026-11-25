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

def view_prompt(view, description=""):
    if view not in directions.UNIQUE: raise ValueError("Unknown unique direction")
    if len(description)>1800: raise ValueError("Character description is limited to 1800 characters")
    return ", ".join(x for x in (description.strip(), directions.HINT[view], IDENTITY) if x)

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
