"""Retarget custom-rig local animation and two-bone IK across character proportions."""
import math
import re
import copy
import numpy as np
from . import custom_skeleton as cs, custom_timeline as timeline, custom_ik as ik, modular

def size(value,label):
    if not isinstance(value,list) or len(value)!=2:raise ValueError("Invalid "+label+" dimensions")
    return tuple(modular.integer(v,1,1024,label+" dimension") for v in value)

def canonical(value):
    return re.sub(r"[^a-z0-9]","",value.lower())

def suggest(source,destination):
    src=cs.validate(source);dst=cs.validate(destination)
    used=set();mapping={};reasons={}
    # Stable IDs have priority over display names, regardless of tree order.
    for b in src["bones"]:
        if any(d["id"]==b["id"] for d in dst["bones"]):
            mapping[b["id"]]=b["id"];used.add(b["id"]);reasons[b["id"]]="id"
    for b in src["bones"]:
        if b["id"] in mapping:continue
        names={canonical(b["name"]),canonical(b["id"])}-{""}
        candidates=[d["id"] for d in dst["bones"] if d["id"] not in used and
                    names & {canonical(d["name"]),canonical(d["id"])}]
        if len(candidates)==1:
            mapping[b["id"]]=candidates[0];used.add(candidates[0]);reasons[b["id"]]="name"
    return {"mapping":mapping,"reasons":reasons}

def geometry(profile,dimensions,frame):
    p=timeline.pose(profile,frame)
    _,points,reports=ik.solve(p,dimensions,frame)
    return {"bones":points,"ik":reports,"size":list(dimensions)}

def transfer(source,destination,mapping,source_size,destination_size,transfer_ik=True,ik_mode="limb",frame=0):
    src=cs.validate(source);dst=cs.validate(destination)
    ss=size(source_size,"source");ds=size(destination_size,"destination")
    if "timeline" not in src:raise ValueError("Source rig has no animation timeline")
    clip=src["timeline"]
    if not clip["tracks"] and not any(c["enabled"] and (c["keys"] or c["locks"]) for c in src.get("ik",[])):
        raise ValueError("Source has no animated bone tracks or IK contacts")
    if not isinstance(transfer_ik,bool) or ik_mode not in ("limb","canvas"):raise ValueError("Invalid IK transfer option")
    frame=modular.integer(frame,0,clip["count"]-1,"preview frame")
    sb={b["id"]:b for b in src["bones"]};db={b["id"]:b for b in dst["bones"]}
    if not isinstance(mapping,dict) or not mapping or len(mapping)>32:raise ValueError("Map at least one source bone")
    if any(k not in sb or not isinstance(v,str) or v not in db for k,v in mapping.items()):
        raise ValueError("Mapping references missing source or destination bone")
    if len(set(mapping.values()))!=len(mapping):raise ValueError("A destination bone can be mapped only once")
    warnings=[];tracks={};unmapped=[];hierarchy=[];static_count=0
    for k,b in sb.items():
        d=mapping.get(k)
        if not d:
            if k in clip["tracks"]:unmapped.append(k)
            continue
        if (b["parent"] is None and db[d]["parent"] is not None) or (b["parent"] is not None and mapping.get(b["parent"])!=db[d]["parent"]):
            hierarchy.append(k)
        if k in clip["tracks"]:
            tracks[d]=copy.deepcopy(clip["tracks"][k])
        elif b["angle"]!=db[d]["angle"]:
            # Preserve source fallback without mutating destination manual pose.
            tracks[d]=[{"frame":0,"angle":b["angle"],"curve":"linear"}];static_count+=1
    if unmapped:warnings.append("Unmapped animated bones: "+", ".join(unmapped))
    if hierarchy:warnings.append("Parent mapping differs or is incomplete for: "+", ".join(hierarchy)+". Local rotations may not reproduce the same world-space pose.")
    _,sseg=cs.transforms(src,ss);_,dseg=cs.transforms(dst,ds)
    chains=[];skipped=[];contacts=0
    for c in src.get("ik",[]):
        end=c["end"];upper=sb[end]["parent"];de=mapping.get(end);du=mapping.get(upper)
        if not transfer_ik or not de or not du or db[de]["parent"]!=du:
            skipped.append(end);continue
        # Map world-space offsets relative to the REST upper joint. A single
        # transform for every target and lock preserves fixed contacts.
        sa,sj=sseg[upper];_,st=sseg[end]
        da,dj=dseg[du];_,dt=dseg[de]
        sl=float(np.linalg.norm(sj-sa)+np.linalg.norm(st-sj))
        dl=float(np.linalg.norm(dj-da)+np.linalg.norm(dt-dj))
        a=math.radians(ik.angle(dj-da)-ik.angle(sj-sa))
        rot=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
        def adapt(p):
            if ik_mode=="canvas":return list(p)
            result=((da+rot@(np.array(p)*ss-sa)*(dl/sl))/ds).tolist()
            return ik.target(result)
        try:
            new={**copy.deepcopy(c),"end":de,"target":adapt(c["target"])}
            new["keys"]=[{**k,"target":adapt(k["target"])} for k in c["keys"]]
            new["locks"]=[{**l,"target":adapt(l["target"])} for l in c["locks"]]
        except ValueError:
            skipped.append(end);warnings.append("IK chain "+end+" exceeds target bounds after scaling; try canvas mode or revise mapping.")
            continue
        chains.append(new);contacts+=len(new["locks"])
    if skipped:warnings.append("IK chains not transferred: "+", ".join(skipped))
    animated=sum(1 for k in clip["tracks"] if k in mapping)
    if not animated and not any(c["enabled"] and (c["keys"] or c["locks"]) for c in chains):
        raise ValueError("No animated tracks or IK contacts can transfer with this mapping")
    if len(dst.get("ik",[])):warnings.append("Destination IK chains will be replaced by the transferred set.")
    candidate=cs.validate({**dst,"timeline":{**clip,"tracks":tracks},"ik":chains})
    max_error=0.;contact_error=0.;unreached=0;locked_misses=0
    # Bounded by 32 frames and eight chains. No textured rendering required.
    for i in range(clip["count"]):
        _,_,reports=ik.solve(timeline.pose(candidate,i),ds,i)
        for r in reports:
            max_error=max(max_error,r["error"])
            if r["error"]>.5:unreached+=1
            if r["locked"]:
                contact_error=max(contact_error,r["error"])
                if r["error"]>.5:locked_misses+=1
    if unreached:warnings.append("Some destination IK endpoints miss their targets (including strength/constraint effects). Review the residuals before exporting.")
    report={"mapped":len(mapping),"source_bones":len(sb),"destination_bones":len(db),
            "animated_tracks":animated,"static_tracks":static_count,"keys":sum(map(len,tracks.values())),
            "unmapped_tracks":unmapped,"hierarchy_mismatches":hierarchy,"ik_chains":len(chains),
            "contact_ranges":contacts,"skipped_ik":skipped,"ik_misses":unreached,
            "locked_misses":locked_misses,"max_error":round(max_error,3),"max_contact_error":round(contact_error,3),
            "warnings":warnings}
    return {"profile":candidate,"report":report,"frame":frame,
            "source":geometry(src,ss,frame),"destination":geometry(candidate,ds,frame)}

def inspect(source,destination,mapping,source_size,destination_size,transfer_ik=True,ik_mode="limb",frame=0):
    return transfer(source,destination,mapping,source_size,destination_size,transfer_ik,ik_mode,frame)
