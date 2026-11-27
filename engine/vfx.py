"""Deterministic, bounded procedural 2D effect layers for scenes."""
import math
import random
import re
from PIL import Image, ImageDraw
from . import modular, vfx_art, vfx_keyframes

SLASH_KINDS=("slash_horizontal","slash_vertical","slash_diagonal","slash_crescent","slash_spin","slash_double","weapon_trail")
PROJECTILE_KINDS=("fireball","energy_bolt","ice_shard","magic_orb")
PATHS=("linear","arc","ease_in","ease_out")
BURST_KINDS=("explosion","shockwave","frost_burst")
IMPACT_KINDS=("none","impact")+BURST_KINDS
KINDS=("magic_circle","slash","impact","sparks","fire","smoke","lightning","aura")+SLASH_KINDS+PROJECTILE_KINDS+BURST_KINDS
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
        path=e.get("path","linear")
        if path not in PATHS:raise ValueError("Invalid projectile path")
        impact_kind=e.get("impact_kind","none")
        if impact_kind not in IMPACT_KINDS:raise ValueError("Invalid impact kind")
        impact_frames=n(e,"impact_frames",1,30,6)
        impact_scale=n(e,"impact_scale",50,200,150)
        impact_color=e.get("impact_color",color)
        if not isinstance(impact_color,str) or not re.fullmatch(r"#[0-9a-fA-F]{6}",impact_color):raise ValueError("Invalid impact color")
        if impact_kind!="none" and (kind not in PROJECTILE_KINDS or end-start+1<impact_frames+2):
            raise ValueError("Impact chain needs a projectile and at least two flight frames")
        out.append(dict(id=key,name=name.strip(),kind=kind,actor=actor,color=color.lower(),start=start,end=end,
            x=n(e,"x",-2048,2048,0),y=n(e,"y",-2048,2048,0),z=n(e,"z",-100,100,0),
            radius=n(e,"radius",4,128,32),opacity=n(e,"opacity",0,100,100),rotation=n(e,"rotation",-180,180,0),
            particles=n(e,"particles",1,96,24),speed=n(e,"speed",10,200,100),
            gravity=n(e,"gravity",-100,100,0),seed=n(e,"seed",0,2147483647,0),
            visible=visible,pixel=pixel,emission=emission,
            face_actor=_face_actor(e,actor),
            sweep=n(e,"sweep",30,360,180),thickness=n(e,"thickness",5,70,24),
            trail=n(e,"trail",0,100,45),glow=n(e,"glow",0,100,60),path=path,
            travel_x=n(e,"travel_x",-512,512,96),travel_y=n(e,"travel_y",-512,512,0),
            arc_height=n(e,"arc_height",-256,256,48),impact_kind=impact_kind,
            impact_frames=impact_frames,impact_scale=impact_scale,impact_color=impact_color.lower(),
            artwork=vfx_art.validate(e.get("artwork")),artwork_opacity=n(e,"artwork_opacity",0,100,100),
            keyframes=vfx_keyframes.validate(e.get("keyframes",[]),end-start+1)))
    return out

def _face_actor(e,actor):
    value=e.get("face_actor",False)
    if not isinstance(value,bool) or (value and actor is None):raise ValueError("Facing mirror needs an attached actor")
    return value

def active(e,frame):return e["visible"] and e["opacity"]>0 and e["start"]<=frame<=e["end"] and keyframe(e,frame)["opacity"]>0

def phase(e,frame):
    return (frame-e["start"])/max(1,e["end"]-e["start"])

def flight_end(e):
    return e["end"]-(e.get("impact_frames",6) if e.get("impact_kind","none")!="none" else 0)

def impact_radius(e):
    return min(128,max(4,round(e["radius"]*e.get("impact_scale",150)/100)))

def stage(e,frame):
    """Non-recursive impact stage; the flight and burst share one recipe and clock."""
    if e["kind"] not in PROJECTILE_KINDS or e.get("impact_kind","none")=="none":return e
    end=flight_end(e)
    if frame<=end:return {**e,"end":end,"impact_kind":"none"}
    return {**e,"kind":e["impact_kind"],"start":end+1,"radius":impact_radius(e),
            "color":e.get("impact_color",e["color"]),"impact_kind":"none","artwork":None}

def keyframe(e,frame):
    return vfx_keyframes.sample(e.get("keyframes",[]),frame-e["start"])

def frame_style(e,frame):
    k=keyframe(e,frame)
    s=stage(e,frame)
    return {**s,"radius":min(128,max(4,round(s["radius"]*k["scale"]/100))),
            "rotation":s["rotation"]+k["rotation"],
            "opacity":round(s["opacity"]*k["opacity"]/100),
            "color":vfx_keyframes.tint(s["color"],k["color"]),"artwork_tint":k["color"]}

