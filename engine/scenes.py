"""Bounded CPU scene compositor of independent baked animation snapshots."""
import math
import re
from PIL import Image
from . import modular, custom_cleanup, custom_timeline, vfx

MAX_ACTORS=8
MAX_ENCODED=24_000_000
MAX_SOURCE_PIXELS=24_000_000

def integer(v,lo,hi,name):
    return modular.integer(v,lo,hi,name)

def boolean(v,name):
    if not isinstance(v,bool):raise ValueError("Invalid "+name)
    return v

def name(v):
    if not isinstance(v,str) or not v.strip() or len(v)>60:raise ValueError("Invalid scene/actor name")
    return v.strip()

def clip(value,budget=None):
    if not isinstance(value,dict):raise ValueError("Invalid actor clip")
    frames=value.get("frames")
    if not isinstance(frames,list) or not 1<=len(frames)<=32:raise ValueError("Actor clip requires 1–32 PNG frames")
    if budget is None:budget=[0,0]
    imgs=[];dims=None
    for uri in frames:
        if not isinstance(uri,str):raise ValueError("Invalid actor image")
        budget[0]+=len(uri)
        if budget[0]>MAX_ENCODED:raise ValueError("Scene exceeds 24 MB encoded actor budget")
        im=custom_cleanup.decode_frame(uri)
        if dims is None:dims=im.size
        if im.size!=dims:raise ValueError("Actor frames must share one canvas")
        budget[1]+=im.width*im.height
        if budget[1]>MAX_SOURCE_PIXELS:raise ValueError("Scene exceeds 24 million source frame pixels")
        imgs.append(im)
    pivot=value.get("pivot")
    if not isinstance(pivot,list) or len(pivot)!=2:raise ValueError("Invalid actor pivot")
    pivot=[integer(pivot[0],0,dims[0],"pivot x"),integer(pivot[1],0,dims[1],"pivot y")]
    return dict(name=name(value.get("name","actor")),fps=integer(value.get("fps",10),1,60,"actor FPS"),
                loop=boolean(value.get("loop",True),"actor loop"),pixel=boolean(value.get("pixel",True),"actor sampling"),
                pivot=pivot,frames=list(frames)),imgs

