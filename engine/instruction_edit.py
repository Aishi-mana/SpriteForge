"""Instruction-conditioned edits with explicit backend capabilities."""
from PIL import Image
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

def edit(source,model,ckpt,lora_dir,instruction,negative="",size=768,bg="green",tolerance=30,pixel=False,
         strength=.45,steps=4,cfg=1,seed=0,remove_bg=True,keep_canvas=True,lora="",lora_weight=1.0):
    backend=capability(model)
    if not backend:
        raise ValueError("Select Qwen Rapid, NetaYume local or a verified SDXL editing checkpoint")
    canvas,box=prepare(source,size,bg,pixel)
    prompt=("Edit the supplied character image. "+instruction.strip()+
            ". Preserve the character's identity, facial features, hairstyle, proportions, pose, framing and art style except where explicitly requested. "
            "Keep one character, use a plain solid "+bg+" background.")
    if backend=="sdxl_inpaint":
        # Full-canvas image-to-image via the existing inpainting pipeline.
        # Regional pixel protection is a subsequent phase.
        raw=gen.inpaint(ckpt,lora,lora_weight,lora_dir,prompt,negative,canvas,Image.new("L",canvas.size,255),
                        strength,steps,cfg,seed,bg=bg,kind="instruction_edit",art_style="pixel" if pixel else "custom")
    else:
        raw,seed=gen.generate(ckpt,lora,lora_weight,lora_dir,prompt,negative,steps,cfg,seed,size,bg,
                              canvas,1-strength,1,kind="instruction_edit",art_style="pixel" if pixel else "custom")[0]
    out=finish(raw,source,box,size,bg,tolerance,pixel,remove_bg,keep_canvas)
    return out,{"size":list(out.size),"backend":backend,"seed":seed,"pipeline":"pixel" if pixel else "hd",
                "strength_supported":backend!="qwen_instruction","canvas_preserved":keep_canvas}
