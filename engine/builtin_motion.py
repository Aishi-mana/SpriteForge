"""Experimental procedural skeleton guides for visual conditioning, not final sprite art."""
import math,tempfile
from pathlib import Path
from PIL import Image,ImageDraw
from . import world,visual_motion

PRESETS=("idle_minimal","idle","alert","floating","weapon_ready","walk","run","attack","cast","hurt","jump")
# OpenPose-style colored limbs; approximate front-facing skeleton, not detected joints.
EDGES=[("neck","rshoulder",(255,0,0)),("rshoulder","relbow",(255,85,0)),("relbow","rhand",(255,170,0)),("neck","lshoulder",(255,255,0)),("lshoulder","lelbow",(170,255,0)),("lelbow","lhand",(85,255,0)),("neck","rhip",(0,255,0)),("rhip","rknee",(0,255,85)),("rknee","rfoot",(0,255,170)),("neck","lhip",(0,255,255)),("lhip","lknee",(0,170,255)),("lknee","lfoot",(0,85,255)),("neck","nose",(0,0,255)),("nose","reye",(85,0,255)),("nose","leye",(170,0,255))]

def render(body):
    n=world.integer
    w=n(body.get("width",480),256,768,"guide width")
    h=n(body.get("height",480),256,768,"guide height")
    count=n(body.get("frames",33),9,97,"guide frames")
    fps=n(body.get("fps",16),8,30,"guide FPS")
    if w%16 or h%16 or (count-1)%4 or w*h*count>24_000_000:raise ValueError("Invalid guide dimensions or frame count")
    preset=body.get("preset","idle_minimal")
    if preset not in PRESETS:raise ValueError("Choose a supported built-in motion")
    style=body.get("proportion","chibi")
    if style not in ("chibi","standard"):raise ValueError("Invalid guide proportions")
    strength=n(body.get("strength",35),0,100,"guide intensity")/100
    q=body.get("guidance") or {}
    from . import full_frame_video as V
    ref=V.prepare_reference(body["reference"],w,h,q) if body.get("reference") else None
    # Derive bounds from the actual alpha reference using the same fit as Wan.
    x0,y0,x1,y1=w*.22,h*.1,w*.78,h*.9
    if ref is not None:
        im=world.image(body["reference"])
        margin=world.integer(q.get("margin",10),0,30,"reference margin")/100
        im.thumbnail((max(1,int(w*(1-2*margin))),max(1,int(h*(1-2*margin)))),Image.Resampling.LANCZOS)
        box=im.getchannel("A").getbbox()
        if not box:raise ValueError("Empty character reference")
        ox=(w-im.width)//2;oy=(h-im.height)//2
        x0,y0,x1,y1=box[0]+ox,box[1]+oy,box[2]+ox,box[3]+oy
    cx=(x0+x1)/2;H=max(1,y1-y0);S=min((x1-x0)*.25,H*.16)
    neck=.43 if style=="chibi" else .22
    hip=.69 if style=="chibi" else .55
    frames=[]
    for i in range(count):
        t=i/(count-1);wave=math.sin(2*math.pi*t);pulse=(1-math.cos(2*math.pi*t))/2
        lift=0;chest=0;arm=0;stride=0;leg=0;lean=0
        if preset in ("idle_minimal","idle","alert","weapon_ready"):
            chest=-H*(.012 if preset=="idle_minimal" else .025)*strength*pulse
        elif preset=="floating":lift=-H*.08*strength*pulse
        elif preset in ("walk","run"):
            stride=H*(.13 if preset=="walk" else .23)*strength*wave
            leg=H*.08*strength*abs(wave);arm=-stride*.8
            lift=-H*.025*strength*abs(wave)
        elif preset=="jump":lift=-H*.20*strength*pulse;leg=H*.05*strength*pulse
        elif preset=="attack":arm=H*.24*strength*wave;lean=H*.045*strength*wave
        elif preset=="cast":arm=H*.20*strength*pulse;chest=-H*.02*strength*pulse
        elif preset=="hurt":lean=-H*.075*strength*pulse
        def p(x,y,dy=0):return (cx+x,y0+y*H+lift+dy)
        pts={"neck":p(lean,neck,chest),"nose":p(lean,neck-(.14 if style=="chibi" else .10),chest),"reye":p(lean-S*.16,neck-.17 if style=="chibi" else neck-.12,chest),"leye":p(lean+S*.16,neck-.17 if style=="chibi" else neck-.12,chest)}
        for side,sign in (("r",-1),("l",1)):
            pts[side+"shoulder"]=p(sign*S+lean,neck+.025,chest)
            pts[side+"elbow"]=p(sign*S*1.18+lean+sign*arm*.45,(neck+hip)/2,chest*.5-abs(arm)*.20)
            pts[side+"hand"]=p(sign*S*1.15+lean+sign*arm,hip+.04,-abs(arm)*.55)
            pts[side+"hip"]=p(sign*S*.55,hip)
            pts[side+"knee"]=p(sign*S*.62+sign*stride*.45,(hip+.97)/2,-leg*.5)
            pts[side+"foot"]=p(sign*S*.72+sign*stride,.97,-leg if sign*wave>0 else 0)
        im=Image.new("RGB",(w,h));draw=ImageDraw.Draw(im);thick=max(2,round(H*.012))
        for a,b,color in EDGES:
            draw.line([pts[a],pts[b]],fill=color,width=thick)
            for x,y in (pts[a],pts[b]):draw.ellipse((x-thick/2,y-thick/2,x+thick/2,y+thick/2),fill=color)
        frames.append(im)
    return frames,fps

def generate(body):
    frames,fps=render(body)
    with tempfile.TemporaryDirectory() as d:return visual_motion.encode(frames,fps,Path(d)/"guide.mp4")