def max_surface_side(e):
    if not e.get("keyframes"):
        r=max(e["radius"],impact_radius(e)) if e.get("impact_kind","none")!="none" else e["radius"]
        return 4*r+8
    return max(4*frame_style(e,i)["radius"]+8 for i in range(e["start"],e["end"]+1))

def motion_offset(e,frame):
    x,y=projectile_offset(e,frame)
    k=keyframe(e,frame)
    return x+k["dx"],y+k["dy"]

def projectile_offset(e,frame):
    """Integer world-space translation; endpoints are exact and frame-order independent."""
    if e["kind"] not in PROJECTILE_KINDS:return (0,0)
    t=max(0,min(1,(frame-e["start"])/max(1,flight_end(e)-e["start"])))
    path=e.get("path","linear")
    u=t*t if path=="ease_in" else 1-(1-t)**2 if path=="ease_out" else t
    arc=4*u*(1-u)*e.get("arc_height",48) if path=="arc" else 0
    return (round(e.get("travel_x",96)*u),round(e.get("travel_y",0)*u-arc))

def effect_canvas(e):
    """Fixed canvas enclosing every local cell along the sampled path."""
    side=max_surface_side(e)
    offsets=[motion_offset(e,i) for i in range(e["start"],e["end"]+1)]
    xs,ys=zip(*offsets)
    return (side+max(xs)-min(xs),side+max(ys)-min(ys),side//2-min(xs),side//2-min(ys))

def surface(e,frame):
    """Return a transparent local cell and center pivot. Randomness is frame-order independent."""
    original=e
    e=frame_style(e,frame)
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
    elif kind in SLASH_KINDS:
        # Sample inside the envelope for very short active ranges.
        if e["end"]-e["start"]<=1:t=.35+.3*t
        # Keep the original Phase 47 slash untouched. New crescents use tapered
        # ribbons, a traveling leading edge, and deterministic fading echoes.
        offset={"slash_horizontal":0,"slash_vertical":-math.pi/2,"slash_diagonal":-math.pi/4,
                "slash_crescent":0,"slash_spin":0,"slash_double":0,"weapon_trail":0}[kind]
        sweep=math.radians(e.get("sweep",180))
        thick=r*e.get("thickness",24)/100
        tail=e.get("trail",45)/100
        glow=e.get("glow",60)/100
        def ribbon(u, angle_offset=0, alpha=1):
            if not 0<=u<=1:return
            # Wind-up, strike and dissipate. Progress never wraps at the end.
            strength=min(1,u/.18)*min(1,(1-u)/.30)
            if strength<=0:return
            extent=sweep*min(1,.15+u*2.8)
            center=rot+offset+angle_offset+sweep*(u-.5)*speed
            if kind=="slash_spin":center=rot+angle_offset+math.tau*u*speed
            a0=center-extent*.85
            outer=[];inner=[];core=[]
            for j in range(49):
                s=j/48;ang=a0+extent*s
                taper=math.sin(math.pi*s)**.65
                rad=r*(.87+.10*s)
                if kind=="weapon_trail":rad=r*(.48+.50*s)
                width=thick*taper*strength
                outer.append(p(*polar(rad+width*.55,ang)))
                inner.append(p(*polar(max(0,rad-width*.55),ang)))
                core.append(p(*polar(rad+width*.25,ang)))
            # Each echo is drawn first, followed by a luminous leading ribbon.
            a=alpha*strength
            if glow>0:
                d.line(outer,fill=rgba(a*glow*.30),width=max(1,round(thick*.45*ss)),joint="curve")
            d.polygon(outer+inner[::-1],fill=rgba(a,.12))
            d.line(core,fill=rgba(a*.95,.35+.6*glow),width=max(1,round(thick*.13*ss)),joint="curve")
        passes=[(t,0)]
        if kind=="slash_double":passes=[(t*2.1,-.55),((t-.42)*2.0,math.pi+.55)]
        for u,ang in passes:
            if tail>0:
                for j in (3,2,1):
                    ribbon(u-j*.075,ang,tail*(4-j)/5)
            ribbon(u,ang)
        # Seeded sparks are part of the effect, not global particle simulation.
        for i in range(min(e["particles"],24)):
            ang=rot+offset+rng.uniform(-sweep/2,sweep/2)
            v=rng.uniform(.65,1.35);age=t-rng.uniform(.12,.4)
            if 0<age<.6:
                rad=r*v*(.75+age*.5);x,y=polar(rad,ang)
                disk(x,y,max(.6,r*.025),(1-age/.6)*tail,.65)
    elif kind in PROJECTILE_KINDS:
        # Heading follows the sampled motion, plus optional artwork rotation.
        before=motion_offset(original,max(original["start"],frame-1))
        after=motion_offset(original,min(flight_end(original),frame+1))
        dx,dy=after[0]-before[0],after[1]-before[1]
        heading=(math.atan2(dy,dx) if dx or dy else math.atan2(e.get("travel_y",0),e.get("travel_x",96)))+rot
        def q(x,y):return (x*math.cos(heading)-y*math.sin(heading),x*math.sin(heading)+y*math.cos(heading))
        tail=e.get("trail",45)/100
        glow=e.get("glow",60)/100
        pulse=.9+.1*math.sin(t*math.tau*speed)
        core=r*(.35 if kind=="energy_bolt" else .48)*pulse
        if tail:
            for j in range(12,0,-1):
                u=j/12;cx,cy=q(-r*u*1.55,0)
                disk(cx,cy,max(1,core*(1-u*.85)),tail*(1-u*.88)*.65,.2)
            for j in range(min(24,e["particles"])):
                u=rng.uniform(.25,1.6);wiggle=rng.uniform(-.35,.35)*r*math.sin(t*math.tau*speed+j)
                cx,cy=q(-r*u,wiggle)
                disk(cx,cy,max(.6,r*.025),tail*(1-u/1.8)*.8,.65)
        if glow:disk(0,0,core*1.45,glow*.32,.2)
        if kind=="ice_shard":
            d.polygon([p(*q(x*core,y*core)) for x,y in ((1.6,0),(.1,-.75),(-1,0),(.1,.75))],fill=rgba(.95,.25))
            line([q(-core,0),q(core*1.6,0)],.95,max(1,r*.05),.9)
        elif kind=="energy_bolt":
            line([q(-core,0),q(core*1.4,0)],.9,max(2,core),.35)
            line([q(-core*.7,0),q(core*1.1,0)],1,max(1,core*.32),.9)
        else:
            disk(0,0,core,.95,.2)
            disk(*q(core*.16,0),core*.6,1,.8 if kind=="fireball" else .65)
            if kind=="magic_orb":ring(core*1.25,.85,max(1,r*.045),.55)
    elif kind in BURST_KINDS:
        # A bright contact flash, expansion, then dissipating fragments.
        fade=max(0,1-t)
        extent=r*(.25+.9*t)
        if kind=="shockwave":
            ring(extent,fade,max(1,r*.09*(.4+fade)),.55)
            ring(extent*.73,fade*.5,max(1,r*.035),.25)
        elif kind=="frost_burst":
            for j in range(8):
                a=rot+j*math.tau/8
                x,y=polar(extent,a)
                line([(0,0),(x,y)],fade,max(1,r*.055),.7)
                for sign in (-1,1):
                    bx,by=polar(extent*.7,a+sign*.25)
                    line([(x*.65,y*.65),(bx,by)],fade*.8,max(1,r*.035),.45)
            ring(extent*.85,fade*.5,max(1,r*.04),.6)
        else:
            ring(extent,fade*.85,max(1,r*.07),.5)
            for j in range(12):
                a=rng.uniform(0,math.tau);dist=extent*rng.uniform(.15,.85)
                x,y=polar(dist,a)
                disk(x,y,max(1,r*rng.uniform(.09,.25)*(.5+t)),fade*.85,.35*fade)
        for j in range(min(e["particles"],32)):
            a=rng.uniform(0,math.tau);dist=extent*rng.uniform(.5,1.25)
            x,y=polar(dist,a)
            disk(x,y,max(.6,r*.035),fade,.65)
        if t<.4:disk(0,0,max(1,r*.28*(1-t)),1-t,.95)
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
    if e.get("artwork"):
        angle=e["rotation"]
        strength=1
        scale=1
        if kind in PROJECTILE_KINDS:
            a=motion_offset(original,max(original["start"],frame-1));b=motion_offset(original,min(flight_end(original),frame+1))
            dx,dy=b[0]-a[0],b[1]-a[1]
            if dx or dy:angle+=math.degrees(math.atan2(dy,dx))
        elif kind in SLASH_KINDS or kind=="slash":
            angle+=(t-.5)*e.get("sweep",180)
            strength=max(.15,math.sin(math.pi*t))
        elif kind in BURST_KINDS or kind=="impact":
            scale=.35+.65*t;strength=1-t
        else:
            scale=.85+.15*math.sin(t*math.tau*speed)
        vfx_art.overlay(im,e["artwork"],r,angle,strength*opacity*e.get("artwork_opacity",100)/100,scale,e["pixel"],e["artwork_tint"])
    return im,(side//2,side//2)
