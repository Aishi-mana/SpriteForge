"""Deterministic, bounded procedural 2D effect layers for scenes."""
import math
import random
import re
from PIL import Image, ImageDraw
from . import modular

KINDS=("magic_circle","slash","impact","sparks","fire","smoke","lightning","aura")
MAX_EFFECTS=12

def validate(effects,count,actor_ids):
    if not isinstance(effects,list) or len(effects)>MAX_EFFECTS:raise ValueError("Scene supports up to 12 effects")
    out=[];seen=set()
    def n(e,k,lo,hi,default):return modular.integer(e.get(k,default),lo,hi,"effect "+k)
    for e in effects:
        if not isinstance(e,dict):raise ValueError("Invalid effect")
        key=e.get("id");kind=e.get("kind","sparks");name=e.get("name",kind)
        if not isinstance(key,str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}",key) or key in seen:raise ValueError("Invalid or duplicate effect ID")
        if kind not in KINDS or not isinstance(name,str) or not name.strip() or len(name)>60:raise ValueError("Invalid effect kind/name")
        seen.add(key)
        actor=e.get("actor")
        if actor is not None and (not isinstance(actor,str) or actor not in actor_ids):raise ValueError("Missing effect attachment actor")
        color=e.get("color","#76ddff")
        if not isinstance(color,str) or not re.fullmatch(r"#[0-9a-fA-F]{6}",color):raise ValueError("Invalid effect color")
        start=n(e,"start",0,count-1,0);end=n(e,"end",start,count-1,count-1)
        visible=e.get("visible",True);pixel=e.get("pixel",True)
        if not isinstance(visible,bool) or not isinstance(pixel,bool):raise ValueError("Invalid effect visibility/sampling")
        emission=e.get("emission","burst")
        if emission not in ("burst","continuous"):raise ValueError("Invalid particle emission")
        out.append(dict(id=key,name=name.strip(),kind=kind,actor=actor,color=color.lower(),start=start,end=end,
            x=n(e,"x",-2048,2048,0),y=n(e,"y",-2048,2048,0),z=n(e,"z",-100,100,0),
            radius=n(e,"radius",4,128,32),opacity=n(e,"opacity",0,100,100),rotation=n(e,"rotation",-180,180,0),
            particles=n(e,"particles",1,96,24),speed=n(e,"speed",10,200,100),
            gravity=n(e,"gravity",-100,100,0),seed=n(e,"seed",0,2147483647,0),
            visible=visible,pixel=pixel,emission=emission))
    return out

def active(e,frame):return e["visible"] and e["opacity"]>0 and e["start"]<=frame<=e["end"]

def phase(e,frame):
    return (frame-e["start"])/max(1,e["end"]-e["start"])

