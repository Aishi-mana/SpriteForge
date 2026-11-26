"""Non-explicit, featureless mannequin for modular game asset layering."""
from PIL import Image, ImageDraw
import math
import re

BUILDS={"masculine":(0.165,0.115,0.125),"feminine":(0.133,0.143,0.105),"androgynous":(0.145,0.125,0.112)}
PROPORTIONS={"chibi":(0.24,0.47),"anime":(0.15,0.48),"realistic":(0.115,0.49),"muscular":(0.13,0.48),"slender":(0.13,0.48)}
VIEWS=("front","side","back","three_quarter")
POSES=("neutral","a_pose","t_pose")
SIZES=(32,64,96,128,160,256,512,768,1024)

def render(build="androgynous",proportions="anime",view="front",pose="a_pose",size=128,color="#C6A58B",pixel=True):
    if build not in BUILDS or proportions not in PROPORTIONS or view not in VIEWS or pose not in POSES or size not in SIZES:
        raise ValueError("Invalid mannequin preset")
    if not isinstance(color,str) or not re.fullmatch(r"#[0-9a-fA-F]{6}",color):
        raise ValueError("Use a six-digit RGB hex color")
    # Geometry only: smooth mannequin, no anatomical intimate detail.
    rgb=tuple(int(color[i:i+2],16) for i in (1,3,5))
    light=tuple(min(255,int(c*1.08+5)) for c in rgb)
    shade=tuple(int(c*.80) for c in rgb)
    S=size*4 if pixel else size*2
    im=Image.new("RGBA",(S,S))
    d=ImageDraw.Draw(im)
    sh,hip,waist=BUILDS[build]
    head,leg=PROPORTIONS[proportions]
    if proportions=="muscular": sh*=1.17
    if proportions=="slender": sh*=.88;hip*=.85;waist*=.83
    if proportions=="chibi":sh*=1.15;hip*=1.1
    projection={"front":1,"back":1,"side":.47,"three_quarter":.78}[view]
    sh*=projection;hip*=projection;waist*=projection
    top=.07; neck=top+head; shoulder=neck+.055; pelvis=.92-leg
    if pelvis<shoulder+.10:pelvis=shoulder+.10
    def pt(x,y):return (round(x*S),round(y*S))
    def ellipse(x,y,rx,ry,c):
        d.ellipse((*pt(x-rx,y-ry),*pt(x+rx,y+ry)),fill=c)
    def limb(points,radii,c):
        for i in range(len(points)-1):
            a,b=points[i],points[i+1]
            dx,dy=b[0]-a[0],b[1]-a[1];n=math.hypot(dx,dy) or 1
            nx,ny=-dy/n,dx/n
            ra,rb=radii[i],radii[i+1]
            d.polygon([pt(a[0]+nx*ra,a[1]+ny*ra),pt(b[0]+nx*rb,b[1]+ny*rb),pt(b[0]-nx*rb,b[1]-ny*rb),pt(a[0]-nx*ra,a[1]-ny*ra)],fill=c)
        for (x,y),r in zip(points,radii):ellipse(x,y,r,r,c)
    for sign in (-1,1):
        x=.5+sign*hip*.58
        foot=.5+sign*hip*.70
        knee=(pelvis+.86)/2
        limb([(x,pelvis),(foot,knee),(foot,.90)],[.047,.035,.025],shade if sign==-1 and view in ("side","three_quarter") else rgb)
        ellipse(foot+(.018 if view=="side" else 0),.925,.041,.023,rgb)
    # Rounded, continuous featureless torso; no garment or anatomy markings.
    d.polygon([pt(.5-sh,shoulder),pt(.5+sh,shoulder),pt(.5+waist,pelvis-.085),pt(.5+hip,pelvis),pt(.5+hip*.55,pelvis+.055),pt(.5-hip*.55,pelvis+.055),pt(.5-hip,pelvis),pt(.5-waist,pelvis-.085)],fill=rgb)
    ellipse(.5,shoulder,sh,.043,rgb)
    ellipse(.5,pelvis,hip,.055,rgb)
    for sign in (-1,1):
        x=.5+sign*sh
        if pose=="t_pose": elbow=(.5+sign*.30,shoulder+.005);hand=(.5+sign*.425,shoulder+.01)
        elif pose=="a_pose":elbow=(.5+sign*(sh+.085),shoulder+.105);hand=(.5+sign*(sh+.15),shoulder+.22)
        else:elbow=(.5+sign*(sh+.018),shoulder+.15);hand=(.5+sign*(sh+.022),min(.73,shoulder+.29))
        limb([(x,shoulder),elbow,hand],[.036,.027,.022],shade if sign==-1 and view in ("side","three_quarter") else rgb)
    limb([(.5,neck-.015),(.5,shoulder)],[.035,.038],rgb)
    ellipse(.5,top+head*.52,head*.39*(.82 if view=="side" else 1),head*.52,light)
    return im.resize((size,size),Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS)
