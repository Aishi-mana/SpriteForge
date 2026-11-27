"""Raster-first shared-layout blockout. AI supplies art; deterministic geometry supplies alignment."""
import random
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from . import world, modular, alpha_cleanup

ROLES=("background","ground","trail","rock","tree","foreground")
LAYOUTS=("winding","straight","clearing")
STYLE_TEXT={"anime":"modern anime game environment, refined linework, coherent cel shading, painted natural details",
            "hd2d":"HD-2D inspired JRPG environment, atmospheric lighting, richly textured stylized scenery",
            "painted":"hand-painted 2D game environment, cohesive brushwork",
            "pixel":"pixel art game environment, crisp deliberate pixel clusters",
            "custom":""}
DEFAULT_MATERIALS={"background":"distant scenery of the requested environment",
                   "ground":"continuous ground surface surrounding the traversable trail, no path or large objects",
                   "trail":"walkable path surface material appropriate for the environment",
                   "rock":"single rock or small boulder appropriate for the environment",
                   "tree":"single upright tree or tall environmental object appropriate for the environment",
                   "foreground":"one foreground foliage cluster or framing environmental decoration"}

def settings(value=None):
    if value is None:value={}
    if not isinstance(value,dict):raise ValueError("Invalid blockout settings")
    layout=value.get("layout","winding")
    if layout not in LAYOUTS:raise ValueError("Invalid blockout layout")
    materials=value.get("materials",{})
    if not isinstance(materials,dict):raise ValueError("Invalid materials")
    return dict(layout=layout,seed=world.integer(value.get("seed",42),0,2147483647,"layout seed"),
                rocks=world.integer(value.get("rocks",4),0,6,"rock count"),
                trees=world.integer(value.get("trees",6),0,8,"tree count"),
                foreground=world.integer(value.get("foreground",2),0,2,"foreground count"),
                materials={role:world.label(materials.get(role,DEFAULT_MATERIALS[role]),role+" material",240) for role in ROLES})

def inputs(value,config):
    d,_=world.validate(value)
    if d["view"]!="quarter":raise ValueError("Structured AI blockout currently supports quarter view")
    if not d["prompt"]:raise ValueError("Enter an environment prompt")
    if d["width"]*d["height"]>3_000_000:raise ValueError("AI blockout canvas must be at most three million pixels")
    return d,settings(config)

def needed(config):
    c=settings(config)
    return list(ROLES[:3])+[role for role,count in (("rock",c["rocks"]),("tree",c["trees"]),("foreground",c["foreground"])) if count]

def prompt(value,config,role):
    d,c=inputs(value,config)
    if role not in needed(c):raise ValueError("Unused or invalid blockout role")
    theme=d["prompt"];style=STYLE_TEXT[d["style"]]
    material=c["materials"][role]
    common=", ".join(v for v in (style,"consistent environment art direction",theme,material,"elevated three-quarter JRPG camera, consistent light from upper left") if v)
    if role=="background":
        detail="distant scenic background plate only, scenery fills frame, no path, no close foreground props, no characters, atmospheric distance"
    elif role in ("ground","trail"):
        detail="even continuous surface texture plate, viewed from above at three-quarter angle, texture fills entire square edge to edge, no horizon, no isolated objects, no border, no cast shadows from objects"
    else:
        detail="one isolated complete object, upright, entire silhouette including base visible, generous empty margins, no scenery, no ground plane, no cast shadow, no other objects"
    return common+", "+detail, "world_prop" if role in ROLES[3:] else "world_plate"

def normalize(raw,role,bg,tol=40,pixel=False):
    if role not in ROLES:raise ValueError("Invalid blockout asset role")
    if raw.width*raw.height>4_200_000 or max(raw.size)>2048:raise ValueError("Generated image exceeds source budget")
    im=raw.convert("RGBA")
    if role in ROLES[:3]:
        # Opaque source plates; no automatic background eraser or palette quantization.
        return modular.png_uri(im.convert("RGB").convert("RGBA"))
    if im.getchannel("A").getextrema()==(255,255):
        im,_=alpha_cleanup.clean(im,tol,mode="smart",background=bg,soft=not pixel)
    alpha=im.getchannel("A");box=alpha.getbbox()
    if box is None or alpha.getextrema()[0]==255:raise ValueError("Object background removal failed; choose another key color or regenerate")
    im=im.crop(box)
    if im.getchannel("A").getextrema()[1]<128:raise ValueError("Object is too transparent")
    return modular.png_uri(im)

