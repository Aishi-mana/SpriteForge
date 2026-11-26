"""Two-bone textured mesh skinning for elbows and knees.

Weights transition across the painted upper/lower bone boundary. A regular
mesh is skinned by the two world transforms, then inverse-sampled triangle
by triangle. Pair layers retain their original place in the draw order.
"""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def prepare(arr, upper, lower, mask, radius, hd):
    if not upper.any() or not lower.any():
        return None
    yy, xx = np.nonzero(mask)
    h, w = mask.shape
    x0, x1 = max(0, xx.min()-1), min(w, xx.max()+2)
    y0, y1 = max(0, yy.min()-1), min(h, yy.max()+2)
    sl = np.s_[y0:y1, x0:x1]
    tex = arr[sl].copy()
    tex[~mask[sl]] = 0
    a, b = upper[sl], lower[sl]
    da, db = ndi.distance_transform_edt(~a), ndi.distance_transform_edt(~b)
    # Smoothstep from upper to lower over a radius in source pixels.
    weights = np.clip(.5 + (da-db)/(2*max(radius, .5)), 0, 1)
    weights = weights*weights*(3-2*weights)
    step = max(4 if hd else 1, min(24, int(radius/2)))
    xs = np.r_[np.arange(0, x1-x0, step), x1-x0].astype(float)
    ys = np.r_[np.arange(0, y1-y0, step), y1-y0].astype(float)
    gy, gx = np.meshgrid(ys, xs, indexing="ij")
    uv = np.stack((gx,gy),axis=-1)
    weight = ndi.map_coordinates(weights,[gy-.5,gx-.5],order=1,mode="nearest")
    return tex, uv, weight, (x0,y0)


def deform(mesh, upper_matrix, lower_matrix, pad, ss, size, hd):
    tex, uv, weight, (x0,y0) = mesh
    xy = (uv + [x0+pad,y0+pad])*ss
    a = xy @ upper_matrix[:2,:2].T + upper_matrix[:2,2]
    b = xy @ lower_matrix[:2,:2].T + lower_matrix[:2,2]
    dst = a*(1-weight[...,None])+b*weight[...,None]
    return rasterize(tex,uv,dst,size,hd)


def rasterize(tex,uv,dst,size,hd):
    """Shared textured triangle renderer; uv and dst use pixel-edge coordinates."""
    W,H=size
    out=np.zeros((H,W,4),np.uint8)
    th,tw=tex.shape[:2]
    if hd:
        source=tex.astype(np.float32)
        source[...,:3]*=source[...,3:4]/255
    def triangle(p,q):
        # Target pixel centers, mapped back into the original texture.
        xlo=max(0,int(np.floor(p[:,0].min())))
        xhi=min(W,int(np.ceil(p[:,0].max())))
        ylo=max(0,int(np.floor(p[:,1].min())))
        yhi=min(H,int(np.ceil(p[:,1].max())))
        if xlo>=xhi or ylo>=yhi:
            return
        d1,d2=p[1]-p[0],p[2]-p[0]
        det=d1[0]*d2[1]-d1[1]*d2[0]
        if abs(det)<1e-8:
            return
        Y,X=np.mgrid[ylo:yhi,xlo:xhi]
        dx,dy=X+.5-p[0,0],Y+.5-p[0,1]
        u=(dx*d2[1]-dy*d2[0])/det
        v=(d1[0]*dy-d1[1]*dx)/det
        inside=(u>=-1e-7)&(v>=-1e-7)&(u+v<=1+1e-7)
        if not inside.any():
            return
        qxy=q[0]+u[inside,None]*(q[1]-q[0])+v[inside,None]*(q[2]-q[0])
        if hd:
            coords=[qxy[:,1]-.5,qxy[:,0]-.5]
            values=np.stack([ndi.map_coordinates(source[...,c],coords,order=1,mode="nearest") for c in range(4)],axis=1)
            values[:,:3]=values[:,:3]*255/np.maximum(values[:,3:4],1e-6)
            values=np.clip(np.rint(values),0,255).astype(np.uint8)
        else:
            values=tex[np.clip(np.floor(qxy[:,1]).astype(int),0,th-1),np.clip(np.floor(qxy[:,0]).astype(int),0,tw-1)]
        # Folded triangles may overlap; opaque samples win over empty padding.
        visible=values[:,3]>0
        out[Y[inside][visible],X[inside][visible]]=values[visible]
    for y in range(uv.shape[0]-1):
        for x in range(uv.shape[1]-1):
            for offsets in (((0,0),(0,1),(1,1)),((0,0),(1,1),(1,0))):
                ix=tuple(zip(*[(y+dy,x+dx) for dy,dx in offsets]))
                triangle(dst[ix],uv[ix])
    return Image.fromarray(out,"RGBA")
