"""Flat-background alpha cleanup. Color evidence is not semantic segmentation."""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

def clean(image,tolerance=40,mode="smart",background=None,points=(),soft=True,shadow_strength=50):
    if mode not in ("edge","smart","all","manual","magic","shadow"):
        raise ValueError("Unknown cleanup mode")
    im=image.convert("RGBA")
    a=np.array(im)
    rgb=a[:,:,:3].astype(np.float32)
    alpha=a[:,:,3]
    tol=max(1,min(100,int(tolerance)))
    if mode=="shadow":
        return _shadow_cleanup(im,tol,background,shadow_strength)
    if background is None:
        border=np.concatenate((a[0],a[-1],a[:,0],a[:,-1]))
        border=border[border[:,3]>=250,:3]
        if not len(border):
            return im,{"removed":0,"pockets":0,"note":"Choose a background color for an already transparent image"}
        keys,counts=np.unique(border//16,axis=0,return_counts=True)
        bg=border[(border//16==keys[counts.argmax()]).all(1)].mean(0)
    else:
        if len(background)!=3 or any(not 0<=v<=255 for v in background):
            raise ValueError("Invalid background color")
        bg=np.array(background,dtype=np.float32)
    if mode=="magic":
        return _magic(im,a,rgb,bg,tol,background is None)
    distance=np.max(np.abs(rgb-bg),axis=2)
    visible=alpha>0
    candidate=(distance<=tol)&visible
    labels,n=ndi.label(candidate)
    edges=np.unique(np.concatenate((labels[0],labels[-1],labels[:,0],labels[:,-1])))
    edge_ids=set(int(v) for v in edges if v)
    # Existing alpha borders can supply exterior evidence, without treating all white as background.
    touching=ndi.binary_dilation(~visible)&candidate
    edge_ids.update(int(v) for v in np.unique(labels[touching]) if v)
    selected=set() if mode=="manual" else set(edge_ids)
    pockets=set()
    if mode in ("smart","all"):
        # Exact flat color, sufficient interior, and little color variation.
        # White costume panels can still be identical to the background: conservative
        # mode avoids tiny highlights and weak matches, but cannot guarantee semantics.
        areas=np.bincount(labels.ravel(),minlength=n+1)
        cores=ndi.binary_erosion(candidate,iterations=1)
        core_counts=np.bincount(labels[cores],minlength=n+1)
        exact=np.bincount(labels[(distance<=min(5,tol))&candidate],minlength=n+1)
        min_area=max(12,round(im.width*im.height*.00012))
        for k in range(1,n+1):
            if k in edge_ids:continue
            if mode=="all" or (areas[k]>=min_area and core_counts[k]>=max(4,areas[k]*.25) and exact[k]>=areas[k]*.97):
                selected.add(k);pockets.add(k)
    for x,y in points:
        if not 0<=x<im.width or not 0<=y<im.height:
            raise ValueError("Point outside image")
        k=int(labels[y,x])
        if k:selected.add(k);pockets.add(k)
    mask=np.isin(labels,list(selected))&candidate
    a[:,:,3][mask]=0
    if soft:
        rim=ndi.binary_dilation(mask)&~mask&visible
        # Only feather pixels that are plausibly mixed with the background.
        factor=np.clip((distance-tol)/max(1,tol),0,1)
        a[:,:,3][rim]=np.minimum(alpha[rim],np.rint(alpha[rim]*factor[rim]).astype(np.uint8))
    a[a[:,:,3]==0,:3]=0
    return Image.fromarray(a),{"removed":int(mask.sum()),"pockets":len(pockets),"background":[int(round(v)) for v in bg]}


def _magic(im,a,rgb,bg,tol,auto):
    """Conservative exterior segmentation with locally sampled border colors.

    No recoloring, resampling, feathering or GPU inference. Interior pockets
    deliberately remain untouched in this mode.
    """
    alpha=a[:,:,3]
    visible=alpha>0
    distance=np.max(np.abs(rgb-bg),axis=2)
    candidate=visible & (distance<=tol)
    if auto:
        border=np.concatenate((a[0],a[-1],a[:,0],a[:,-1]))
        samples=border[border[:,3]>=250,:3]
        # Only extend the dominant key with sufficiently supported nearby
        # shades; do not learn arbitrary foreground colors from the border.
        if len(samples):
            keys,counts=np.unique(samples//16,axis=0,return_counts=True)
            for key,count in zip(keys,counts):
                if count<max(4,len(samples)*.03):
                    continue
                shade=samples[(samples//16==key).all(1)].mean(0)
                if np.max(np.abs(shade-bg))<=min(100,tol*1.5):
                    candidate |= visible & (np.max(np.abs(rgb-shade),axis=2)<=max(3,tol*.5))
    # Flood only from the image boundary through candidate or clear pixels.
    # Unlike legacy smart mode, an isolated transparent interior hole is
    # not sufficient evidence to erase adjacent opaque details.
    traversable=candidate | ~visible
    seeds=np.zeros_like(visible)
    seeds[0,:]=traversable[0,:]
    seeds[-1,:]=traversable[-1,:]
    seeds[:,0]=traversable[:,0]
    seeds[:,-1]=traversable[:,-1]
    mask=ndi.binary_propagation(seeds,mask=traversable)&candidate
    info={"removed":int(mask.sum()),"pockets":0,"background":[int(round(v)) for v in bg]}
    if visible.any() and not (visible & ~mask).any():
        info.update(removed=0,note="Magic eraser would remove every visible pixel; lower tolerance or use manual cleanup.")
        return im,info
    a[mask]=0
    return Image.fromarray(a),info


def _shadow_cleanup(im,tol,background,strength):
    """Remove only plausible shallow ground-shadow components, without model inference."""
    if not 0<=strength<=100:
        raise ValueError("Invalid shadow strength")
    original=np.array(im)
    # On already transparent assets, do not run a second color-key pass.
    # A meaningful transparent exterior allows shadow-only refinement.
    border=np.concatenate((original[0],original[-1],original[:,0],original[:,-1]))
    if (border[:,3]==0).mean()>=.25:
        base=im.copy()
        info={"removed":0,"pockets":0}
    else:
        base,info=clean(im,tol,"magic",background,soft=False)
        if info.get("note"):
            return base,dict(info,shadow_removed=0)
    a=np.array(base)
    alpha=a[:,:,3]
    visible=alpha>0
    info=dict(info,shadow_removed=0)
    if not strength or not visible.any():
        return base,info
    rgb=a[:,:,:3].astype(np.float32)
    value=rgb.max(axis=2)
    chroma=value-rgb.min(axis=2)
    # Semi-transparent neutral/dark residuals, or opaque neutral midtones.
    # Never classify very dark opaque outlines as a ground shadow.
    candidate=visible & (chroma<=8+strength*.22) & (
        ((alpha<255)&(alpha<=90+strength*1.5)&(value<=150+strength*.7)) |
        ((alpha==255)&(value>=65-strength*.25)&(value<=120+strength*.9)))
    # If a color key is available, allow its darker shades on opaque backgrounds.
    if "background" in info:
        bg=np.array(info["background"],dtype=np.float32)
        denom=float(bg@bg)
        if denom>0:
            ratio=np.sum(rgb*bg,axis=2)/denom
            residual=np.max(np.abs(rgb-ratio[:,:,None]*bg),axis=2)
            candidate |= visible & (ratio>=.30-strength*.001) & (ratio<=.87) & (residual<=5+strength*.12)
    core=visible & ~candidate
    if not core.any():
        return base,dict(info,note="No reliable foreground anchor; shadow cleanup skipped.")
    ys,xs=np.nonzero(core)
    top,bottom=int(ys.min()),int(ys.max())
    height=bottom-top+1
    width=int(xs.max()-xs.min()+1)
    if height<8:
        return base,dict(info,note="Foreground too small for conservative shadow detection.")
    # Label before restricting vertical location: a tall connected gray garment
    # must not become a shallow component merely because it crosses the foot band.
    labels,n=ndi.label(candidate)
    exterior=ndi.binary_propagation(
        _boundary_seeds(~visible),mask=~visible)
    touching=ndi.binary_dilation(exterior)
    remove=np.zeros_like(visible)
    for k,sl in enumerate(ndi.find_objects(labels),1):
        if sl is None:
            continue
        yr,xr=sl
        h,w=yr.stop-yr.start,xr.stop-xr.start
        part=labels[sl]==k
        if yr.start<bottom-max(2,round(height*(.07+strength*.001))):
            continue
        if yr.start>bottom+max(3,round(height*.15)):
            continue
        if h>max(2,round(height*(.10+strength*.001))) or w<max(4,round(width*.25)) or w<2*h:
            continue
        if xr.stop<=xs.min() or xr.start>xs.max():
            continue
        if not (part & touching[sl]).any():
            continue
        remove[sl]|=part
    if remove.any():
        a[remove]=0
    info["shadow_removed"]=int(remove.sum())
    info["removed"]+=info["shadow_removed"]
    if not remove.any():
        info["note"]="No confident ground shadow found. Adjust sensitivity or use manual cleanup."
    return Image.fromarray(a),info


def _boundary_seeds(mask):
    seeds=np.zeros_like(mask)
    seeds[0,:]=mask[0,:]
    seeds[-1,:]=mask[-1,:]
    seeds[:,0]=mask[:,0]
    seeds[:,-1]=mask[:,-1]
    return seeds
