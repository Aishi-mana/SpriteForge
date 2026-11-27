"""Phase 61P-A: reusable standalone procedural effect recipes."""
from . import scenes, vfx, modular

PRESETS = (
    ("slash","Sword slash","#9ceaff",8,False,"burst"),
    ("slash_horizontal","Horizontal slash","#9ceaff",10,False,"burst"),
    ("slash_vertical","Vertical slash","#9ceaff",10,False,"burst"),
    ("slash_diagonal","Diagonal slash","#9ceaff",10,False,"burst"),
    ("slash_crescent","Crescent slash","#b38cff",12,False,"burst"),
    ("slash_spin","Circular slash","#79f5d0",16,False,"burst"),
    ("slash_double","Double slash","#ffbe7d",16,False,"burst"),
    ("weapon_trail","Weapon trail","#b8e8ff",12,False,"burst"),
    ("fireball","Fireball","#ff7838",16,False,"burst"),
    ("energy_bolt","Energy bolt","#65d7ff",12,False,"burst"),
    ("ice_shard","Ice shard","#a4eaff",16,False,"burst"),
    ("magic_orb","Magic orb","#b994ff",20,False,"burst"),
    ("explosion","Explosion","#ff9345",12,False,"burst"),
    ("shockwave","Shockwave","#f6e3bb",12,False,"burst"),
    ("frost_burst","Frost burst","#a4eaff",12,False,"burst"),
    ("impact","Impact flash","#ffe29b",8,False,"burst"),
    ("sparks","Sparks","#ffc861",16,False,"burst"),
    ("fire","Fire","#ff793c",24,True,"continuous"),
    ("smoke","Smoke","#9299ab",24,True,"continuous"),
    ("lightning","Lightning","#8ccfff",12,False,"burst"),
    ("aura","Aura","#65e0af",24,True,"continuous"),
    ("magic_circle","Magic circle","#a78bfa",24,True,"continuous"),
)

def presets():
    return [validate(dict(name=name,kind=kind,color=color,count=count,loop=loop,emission=emission,sweep=360 if kind=="slash_spin" else 210 if kind=="slash_crescent" else 150 if kind=="weapon_trail" else 180)) for kind,name,color,count,loop,emission in PRESETS]

def validate(value):
    if not isinstance(value,dict) or value.get("version",1)!=1:raise ValueError("Invalid VFX recipe")
    count=modular.integer(value.get("count",16),2,32,"effect frame count")
    fps=modular.integer(value.get("fps",12),1,60,"effect FPS")
    loop=value.get("loop",False)
    if not isinstance(loop,bool):raise ValueError("Invalid effect loop")
    raw={**value,"id":"effect","actor":None,"x":0,"y":0,"z":0,"visible":True}
    e=vfx.validate([raw],count,set())[0]
    w,h,_,_=vfx.effect_canvas(e)
    if max(w,h)>1024 or w*h*count>12_000_000:raise ValueError("Reduce radius or frame count for preview")
    return {**{k:e[k] for k in ("kind","name","color","radius","opacity","rotation","speed","particles","gravity","seed","pixel","emission","start","end","sweep","thickness","trail","glow","path","travel_x","travel_y","arc_height","impact_kind","impact_frames","impact_scale","impact_color","artwork","artwork_opacity","keyframes")},"version":1,"count":count,"fps":fps,"loop":loop}

def scene(value):
    r=validate(value);w,h,x,y=vfx.effect_canvas(r)
    effect={**r,"id":"effect","actor":None,"x":x,"y":y,"z":0,"visible":True}
    return {"version":1,"name":r["name"],"width":w,"height":h,"count":r["count"],"fps":r["fps"],"loop":r["loop"],"actors":[],"effects":[effect]}

def render(value,frame=None,preview=True):
    return scenes.render(scene(value),frame,preview)
