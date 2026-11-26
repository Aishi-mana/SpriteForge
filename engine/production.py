"""Batch character recipes and non-destructive per-project animation exports."""
import math
import secrets
import uuid
from . import projects, modular, custom_skeleton, custom_timeline, custom_retarget, custom_cleanup, exporter

def text(v,limit,label,required=False):
    if not isinstance(v,str) or len(v)>limit or (required and not v.strip()):raise ValueError("Invalid "+label)
    return v.strip()

def plan(body):
    if not isinstance(body,dict):raise ValueError("Invalid production recipe")
    name=text(body.get("name","batch"),60,"batch name",True)
    common=body.get("params")
    if not isinstance(common,dict):raise ValueError("Missing generation settings")
    rows=body.get("characters")
    if not isinstance(rows,list) or not 1<=len(rows)<=24:raise ValueError("Choose 1–24 characters")
    base=modular.integer(common.get("seed",-1),-1,2147483647,"seed")
    if base<0:base=secrets.randbelow(2147483648-len(rows))
    prefix=text(common.get("prompt",""),2000,"common prompt")
    result=[];names=set()
    for i,row in enumerate(rows):
        if not isinstance(row,dict):raise ValueError("Invalid character row")
        label=text(row.get("name"),60,"character name",True)
        if label.casefold() in names:raise ValueError("Duplicate character name")
        names.add(label.casefold())
        detail=text(row.get("prompt"),2000,"character prompt",True)
        p={**common,"prompt":", ".join(v for v in (prefix,detail) if v),"seed":(base+i)%2147483648,"kind":"sprite","n":1}
        if len(p["prompt"])>3000:raise ValueError("Combined prompt exceeds 3000 characters")
        result.append({"name":label,"params":p,"index":i})
    return name,result

def animation(root,body):
    target=projects.load(root,body.get("target"))
    dst=target.get("custom_skeleton");image=target.get("images",{}).get("customrig")
    if not dst or not image:raise ValueError("Target project needs a fitted custom rig")
    dst=custom_skeleton.validate(dst)
    pad=int(target.get("settings",{}).get("csPad",32))
    source_name=body.get("source")
    warnings=[];report=None
    if source_name:
        src=projects.load(root,source_name)
        sp=src.get("custom_skeleton");si=src.get("images",{}).get("customrig")
        if not sp or not si:raise ValueError("Source project needs a custom animation")
        mapping=custom_retarget.suggest(sp,dst)["mapping"]
        if body.get("mapping") is not None:mapping=body["mapping"]
        ret=custom_retarget.transfer(sp,dst,mapping,list(modular.decode(si).size),list(modular.decode(image).size),
                                    body.get("transfer_ik",True),body.get("ik_mode","limb"))
        dst=ret["profile"];report=ret["report"];warnings=report["warnings"]
        # Do not silently export incomplete or unreachable retargets.
        if warnings and not body.get("allow_warnings",False):
            return {"status":"review","target":target["name"],"report":report,"warnings":warnings}
    frames,meta=custom_timeline.render(image,dst,pad,preview=False)
    if body.get("cleanup",False) and not source_name:frames=custom_cleanup.apply(frames,meta,target.get("custom_cleanup"))
    # Unique run suffix avoids overwriting any prior export.
    run=projects.safe_name(target["name"])[:32]+"_"+uuid.uuid4().hex[:10]
    options=body.get("options") or {}
    if not isinstance(options,dict):raise ValueError("Invalid export options")
    out=exporter.export_pack([{**meta,"frames":frames}],dict(options,crop=False,uniform=True,smooth=not dst["pixel"]),run,root)
    return {"status":"done","target":target["name"],"report":report,"warnings":warnings,**out}
