"""Portable independent character sheets and shared interaction metadata."""
import io
import json
import math
import zipfile
from PIL import Image
from . import scenes

def _json(z,path,value):
    z.writestr(path,json.dumps(value,ensure_ascii=False,indent=2))

def _image(z,path,image,fmt):
    buf=io.BytesIO()
    if fmt=="WEBP":image.save(buf,fmt,lossless=True,exact=True)
    else:image.save(buf,fmt)
    z.writestr(path,buf.getvalue())

def _contact(value):
    if value is None:return None
    if not isinstance(value,dict):raise ValueError("Invalid contact metadata")
    label=value.get("label","Custom")
    if label not in ("Hands","Face / lips","Chest / shoulder","Waist","Custom"):raise ValueError("Invalid contact label")
    anchors=value.get("anchors")
    if not isinstance(anchors,dict):raise ValueError("Invalid contact anchors")
    result={}
    for key in ("A","B"):
        p=anchors.get(key)
        if not isinstance(p,list) or len(p)!=2:raise ValueError("Invalid contact anchor")
        result[key]=[scenes.integer(v,-2048,2048,"contact offset") for v in p]
    return dict(label=label,anchors=result,space="source pixels relative to unmirrored pivot")

def _stages(value,count):
    if value is None:return {"enabled":False}
    if not isinstance(value,dict):raise ValueError("Invalid stage metadata")
    enabled=scenes.boolean(value.get("enabled",False),"stages enabled")
    preset=value.get("preset","custom")
    if preset not in ("custom","hands","hug","kiss","handshake","dance","grapple"):raise ValueError("Invalid interaction preset")
    if not enabled:return dict(enabled=False,preset=preset)
    l=scenes.integer(value.get("loopStart"),1,count-2,"loop start")
    e=scenes.integer(value.get("exitStart"),l+1,count-1,"exit start")
    return dict(enabled=True,preset=preset,enter=[0,l],loop=[l,e],exit=[e,count],range_end="exclusive",release="next loop boundary, or end of enter when requested during enter")

def export(body):
    if not isinstance(body,dict):raise ValueError("Invalid pair export")
    scene,decoded=scenes.validate(body.get("scene"))
    if len(scene["actors"])!=2 or {a["id"] for a in scene["actors"]}!={"actor_A","actor_B"} or scene["effects"]:
        raise ValueError("Export requires exactly two independent actors and no scene effects")
    fmt=body.get("format","png")
    if fmt not in ("png","webp"):raise ValueError("Choose PNG or WebP")
    contact=_contact(body.get("contact"))
    stages=_stages(body.get("stages"),scene["count"])
    manifest=dict(format="spriteforge-interaction",version=1,name=scene["name"],canvas=[scene["width"],scene["height"]],
        fps=scene["fps"],count=scene["count"],loop=scene["loop"],coordinate_space="scene pixels, top-left origin, y down",
        stages=stages,contact=contact,actors=[],timeline=[],depth_order="ascending depth; ties use actors array order")
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
        for a in scene["actors"]:
            images=decoded[a["id"]];w,h=images[0].size;n=len(images)
            cols=min(n,max(1,4096//w),max(1,math.ceil(math.sqrt(n*h/w))))
            rows=(n+cols-1)//cols
            # Keep each sheet within common GPU texture limits. Use multiple pages if needed.
            per_page=cols*max(1,4096//h)
            if w>4096 or h>4096:raise ValueError("Source frame exceeds 4096px texture limit")
            stem="character_"+a["id"][-1]
            entries=[];pages=[]
            for start in range(0,n,per_page):
                part=images[start:start+per_page];pc=min(cols,len(part));pr=(len(part)+pc-1)//pc
                sheet=Image.new("RGBA",(pc*w,pr*h))
                page=stem+("" if n<=per_page else "_"+str(len(pages)))+"."+fmt
                for j,im in enumerate(part):
                    x=(j%pc)*w;y=(j//pc)*h
                    sheet.paste(im,(x,y))
                    entries.append(dict(index=start+j,page=page,rect=[x,y,w,h]))
                _image(z,page,sheet,fmt.upper());pages.append(page)
            clip=a["clip"]
            atlas=dict(format="spriteforge-actor-atlas",version=1,name=clip["name"],fps=clip["fps"],loop=clip["loop"],pixel=clip["pixel"],pivot=clip["pivot"],cell=[w,h],pages=pages,frames=entries)
            _json(z,stem+".json",atlas)
            manifest["actors"].append(dict(id=a["id"],name=a["name"],atlas=stem+".json",pivot=clip["pivot"],pixel=clip["pixel"],source_fps=clip["fps"],source_count=n,scale=a["scale"]/100,flip=a["flip"],opacity=a["opacity"]/100))
        for i in range(scene["count"]):
            actors={}
            for a in scene["actors"]:
                index=scenes.frame_index(a,i,scene["fps"])
                x,y=scenes.position(a,i)
                actors[a["id"]]=dict(source_frame=index,visible=index is not None and a["opacity"]>0,position=[x,y],depth=scenes.depth(a,i))
            manifest["timeline"].append(dict(frame=i,actors=actors))
        _json(z,"interaction.json",manifest)
        z.writestr("README.txt","SpriteForge paired interaction v1\nLoad each actor atlas separately. Draw the source frame using its pivot at the timeline position, applying flip about the pivot, scale and opacity. Sort visible actors by depth, stable on ties. All indices are zero-based; stage end indices are exclusive. Source sheets are untrimmed and unmirrored. If stages are enabled, play enter once, repeat loop, then play exit once on release at a loop boundary. Add your own world origin and runtime controller. PNG and lossless WebP preserve transparency.\n")
    return buf.getvalue()