def surface(e,frame):
    """Return a transparent local cell and center pivot. Randomness is frame-order independent."""
    r=e["radius"];side=4*r+8;c=side/2
    ss=1 if e["pixel"] else 2
    im=Image.new("RGBA",(side*ss,side*ss));d=ImageDraw.Draw(im)
    t=phase(e,frame);kind=e["kind"];rng=random.Random(e["seed"])
    base=tuple(int(e["color"][i:i+2],16) for i in (1,3,5))
    rot=math.radians(e["rotation"]);speed=e["speed"]/100
    opacity=e["opacity"]/100
    def rgba(a,light=0):
        return tuple(round(v+(255-v)*light) for v in base)+(max(0,min(255,round(a*255*opacity))),)
    def p(x,y):return (round((c+x)*ss),round((c+y)*ss))
    def polar(rad,a):return (rad*math.cos(a),rad*math.sin(a))
    def line(points,a=1,width=1,light=0):
        d.line([p(*q) for q in points],fill=rgba(a,light),width=max(1,round(width*ss)),joint="curve")
    def disk(x,y,rad,a,light=0,outline=False,width=1):
        box=(*p(x-rad,y-rad),*p(x+rad,y+rad))
        if outline:d.ellipse(box,outline=rgba(a,light),width=max(1,round(width*ss)))
        else:d.ellipse(box,fill=rgba(a,light))
    def ring(rad,a,width=1,light=0):disk(0,0,rad,a,light,True,width)
    if kind=="magic_circle":
        a=.65+.35*math.sin(math.pi*t);angle=rot+t*math.tau*speed
        ring(r,a,max(1,r*.055));ring(r*.76,a*.8,max(1,r*.035))
        for offset in (0,math.pi/3):
            pts=[polar(r*.72,angle+offset+i*math.tau/3) for i in range(4)]
            line(pts,a,max(1,r*.035),.25)
        for i in range(12):
            q=angle+i*math.tau/12
            line([polar(r*.84,q),polar(r*.98,q)],a,max(1,r*.045),.4)
    elif kind=="slash":
        a=max(.05,math.sin(math.pi*(.1+.8*t)));angle=rot+(t-.5)*1.6*speed
        points=[polar(r*(.75+.24*math.sin(math.pi*i/24)),angle-1.35+2.7*i/24) for i in range(25)]
        line(points,a*.5,max(2,r*.23));line(points,a,max(1,r*.11),.35);line(points,a,max(1,r*.035),.85)
    elif kind=="impact":
        a=1-t*.95;rr=r*(.24+.9*t)
        ring(rr,a*.7,max(1,r*.07),.35)
        for i in range(8):
            q=rot+i*math.tau/8+rng.uniform(-.14,.14)
            line([polar(rr*.35,q),polar(rr*rng.uniform(.8,1.35),q)],a,max(1,r*.06),.55)
        disk(0,0,max(1,r*.24*(1-t)),a,.85)
    elif kind=="lightning":
        a=.5+.5*math.sin(math.pi*(.1+.8*t))
        # A reproducible flicker per frame, independent of previous renders.
        rng=random.Random(e["seed"]+7919*(frame-e["start"]))
        for j in range(3):
            q=rot+j*.65-.65
            pts=[]
            for i in range(9):
                u=(i/8-.5)*2*r;v=0 if i in (0,8) else rng.uniform(-.19,.19)*r
                pts.append((u*math.cos(q)-v*math.sin(q),u*math.sin(q)+v*math.cos(q)))
            line(pts,a*.45,max(2,r*.14));line(pts,a,max(1,r*.045),.9)
    elif kind=="aura":
        pulse=.87+.12*math.sin(t*math.tau*speed)
        ring(r*pulse,.7,max(1,r*.07));ring(r*(pulse-.14),.35,max(1,r*.045),.4)
        for i in range(min(e["particles"],32)):
            q=rng.random()*math.tau+rot+t*math.tau*speed
            x,y=polar(r*pulse*rng.uniform(.8,1.14),q)
            disk(x,y,max(1,r*.045),.65,.4)
    else:
        for i in range(e["particles"]):
            q=rng.uniform(-math.pi,math.pi)+rot
            delay=rng.random();velocity=rng.uniform(.35,1);size=rng.uniform(.035,.095)*r
            age=(t*speed+delay)%1 if e["emission"]=="continuous" else t*speed-delay*.22
            if not 0<=age<=1:continue
            a=max(0,1-age)
            if kind=="sparks":
                x,y=polar(r*velocity*age,q);y+=e["gravity"]/100*r*age*age
                line([(x,y),(x-math.cos(q)*r*.13,y-math.sin(q)*r*.13)],a,max(1,size*.65),.65)
            else:
                x=math.sin(q)*r*(.13+age*.35)*velocity
                y=-r*age*velocity+e["gravity"]/100*r*age*age
                if kind=="fire":disk(x,y,max(1,size*(1.3-age*.6)),a,.7*(1-age))
                else:disk(x,y,max(1,size*(1+age*2)),a*.45,.15)
    if ss>1:im=im.resize((side,side),Image.Resampling.LANCZOS)
    return im,(side//2,side//2)
