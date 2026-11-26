"""Phase 27: CPU-only mesh skinning and rig integration."""
from _common import *
from engine import rig, softmesh
from PIL import Image
import numpy as np

a=np.zeros((32,24,4),np.uint8)
a[2:30,8:16]=[180,90,30,255]
upper=np.zeros(a.shape[:2],bool); upper[2:16,8:16]=True
lower=np.zeros_like(upper); lower[16:30,8:16]=True
mesh=softmesh.prepare(a,upper,lower,upper|lower,4,False)
ident=np.eye(3)
out=softmesh.deform(mesh,ident,ident,0,1,(24,32),False)
ok(np.array_equal(np.asarray(out),a),"identity mesh preserves source pixels")
bend=rig._rot(12,16,45)
out=np.asarray(softmesh.deform(mesh,ident,bend,0,1,(24,32),False))
ok(not np.array_equal(out,a) and (out[...,3]>0).sum()>120,"bend moves texture without dropping most of limb")
ok(set(map(tuple,out[out[...,3]>0]))=={(180,90,30,255)},"pixel mesh keeps original colours")
hd=a.copy();hd[2:30,8,3]=90
hm=softmesh.prepare(hd,upper,lower,upper|lower,5,True)
ha=np.asarray(softmesh.deform(hm,ident,bend,0,1,(24,32),True))
ok(((ha[...,3]>0)&(ha[...,3]<255)).any(),"HD mesh retains fractional alpha")
ok(softmesh.prepare(a,upper,np.zeros_like(lower),upper,4,False) is None,"missing lower bone falls back to rigid")
sp,j,ov=synth_sprite()
old,meta=rig.render(sp,j,ov,"walk",3)
rigid,_=rig.render(sp,j,ov,"walk",3,softness=0)
soft,sm=rig.render(sp,j,ov,"walk",3,softness=55)
ok(all(x.tobytes()==y.tobytes() for x,y in zip(old,rigid)),"zero softness matches original mode")
ok(len(soft)==3 and sm["softness"]==55 and soft[0].size==old[0].size,"soft clip preserves output dimensions and timing")
ok(all(np.asarray(im)[...,3].any() for im in soft),"soft clip has visible frames")
try:
    rig.render(sp,j,ov,"walk",2,softness=101)
    ok(False,"invalid softness rejected")
except ValueError:
    ok(True,"invalid softness rejected")
done("test_softmesh")
