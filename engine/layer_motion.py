"""CPU-only preparation of independently deformable modular assets."""
import numpy as np
from scipy import ndimage as ndi
from . import softmesh

def garment_meshes(arr,labels,bones,bone_idx,softness,hd):
    """Disjoint paired elbow/knee masks, shared interpolation with body mesh."""
    out={};children=set()
    if softness<=0:return out,children
    radius=max(1.,max(arr.shape[:2])*.14*softness/100)
    for side in ("l","r"):
        for limb in ("arm","leg"):
            a,b=(f"{side}_{limb}_{part}" for part in ("u","l"))
            ma,mb=labels==bone_idx[a],labels==bone_idx[b]
            mesh=softmesh.prepare(arr,ma,mb,ma|mb,radius,hd)
            if mesh is not None:
                out[a]=(b,mesh);children.add(b)
    return out,children

def spring_geometry(arr,settings,defaults):
    """Anchor in occupied bounding box, projected chain along farthest end.
    Degenerate/tiny assets return None and fall back to their rigid attachment.
    """
    mask=arr[...,3]>0
    yy,xx=np.nonzero(mask)
    if len(xx)<6:return None
    P=np.stack([xx+.5,yy+.5],1).astype(float)
    target=np.array([xx.min()+settings["anchor_x"]*(xx.max()-xx.min()+1),
                     yy.min()+settings["anchor_y"]*(yy.max()-yy.min()+1)])
    k=max(1,int(np.ceil(.06*len(P))))
    distance=np.sum((P-target)**2,axis=1)
    A=P[np.argpartition(distance,k-1)[:k]].mean(0)
    dist=np.sum((P-A)**2,axis=1)
    tip=P[np.argpartition(dist,len(P)-k)[-k:]].mean(0)
    L=float(np.linalg.norm(tip-A))
    if L<2:return None
    u=(tip-A)/L
    nseg=max(1,min(settings["segments"],int(L//2) or 1))
    si=np.clip(np.floor(((P-A)@u)/L*nseg),0,nseg-1).astype(np.int32)
    seg=np.full(mask.shape,-1,np.int32);seg[yy,xx]=si
    return dict(A=A,u=u,L=L,nseg=nseg,seg=seg,mask=mask,
                pivots=[A+u*L*i/nseg for i in range(nseg)],
                omega=defaults["omega"],grav=defaults["grav"],gain=defaults["gain"])

def spring_masks(pt,overlap):
    """Small overlapping joints reduce cracks between rigid chain segments."""
    for i in range(pt["nseg"]):
        m=pt["seg"]==i
        if overlap and m.any():
            m=ndi.binary_dilation(m,iterations=min(3,overlap))&pt["mask"]
        yield m
