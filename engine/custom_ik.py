"""Two-bone analytical IK and frame-indexed canvas-space contact locks."""
import math
import numpy as np
from . import modular

MAX_CHAINS=8
CURVES=("linear","ease","step")

def num(v,lo,hi,label):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError("Invalid "+label)
    return float(v)

def target(v):
    if not isinstance(v,list) or len(v)!=2:raise ValueError("Invalid IK target")
    return [num(x,-.5,1.5,"IK coordinate") for x in v]

def validate(chains,bones,count):
    if not isinstance(chains,list) or len(chains)>MAX_CHAINS:raise ValueError("At most eight IK chains")
    by={b["id"]:b for b in bones};used=set();out=[]
    for c in chains:
        if not isinstance(c,dict):raise ValueError("Invalid IK chain")
        end=c.get("end")
        if not isinstance(end,str) or end not in by or by[end]["parent"] is None:raise ValueError("IK requires a child bone and its parent")
        upper=by[end]["parent"]
        if end in used or upper in used:raise ValueError("IK chains cannot share controlled bones")
        used.update((end,upper))
        enabled=c.get("enabled",True)
        if not isinstance(enabled,bool):raise ValueError("Invalid IK enabled flag")
        bend=c.get("bend",1)
        if isinstance(bend,bool) or bend not in (-1,1):raise ValueError("Invalid IK bend direction")
        lo=num(c.get("min_bend",0),0,179,"minimum bend");hi=num(c.get("max_bend",170),0,179,"maximum bend")
        if lo>hi:raise ValueError("Minimum bend exceeds maximum")
        keys=c.get("keys",[]);locks=c.get("locks",[])
        if not isinstance(keys,list) or len(keys)>count or not isinstance(locks,list) or len(locks)>count:raise ValueError("Invalid IK timeline entries")
        clean_keys=[];seen=set()
        for k in keys:
            if not isinstance(k,dict):raise ValueError("Invalid IK key")
            frame=modular.integer(k.get("frame"),0,count-1,"IK key frame")
            if frame in seen or k.get("curve","linear") not in CURVES:raise ValueError("Invalid or duplicate IK key")
            seen.add(frame);clean_keys.append(dict(frame=frame,target=target(k.get("target")),curve=k.get("curve","linear")))
        clean_locks=[];occupied=set()
        for l in locks:
            if not isinstance(l,dict):raise ValueError("Invalid foot lock")
            start=modular.integer(l.get("start"),0,count-1,"lock start");end_frame=modular.integer(l.get("end"),start,count-1,"lock end")
            frames=set(range(start,end_frame+1))
            if occupied&frames:raise ValueError("Foot locks cannot overlap within one chain")
            occupied.update(frames);clean_locks.append(dict(start=start,end=end_frame,target=target(l.get("target"))))
        out.append(dict(end=end,enabled=enabled,target=target(c.get("target")),bend=int(bend),
                        strength=num(c.get("strength",1),0,1,"IK strength"),min_bend=lo,max_bend=hi,
                        keys=sorted(clean_keys,key=lambda k:k["frame"]),locks=sorted(clean_locks,key=lambda l:l["start"])))
    # Ancestor chains solve before descendants.
    order={b["id"]:i for i,b in enumerate(bones)}
    return sorted(out,key=lambda c:order[by[c["end"]]["parent"]])

def at_frame(c,frame):
    if frame is None:return c["target"],False
    for l in c["locks"]:
        if l["start"]<=frame<=l["end"]:return l["target"],True
    keys=c["keys"]
    if not keys:return c["target"],False
    if frame<=keys[0]["frame"]:return keys[0]["target"],False
    if frame>=keys[-1]["frame"]:return keys[-1]["target"],False
    for a,b in zip(keys,keys[1:]):
        if frame==b["frame"]:return b["target"],False
        if a["frame"]<=frame<b["frame"]:
            t=(frame-a["frame"])/(b["frame"]-a["frame"])
            if a["curve"]=="step":t=0
            elif a["curve"]=="ease":t=t*t*(3-2*t)
            return [x+(y-x)*t for x,y in zip(a["target"],b["target"])],False
    return c["target"],False

def wrap(a):return (a+180)%360-180

def angle(v):return math.degrees(math.atan2(v[1],v[0]))

def apply(M,p):return (M@np.r_[p,1])[:2]

def solve(profile,size,frame=None):
    from . import custom_skeleton as cs
    p={**profile,"bones":[dict(b) for b in profile["bones"]]}
    by={b["id"]:b for b in p["bones"]};reports=[]
    for c in p.get("ik",[]):
        if not c["enabled"]:continue
        end=by[c["end"]];upper=by[end["parent"]]
        mat,seg=cs.transforms(p,size)
        a,j=seg[upper["id"]];_,b=seg[end["id"]]
        l1=float(np.linalg.norm(j-a));l2=float(np.linalg.norm(b-j))
        parent=np.eye(3) if upper["parent"] is None else mat[upper["parent"]]
        origin=apply(parent,a)
        xy,locked=at_frame(c,frame);goal=np.array(xy)*size
        v=goal-origin;dist=float(np.linalg.norm(v))
        direction=angle(v) if dist>1e-9 else angle(apply(mat[upper["id"]],j)-origin)
        cosine=np.clip((dist*dist-l1*l1-l2*l2)/(2*l1*l2),-1,1)
        bend=c["bend"]*float(np.clip(math.degrees(math.acos(cosine)),c["min_bend"],c["max_bend"]))
        rad=math.radians(bend)
        theta=direction-math.degrees(math.atan2(l2*math.sin(rad),l1+l2*math.cos(rad)))
        parent_angle=angle(parent[:2,0])
        u=wrap(theta-parent_angle-angle(j-a))
        lower=wrap(bend+angle(j-a)-angle(b-j))
        strength=c["strength"]
        upper["angle"]=wrap(upper["angle"]+strength*wrap(u-upper["angle"]))
        end["angle"]=wrap(end["angle"]+strength*wrap(lower-end["angle"]))
        reports.append(dict(end=end["id"],target=goal.tolist(),locked=locked))
    mat,seg=cs.transforms(p,size)
    for r in reports:
        tip=apply(mat[r["end"]],seg[r["end"]][1])
        r["tip"]=tip.tolist();r["error"]=float(np.linalg.norm(tip-r["target"]))
    points={k:[apply(mat[k],a).tolist(),apply(mat[k],b).tolist()] for k,(a,b) in seg.items()}
    return p,points,reports
