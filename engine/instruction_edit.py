"""Instruction-conditioned edits with explicit backend capabilities."""
from PIL import Image
import base64, io
import numpy as np
from . import generate as gen, alpha_cleanup

def capability(model):
    if not model.get("supported"):
        return None
    if model.get("backend")=="qwen":
        return "qwen_instruction"
    if model.get("backend")=="neta":
        return "neta_img2img"
    if model.get("family")=="sdxl" and not model.get("backend"):
        return "sdxl_inpaint"
    return None

def prepare(source,size,bg,pixel):
    im=source.convert("RGBA")
    scale=min(size/im.width,size/im.height)
    w,h=max(1,round(im.width*scale)),max(1,round(im.height*scale))
    im=im.resize((w,h),Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS)
    box=((size-w)//2,(size-h)//2,w,h)
    canvas=Image.new("RGB",(size,size),gen.BG_RGB[bg])
    canvas.paste(im,box[:2],im)
    return canvas,box

def finish(raw,source,box,size,bg,tolerance,pixel,remove_bg,keep_canvas):
    im=raw.convert("RGBA")
    if remove_bg:
        im,_=alpha_cleanup.clean(im,tolerance,"smart",gen.BG_RGB[bg],soft=not pixel)
    if keep_canvas:
        if im.size!=(size,size):
            im=im.resize((size,size),Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS)
        x,y,w,h=box
        im=im.crop((x,y,x+w,y+h))
        im=im.resize(source.size,Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS)
    if pixel:
        a=im.getchannel("A").point(lambda v:255 if v>=128 else 0)
        im.putalpha(a)
    if not im.getchannel("A").getbbox():
        raise ValueError("Edit returned an empty image; try a different background or tolerance")
    return im

def decode_mask(value,source_size):
    """A binary luminance PNG matching source dimensions; white is editable."""
    if not isinstance(value,str) or len(value)>2_000_000 or not value.startswith("data:image/png;base64,"):
        raise ValueError("Invalid edit mask PNG")
    try:
        data=base64.b64decode(value.split(",",1)[1],validate=True)
        with Image.open(io.BytesIO(data)) as im:
            if im.format!="PNG" or im.size!=source_size:
                raise ValueError("Mask must match source dimensions")
            mask=im.convert("L").point(lambda v:255 if v>=128 else 0)
    except Exception as e:
        raise ValueError("Invalid edit mask: "+str(e)) from e
    if not mask.getbbox():
        raise ValueError("Paint at least one editable pixel")
    return mask

def protected_composite(source,candidate,mask):
    if source.size!=candidate.size or mask.size!=source.size:
        raise ValueError("Mask, source and candidate must share dimensions")
    return Image.composite(candidate.convert("RGBA"),source.convert("RGBA"),mask)

IDENTITY_LOCKS={
    "face":"facial features and facial structure",
    "eyes":"eye shape and eye color",
    "hair_color":"hair color",
    "hairstyle":"hairstyle and hair length",
    "body":"body proportions and silhouette",
    "pose":"pose and limb placement",
    "style":"art style and rendering technique",
    "palette":"existing character color palette",
    "outfit":"outfit and footwear",
    "accessories":"equipment and accessories",
}
DEFAULT_LOCKS=("face","eyes","hair_color","hairstyle","body","pose","style")

def identity_locks(locks=None):
    if locks is None:
        return list(DEFAULT_LOCKS)
    if not isinstance(locks,list) or len(locks)>len(IDENTITY_LOCKS) or any(not isinstance(k,str) or k not in IDENTITY_LOCKS for k in locks) or len(set(locks))!=len(locks):
        raise ValueError("Invalid identity preservation locks")
    return locks

def edit_prompt(instruction,bg,locks=None):
    selected=identity_locks(locks)
    prompt="Edit the supplied character image. "+instruction.strip()+"."
    if selected:
        prompt+=" Preserve "+", ".join(IDENTITY_LOCKS[k] for k in selected)+" exactly where possible. Do not alter these selected features."
    return prompt+" Keep one character, use a plain solid "+bg+" background."

def edit(source,model,ckpt,lora_dir,instruction,negative="",size=768,bg="green",tolerance=30,pixel=False,
         strength=.45,steps=4,cfg=1,seed=0,remove_bg=True,keep_canvas=True,lora="",lora_weight=1.0,mask=None,locks=None):
    backend=capability(model)
    if not backend:
        raise ValueError("Select Qwen Rapid, NetaYume local or a verified SDXL editing checkpoint")
    region=decode_mask(mask,source.size) if mask is not None else None
    if region is not None and not keep_canvas:
        raise ValueError('Regional editing requires original canvas size')
    canvas,box=prepare(source,size,bg,pixel)
    selected=identity_locks(locks)
    prompt=edit_prompt(instruction,bg,selected)
    if region is not None:
        prompt += " Restrict the requested changes to the selected area; preserve surrounding content."
    if backend=="sdxl_inpaint":
        paint_mask=Image.new("L",canvas.size,255)
        if region is not None:
            x,y,w,h=box
            paint_mask=Image.new("L",canvas.size,0)
            paint_mask.paste(region.resize((w,h),Image.Resampling.NEAREST),(x,y))
        raw=gen.inpaint(ckpt,lora,lora_weight,lora_dir,prompt,negative,canvas,paint_mask,
                        strength,steps,cfg,seed,bg=bg,kind="instruction_edit",art_style="pixel" if pixel else "custom")
    else:
        raw,seed=gen.generate(ckpt,lora,lora_weight,lora_dir,prompt,negative,steps,cfg,seed,size,bg,
                              canvas,1-strength,1,kind="instruction_edit",art_style="pixel" if pixel else "custom")[0]
    out=finish(raw,source,box,size,bg,tolerance,pixel,remove_bg,keep_canvas)
    if region is not None:
        out=protected_composite(source,out,region)
    return out,{"size":list(out.size),"backend":backend,"seed":seed,"pipeline":"pixel" if pixel else "hd",
                "strength_supported":backend!="qwen_instruction","canvas_preserved":keep_canvas,"regional":region is not None,
                "protected_pixels":int(np.count_nonzero(np.asarray(region)==0)) if region is not None else 0,
                "native_mask":region is not None and backend=="sdxl_inpaint",
                "identity_locks":selected,"identity_lock_type":"prompt_guidance"}
