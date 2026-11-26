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


def weighted_mesh(arr,settings,hd):
    """Create a bounded regular mesh; B weight painted over a uniform A/B base.
    Strokes are normalized to the transformed, clipped rest canvas.
    """
    yy,xx=np.nonzero(arr[...,3]>0)
    if not len(xx):return None
    H,W=arr.shape[:2]
    x0,x1=max(0,int(xx.min())-1),min(W,int(xx.max())+2)
    y0,y1=max(0,int(yy.min())-1),min(H,int(yy.max())+2)
    tw,th=x1-x0,y1-y0
    step=max(2 if hd else 1,int(np.ceil(max(tw,th)/48)))
    xs=np.r_[np.arange(0,tw,step),tw].astype(float)
    ys=np.r_[np.arange(0,th,step),th].astype(float)
    gy,gx=np.meshgrid(ys,xs,indexing="ij")
    uv=np.stack((gx,gy),axis=-1)
    weight=np.full(gx.shape,settings["base"],dtype=float)
    for x,y,r,v in settings["strokes"]:
        distance=np.hypot(gx+x0-x*W,gy+y0-y*H)/max(r*max(W,H),.5)
        strength=np.clip(1-distance,0,1)
        strength=strength*strength*(3-2*strength)
        weight=weight*(1-strength)+v*strength
    return arr[y0:y1,x0:x1].copy(),uv,weight,(x0,y0)
