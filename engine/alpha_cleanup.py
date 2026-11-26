"""Flat-background alpha cleanup. Color evidence is not semantic segmentation."""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

def clean(image,tolerance=40,mode="smart",background=None,points=(),soft=True):
    if mode not in ("edge","smart","all","manual"):
        raise ValueError("Unknown cleanup mode")
    im=image.convert("RGBA")
    a=np.array(im)
    rgb=a[:,:,:3].astype(np.float32)
    alpha=a[:,:,3]
    tol=max(1,min(100,int(tolerance)))
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