def validate(value):
    if not isinstance(value,dict) or value.get("version",1)!=1:raise ValueError("Invalid scene")
    w=integer(value.get("width",512),16,1024,"scene width");h=integer(value.get("height",384),16,1024,"scene height")
    count=integer(value.get("count",16),2,64,"scene frame count")
    fps=integer(value.get("fps",12),1,60,"scene FPS")
    actors=value.get("actors",[])
    if not isinstance(actors,list) or len(actors)>MAX_ACTORS:raise ValueError("Scene supports up to eight actors")
    out=[];decoded={};used=set();budget=[0,0]
    for a in actors:
        if not isinstance(a,dict):raise ValueError("Invalid scene actor")
        key=a.get("id")
        if not isinstance(key,str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}",key) or key in used:raise ValueError("Invalid or duplicate actor ID")
        used.add(key)
        c,imgs=clip(a.get("clip"),budget);decoded[key]=imgs
        start=integer(a.get("start",0),0,count-1,"actor start")
        end=integer(a.get("end",count-1),start,count-1,"actor end")
        behavior=a.get("behavior","loop" if c["loop"] else "hold")
        if behavior not in ("loop","hold","hide"):raise ValueError("Invalid actor end behavior")
        x=integer(a.get("x",w//2),-2048,2048,"actor x");y=integer(a.get("y",h//2),-2048,2048,"actor y")
        out.append(dict(id=key,name=name(a.get("name",c["name"])),clip=c,x=x,y=y,
            end_x=integer(a.get("end_x",x),-2048,2048,"actor end x"),end_y=integer(a.get("end_y",y),-2048,2048,"actor end y"),
            z=integer(a.get("z",0),-100,100,"actor depth"),scale=integer(a.get("scale",100),10,200,"actor scale"),
            opacity=integer(a.get("opacity",100),0,100,"actor opacity"),flip=boolean(a.get("flip",False),"actor facing"),
            visible=boolean(a.get("visible",True),"actor visibility"),start=start,end=end,
            offset=integer(a.get("offset",0),0,len(imgs)-1,"source frame offset"),
            speed=integer(a.get("speed",100),10,300,"actor speed"),behavior=behavior))
    effects=vfx.validate(value.get("effects",[]),count,used)
    return dict(version=1,name=name(value.get("name","scene")),width=w,height=h,count=count,fps=fps,
                loop=boolean(value.get("loop",True),"scene loop"),actors=out,effects=effects),decoded

def from_timeline(body):
    frames,meta=custom_timeline.render(body.get("image"),body.get("profile"),body.get("padding",32))
    frames=custom_cleanup.apply(frames,meta,body.get("cleanup"))
    result=dict(name=meta["name"],fps=meta["fps"],loop=meta["loop"],pixel=body["profile"].get("pixel",True),
                pivot=meta["pivot"],frames=[modular.png_uri(im) for im in frames])
    return clip(result)[0]

def frame_index(actor,scene_frame,scene_fps):
    if not actor["visible"] or not actor["start"]<=scene_frame<=actor["end"]:return None
    count=len(actor["clip"]["frames"])
    index=actor["offset"]+((scene_frame-actor["start"])*actor["clip"]["fps"]*actor["speed"])//(scene_fps*100)
    if actor["behavior"]=="loop":return index%count
    if actor["behavior"]=="hide" and index>=count:return None
    return min(index,count-1)

def position(actor,frame):
    t=(frame-actor["start"])/max(1,actor["end"]-actor["start"])
    return (round(actor["x"]+(actor["end_x"]-actor["x"])*t),round(actor["y"]+(actor["end_y"]-actor["y"])*t))

def composite(out,im,left,top):
    x0,y0=max(0,left),max(0,top);x1,y1=min(out.width,left+im.width),min(out.height,top+im.height)
    if x1>x0 and y1>y0:out.alpha_composite(im.crop((x0-left,y0-top,x1-left,y1-top)),(x0,y0))


def compose(scene,decoded,index,cache):
    out=Image.new("RGBA",(scene["width"],scene["height"]))
    by={a["id"]:a for a in scene["actors"]}
    layers=[(a["z"],0,a) for a in scene["actors"]]+[(e["z"],1,e) for e in scene["effects"]]
    for _,kind,a in sorted(layers,key=lambda layer:(layer[0],layer[1])):
        if kind==1:
            if not vfx.active(a,index):continue
            x,y=a["x"],a["y"]
            if a["actor"] is not None:
                actor=by[a["actor"]]
                if frame_index(actor,index,scene["fps"]) is None or not actor["opacity"]:continue
                ax,ay=position(actor,index);x=ax+(-x if actor["flip"] else x);y=ay+y
            dx,dy=vfx.projectile_offset(a,index)
            x+=dx;y+=dy
            im,(px,py)=vfx.surface(a,index)
            composite(out,im,x-px,y-py)
            continue
        i=frame_index(a,index,scene["fps"])
        if i is None or not a["opacity"]:continue
        key=(a["id"],i)
        if key not in cache:
            im=decoded[a["id"]][i]
            pw,ph=a["clip"]["pivot"];w,h=im.size
            nw,nh=max(1,round(w*a["scale"]/100)),max(1,round(h*a["scale"]/100))
            # Keep cache bounded; only cache transformed frames under 8M aggregate pixels.
            if a["flip"]:im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT);pw=w-pw
            if (nw,nh)!=(w,h):im=im.resize((nw,nh),Image.Resampling.NEAREST if a["clip"]["pixel"] else Image.Resampling.BICUBIC)
            if a["opacity"]!=100:
                im=im.copy();im.putalpha(im.getchannel("A").point([round(v*a["opacity"]/100) for v in range(256)]))
            item=(im,round(pw*nw/w),round(ph*nh/h))
            if sum(v[0].width*v[0].height for v in cache.values())+nw*nh<=8_000_000:cache[key]=item
        else:item=cache[key]
        im,px,py=item;x,y=position(a,index);left,top=x-px,y-py
        # Clip explicitly to the scene bounds, including negative positions.
        composite(out,im,left,top)
    return out

def render(value,frame=None,preview=True):
    scene,decoded=validate(value)
    if not scene["actors"] and not scene["effects"]:raise ValueError("Add at least one actor or effect")
    indices=list(range(scene["count"])) if frame is None else [integer(frame,0,scene["count"]-1,"scene frame")]
    if scene["width"]*scene["height"]*len(indices)>(12_000_000 if preview else 32_000_000):
        raise ValueError("Scene exceeds frame budget; reduce dimensions or frame count")
    work=sum(sum(max(1,round(im.width*a["scale"]/100))*max(1,round(im.height*a["scale"]/100))
                 for im in decoded[a["id"]]) for a in scene["actors"])
    # Prevent excessive repeated scaling of huge source clips.
    if work>72_000_000:raise ValueError("Scaled actors exceed CPU surface budget")
    fxwork=sum(vfx.max_surface_side(e)**2*(1 if e["pixel"] else 4)*sum(vfx.active(e,i) for i in indices) for e in scene["effects"])
    if fxwork>120_000_000:raise ValueError("Effects exceed CPU surface budget; reduce size, duration or count")
    cache={};frames=[compose(scene,decoded,i,cache) for i in indices]
    meta=dict(name=scene["name"],fps=scene["fps"],loop=scene["loop"],size=[scene["width"],scene["height"]],
              pivot=[scene["width"]//2,scene["height"]//2],indices=indices)
    return frames,meta