def layout(value,config):
    """All positions are projected map pixels, not guesses from generated artwork."""
    d,c=inputs(value,config);w,h=d["width"],d["height"];rng=random.Random(c["seed"])
    if c["layout"]=="straight":centers=[.5,.5,.5,.5,.5]
    elif c["layout"]=="clearing":centers=[.50,.48,.50,.52,.50]
    else:centers=[.48,.62,.43,.55,.50]
    ys=[.20,.37,.57,.78,1.0]
    widths=[.07,.105,.15,.19,.24] if c["layout"]!="clearing" else [.09,.18,.32,.30,.25]
    left=[(round(w*(x-r)),round(h*y)) for x,r,y in zip(centers,widths,ys)]
    right=[(round(w*(x+r)),round(h*y)) for x,r,y in zip(centers,widths,ys)]
    def bounds(y):
        i=next((j for j in range(4) if y<=ys[j+1]),3)
        t=max(0,min(1,(y-ys[i])/(ys[i+1]-ys[i])))
        center=centers[i]*(1-t)+centers[i+1]*t
        width=widths[i]*(1-t)+widths[i+1]*t
        return center-width,center+width
    props=[]
    for role,count in (("rock",c["rocks"]),("tree",c["trees"]),("foreground",c["foreground"])):
        for i in range(count):
            side=i%2
            y=(.32+.59*(i//2+.5)/max(1,(count+1)//2)+rng.uniform(-.035,.035)) if role!="foreground" else .96
            lo,hi=bounds(y)
            # Footprint is placed outside path; overhanging silhouette is expected.
            x=(max(.045,lo*.48+rng.uniform(-.025,.025)) if side==0 else min(.955,hi+(1-hi)*.52+rng.uniform(-.025,.025)))
            if role=="foreground":x=.025 if side==0 else .975
            depth=.52+.48*y
            size=round(min(w,h)*depth*({"rock":.17,"tree":.55,"foreground":.48}[role])*rng.uniform(.85,1.13))
            props.append(dict(role=role,x=round(w*x),y=min(h-1,round(h*y)),size=max(12,size),flip=bool(rng.randrange(2))))
    props.sort(key=lambda p:(p["role"]=="foreground",p["y"]))
    return dict(path=left+right[::-1],props=props,spawn=[round(w*centers[3]),round(h*ys[3])])

def assemble(value,config,assets):
    d,c=inputs(value,config);w,h=d["width"],d["height"]
    roles=needed(c)
    if not isinstance(assets,dict) or set(assets)!=set(roles):raise ValueError("Missing or unexpected generated artwork")
    if any(not isinstance(v,str) for v in assets.values()) or sum(len(v) for v in assets.values())>32_000_000:
        raise ValueError("Source artwork exceeds blockout budget")
    images={role:world.image(uri) for role,uri in assets.items()}
    if sum(im.width*im.height for im in images.values())>12_000_000:raise ValueError("Source artwork exceeds pixel budget")
    for role,im in images.items():
        if role in ROLES[3:] and (not im.getchannel("A").getbbox() or im.getchannel("A").getextrema()[0]==255):
            raise ValueError("Expected transparent prop artwork")
    plan=layout(d,c)
    sampling=Image.Resampling.NEAREST if d["pixel"] else Image.Resampling.LANCZOS
    layers=[]
    def add(role,name,im,x=0,y=0):
        layers.append(dict(id="layer_"+str(len(layers)+1),name=name,role=role,image=modular.png_uri(im),
                           x=x,y=y,opacity=100,visible=True,locked=False))
    def plate(role):return ImageOps.fit(images[role].convert("RGB"),(w,h),sampling).convert("RGBA")
    add("background","Distant background",plate("background"))
    ground=plate("ground");alpha=Image.new("L",(1,h))
    alpha.putdata([round(255*max(0,min(1,(y/h-.12)/.13))) for y in range(h)])
    ground.putalpha(alpha.resize((w,h),Image.Resampling.NEAREST));add("ground","Ground surface",ground)
    trail=plate("trail");mask=Image.new("L",(w,h));ImageDraw.Draw(mask).polygon(plan["path"],fill=255)
    if not d["pixel"]:mask=mask.filter(ImageFilter.GaussianBlur(max(1,min(w,h)*.004)))
    trail.putalpha(mask);add("ground_detail","Traversable trail",trail)
    counts={}
    for item in plan["props"]:
        role=item["role"];im=images[role].copy()
        im.thumbnail((item["size"],item["size"]),sampling)
        if item["flip"]:im=ImageOps.mirror(im)
        counts[role]=counts.get(role,0)+1
        add({"rock":"objects","tree":"foliage","foreground":"foreground"}[role],
            role.title()+" "+str(counts[role]),im,item["x"]-im.width//2,item["y"]-im.height+1)
    return world.validate({**d,"layers":layers,"spawn":plan["spawn"],"blockout":c})[0]
