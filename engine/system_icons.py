"""Single-subject, square transparent game icons using shared style guidance."""
from PIL import Image
from . import system_assets as S, system_kit, world, world_style, modular

def settings(value):
    if not isinstance(value,dict):raise ValueError("Invalid icon settings")
    category=value.get("category")
    if category not in S.ICON_CATEGORIES:raise ValueError("Invalid icon category")
    size=value.get("size",64)
    if type(size) is not int or size not in S.ICON_SIZES:raise ValueError("Invalid icon size")
    return dict(category=category,size=size,subject=world.label(value.get("subject"),"icon subject",240),
                name=world.label(value.get("name"),"icon name",60))

def prompt(theme, options):
    d=S.validate(theme);o=settings(options)
    if len(d["assets"])>=S.MAX_ASSETS:raise ValueError("Artwork library is full")
    guide=world_style.guidance(d.get("style_profile")).replace("retain natural environment material colors","retain readable icon material colors")
    return ", ".join(x for x in (system_kit.STYLES[d["style"]],d["prompt"],guide,
        "optional accent colors "+", ".join(d["palette"]) if d["palette"] else "",
        o["category"]+" game icon: "+o["subject"],
        "single isolated complete subject, centered square composition, readable silhouette at small size, consistent upper-left lighting, generous empty margins, no text, no letters, no numbers, no interface frame, no other objects") if x)

def normalize(raw,bg,tol,pixel,size):
    if type(size) is not int or size not in S.ICON_SIZES:raise ValueError("Invalid icon size")
    im=world.image(system_kit.normalize(raw,bg,tol,pixel))
    box=im.getchannel("A").getbbox()
    if not box:raise ValueError("Empty icon")
    im=im.crop(box)
    pad=max(1,round(size*.08))
    im.thumbnail((size-2*pad,size-2*pad),Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS)
    out=Image.new("RGBA",(size,size))
    out.paste(im,((size-im.width)//2,(size-im.height)//2))
    return modular.png_uri(out)

def append(theme,options,image):
    d=S.validate(theme);o=settings(options)
    if len(d["assets"])>=S.MAX_ASSETS:raise ValueError("Artwork library is full")
    im=world.image(image)
    if im.size!=(o["size"],o["size"]) or not im.getchannel("A").getbbox() or im.getchannel("A").getextrema()[0]==255:raise ValueError("Expected transparent square icon")
    ids={a["id"] for a in d["assets"]};i=1
    while "icon_"+str(i) in ids:i+=1
    d["assets"].append(dict(id="icon_"+str(i),role="icon",name=o["name"],image=image,icon={k:o[k] for k in ("category","size","subject")}))
    return S.validate(d)
