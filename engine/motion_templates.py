"""Portable motion plans. Timed descriptions are prompt conditioning, not pose tensors."""
from . import world

TEMPLATES={
 "breathing": ("Subtle breathing",[(0,"Original stance, eyes open, mouth closed"),(50,"Tiny chest rise, feet and hands stationary, unchanged expression"),(100,"Return to original stance")]),
 "alert": ("Alert idle",[(0,"Ready stance"),(50,"Small controlled shoulder tension, steady gaze"),(100,"Return to ready stance")]),
 "floating": ("Floating idle",[(0,"Original floating pose"),(50,"Gentle vertical rise, relaxed limbs"),(100,"Return to original height")]),
 "weapon_ready": ("Weapon-ready idle",[(0,"Original guard"),(50,"Subtle breathing, stable grip and weapon angle"),(100,"Original guard")]),
 "walk": ("Walk cycle",[(0,"Left foot forward"),(25,"Passing pose"),(50,"Right foot forward"),(75,"Passing pose"),(100,"Left foot forward")]),
 "run": ("Run cycle",[(0,"Left stride contact"),(25,"Airborne passing pose"),(50,"Right stride contact"),(75,"Airborne passing pose"),(100,"Left stride contact")]),
 "attack": ("Attack cycle",[(0,"Ready stance"),(25,"Windup"),(50,"Strike"),(75,"Follow-through"),(100,"Return to ready stance")]),
 "cast": ("Cast cycle",[(0,"Ready stance"),(30,"Gather energy"),(60,"Release spell"),(100,"Recover original stance")]),
}

def catalog():
    return [{"id":key,"label":name,"poses":[{"at":t,"pose":p} for t,p in poses]} for key,(name,poses) in TEMPLATES.items()]

def validate(value=None):
    if value is None:return []
    if not isinstance(value,list) or len(value)>12:raise ValueError("Motion plan must contain at most 12 poses")
    if not value:return []
    result=[]
    for p in value:
        if not isinstance(p,dict):raise ValueError("Invalid motion pose")
        at=world.integer(p.get("at"),0,100,"pose time percent")
        pose=world.label(p.get("pose"),"pose description",180)
        if not pose.strip():raise ValueError("Pose description is required")
        if result and at<=result[-1]["at"]:raise ValueError("Pose times must strictly increase")
        result.append({"at":at,"pose":pose})
    if result[0]["at"]!=0 or result[-1]["at"]!=100:raise ValueError("Motion plan needs 0% and 100% endpoints")
    return result

def describe(value):
    poses=validate(value)
    if not poses:return ""
    return "Ordered motion plan: "+"; ".join(str(p["at"])+"%: "+p["pose"] for p in poses)+". Follow this sequence gradually without abrupt transitions."
