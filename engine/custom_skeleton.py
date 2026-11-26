"""Editable connected bone trees and CPU rigid cutout pose preview.
Coordinates are normalized to the source canvas. Child heads are parent tails.
"""
import math
import re
import numpy as np
from PIL import Image
from . import modular, rig

MAX_BONES=32

def number(v,lo,hi,label):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:
        raise ValueError("Invalid "+label)
    return float(v)

def point(v):
    if not isinstance(v,(list,tuple)) or len(v)!=2:raise ValueError("Invalid joint coordinates")
    return [number(x,0,1,"joint coordinate") for x in v]

def validate(profile):
    if not isinstance(profile,dict) or profile.get("version",1)!=1:raise ValueError("Invalid skeleton preset")
    bones=profile.get("bones")
    if not isinstance(bones,list) or not 1<=len(bones)<=MAX_BONES:raise ValueError("Skeleton requires 1–32 bones")
    root_head=point(profile.get("root_head",[.5,.55]))
    out=[];ids=set()
    for b in bones:
        if not isinstance(b,dict):raise ValueError("Invalid bone")
        key=b.get("id");name=b.get("name");parent=b.get("parent")
        if not isinstance(key,str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}",key) or key in ids:raise ValueError("Invalid or duplicate bone ID")
        if not isinstance(name,str) or not name.strip() or len(name)>60:raise ValueError("Invalid bone name")
        if parent is not None and not isinstance(parent,str):raise ValueError("Invalid parent")
        ids.add(key)
        out.append(dict(id=key,name=name.strip(),parent=parent,tail=point(b.get("tail")),angle=number(b.get("angle",0),-180,180,"bone rotation")))
    by={b["id"]:b for b in out}
    roots=[b for b in out if b["parent"] is None]
    if len(roots)!=1:raise ValueError("Skeleton must have exactly one root bone")
    ordered=[];visited=set();active=set()
    def visit(b):
        k=b["id"]
        if k in active:raise ValueError("Bone hierarchy contains a cycle")
        if k in visited:return
        active.add(k)
        parent=b["parent"]
        if parent is not None:
            if parent not in by:raise ValueError("Missing parent bone")
            visit(by[parent])
        head=root_head if parent is None else by[parent]["tail"]
        if math.dist(head,b["tail"])<.001:raise ValueError("Bone length must be nonzero")
        active.remove(k);visited.add(k);ordered.append(b)
    for b in out:visit(b)
    pixel=profile.get("pixel",True)
    if not isinstance(pixel,bool):raise ValueError("Invalid sampling mode")
    return {"version":1,"root_head":root_head,"pixel":pixel,"bones":ordered}

def preset(kind):
    if kind not in ("humanoid","quadruped","winged","chain"):raise ValueError("Unknown skeleton preset")
    def b(id,parent,x,y):
        return dict(id=id,name=id.replace("_"," ").title(),parent=parent,tail=[x,y],angle=0)
    if kind in ("humanoid","winged"):
        root=[.5,.66]
        bones=[b("pelvis",None,.5,.58),b("torso","pelvis",.5,.32),b("head","torso",.5,.12),
               b("left_arm","torso",.25,.43),b("left_forearm","left_arm",.19,.62),
               b("right_arm","torso",.75,.43),b("right_forearm","right_arm",.81,.62),
               b("left_thigh","pelvis",.38,.78),b("left_shin","left_thigh",.36,.95),
               b("right_thigh","pelvis",.62,.78),b("right_shin","right_thigh",.64,.95)]
        if kind=="winged":bones += [b("left_wing","torso",.22,.20),b("left_wing_tip","left_wing",.04,.42),
                                  b("right_wing","torso",.78,.20),b("right_wing_tip","right_wing",.96,.42)]
    elif kind=="quadruped":
        root=[.20,.43];bones=[b("hindquarters",None,.35,.43),b("spine","hindquarters",.68,.40),
            b("neck","spine",.79,.25),b("head","neck",.94,.24),
            b("hind_leg","hindquarters",.29,.68),b("hind_foot","hind_leg",.35,.93),
            b("front_leg","spine",.72,.68),b("front_foot","front_leg",.72,.93),
            b("tail","hindquarters",.13,.32),b("tail_tip","tail",.04,.15)]
    else:
        root=[.2,.5];bones=[b("root",None,.35,.5),b("segment_2","root",.55,.5),b("segment_3","segment_2",.73,.5),b("tip","segment_3",.92,.5)]
    return validate(dict(version=1,root_head=root,pixel=True,bones=bones))

def transforms(profile,size):
    """Rest-space to posed-space transforms. A parent rotates its entire subtree."""
    w,h=size;by={b["id"]:b for b in profile["bones"]};mat={};segments={}
    for b in profile["bones"]:
        k,p=b["id"],b["parent"]
        head=np.array(profile["root_head"] if p is None else by[p]["tail"])*[w,h]
        tail=np.array(b["tail"])*[w,h]
        mat[k]=(np.eye(3) if p is None else mat[p])@rig._rot(*head,b["angle"])
        segments[k]=(head,tail)
    return mat,segments

def render(image,profile,padding=32):
    profile=validate(profile)
    im=modular.decode(image) if isinstance(image,str) else image.convert("RGBA")
    w,h=im.size
    padding=modular.integer(padding,0,256,"padding")
    W,H=w+2*padding,h+2*padding
    if max(w,h)>1024 or W*H*len(profile["bones"])>48_000_000:
        raise ValueError("Custom pose exceeds CPU surface budget; reduce padding or bone count")
    arr=np.asarray(im).copy()
    yy,xx=np.nonzero(arr[...,3]>0)
    if not len(xx):raise ValueError("Source image is transparent")
    matrices,segments=transforms(profile,im.size)
    # Assign visible pixels to nearest rest segment. Only one distance vector retained per bone.
    x=xx.astype(float)+.5;y=yy.astype(float)+.5
    best=np.full(len(xx),np.inf);label=np.zeros(len(xx),np.int16)
    for i,b in enumerate(profile["bones"]):
        a,z=segments[b["id"]];v=z-a;den=max(float(v@v),1e-9)
        t=np.clip(((x-a[0])*v[0]+(y-a[1])*v[1])/den,0,1)
        d=(x-a[0]-t*v[0])**2+(y-a[1]-t*v[1])**2
        take=d<best;best[take]=d[take];label[take]=i
    out=Image.new("RGBA",(W,H))
    shift=np.array([[1.,0,padding],[0,1.,padding],[0,0,1.]])
    resample=Image.Resampling.NEAREST if profile["pixel"] else Image.Resampling.BICUBIC
    for i,b in enumerate(profile["bones"]):
        take=label==i
        if not take.any():continue
        sx,sy=xx[take],yy[take];x0,y0=int(sx.min()),int(sy.min())
        part=np.zeros((int(sy.max())-y0+1,int(sx.max())-x0+1,4),np.uint8)
        part[sy-y0,sx-x0]=arr[sy,sx]
        offset=np.array([[1.,0,x0],[0,1.,y0],[0,0,1.]])
        inv=np.linalg.inv(shift@matrices[b["id"]]@offset)
        surface=Image.fromarray(part).transform((W,H),Image.Transform.AFFINE,tuple(inv[:2].flatten()),resample=resample)
        out=Image.alpha_composite(out,surface)
    posed={}
    for b in profile["bones"]:
        k=b["id"];head,tail=segments[k]
        posed[k]=[(shift@matrices[k]@np.r_[p,1])[:2].tolist() for p in (head,tail)]
    return out,posed
