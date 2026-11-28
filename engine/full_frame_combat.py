"""Authored game animation metadata; coordinates are sprite canvas pixels."""
from . import world
PHASES=("anticipation","active","recovery","neutral")
EVENTS=("impact","cast","release","footstep","sound","vfx","combo","custom")

def validate(value,count,w,h):
    if value is None:value=[]
    if not isinstance(value,list) or len(value)>count:raise ValueError("Invalid combat frame metadata")
    n=world.integer;out=[];seen=set()
    for item in value:
        if not isinstance(item,dict):raise ValueError("Invalid combat frame")
        frame=n(item.get("frame"),0,count-1,"combat frame")
        if frame in seen:raise ValueError("Duplicate combat frame")
        seen.add(frame)
        phase=item.get("phase","neutral")
        if phase not in PHASES:raise ValueError("Invalid combat phase")
        event=item.get("event","")
        if event not in ("",*EVENTS):raise ValueError("Invalid animation event")
        box=item.get("hitbox");anchor=item.get("anchor");root=item.get("root",[0,0])
        def point(p,lo_x,hi_x,lo_y,hi_y,label):
            if not isinstance(p,list) or len(p)!=2:raise ValueError("Invalid "+label)
            return [n(p[0],lo_x,hi_x,label+" X"),n(p[1],lo_y,hi_y,label+" Y")]
        if box is not None:
            if not isinstance(box,list) or len(box)!=4:raise ValueError("Invalid hitbox")
            x,y=point(box[:2],0,w-1,0,h-1,"hitbox")
            box=[x,y,n(box[2],1,w-x,"hitbox width"),n(box[3],1,h-y,"hitbox height")]
        if anchor is not None:anchor=point(anchor,0,w-1,0,h-1,"effect anchor")
        root=point(root,-2048,2048,-2048,2048,"root displacement")
        out.append(dict(frame=frame,phase=phase,event=event,label=world.label(item.get("label",""),"event label",80,True),hitbox=box,anchor=anchor,root=root))
    return sorted(out,key=lambda v:v["frame"])
