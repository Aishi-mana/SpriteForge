"""CPU animation diagnostics. Pixel metrics are not perceptual quality scores."""
import hashlib
import numpy as np
from . import full_frame as F, world

def measure(doc):
    d=F.validate(doc)
    if len(d["frames"])<2:raise ValueError("Benchmark needs at least two frames")
    def read(src):
        a=np.asarray(world.image(src),dtype=np.float32)/255
        a[:,:,:3]*=a[:,:,3:4]
        return a
    def delta(a,b):
        mask=(a[:,:,3]>0)|(b[:,:,3]>0)
        if not mask.any():return 0.
        return float(np.abs(a-b)[mask].mean()*100)
    def alpha_iou(a,b):
        x=a[:,:,3]>=.5;y=b[:,:,3]>=.5
        union=np.count_nonzero(x|y)
        return float(np.count_nonzero(x&y)/union*100) if union else 100.
    first=read(d["frames"][0]);prev=first
    differences=[];overlaps=[];areas=[];centers=[];bottoms=[];empty=0;opaque=0;unique=set()
    for i,src in enumerate(d["frames"]):
        a=first if i==0 else read(src)
        unique.add(hashlib.sha256(a.tobytes()).hexdigest())
        mask=a[:,:,3]>=.5
        ys,xs=np.where(mask)
        areas.append(float(mask.mean()*100))
        if not len(xs):empty+=1
        else:
            centers.append((float(xs.mean()),float(ys.mean())))
            bottoms.append(float(ys.max()))
        if np.all(a[:,:,3]>=.999):opaque+=1
        if i:
            differences.append(delta(prev,a));overlaps.append(alpha_iou(prev,a))
        prev=a
    def rnd(v):return round(float(v),3)
    mean=float(np.mean(differences))
    seam=delta(prev,first)
    c=np.asarray(centers)
    drift=np.linalg.norm(c-c[0],axis=1).max() if len(c) else 0
    return dict(frames=len(d["frames"]),width=d["width"],height=d["height"],fps=d["fps"],duration_seconds=rnd(len(d["frames"])/d["fps"]),loop=d["loop"],
        reference_id=hashlib.sha256(d["reference"].encode()).hexdigest() if d["reference"] else None,
        unique_frames=len(unique),empty_frames=empty,opaque_frames=opaque,
        adjacent_change_pct=rnd(mean),peak_change_pct=rnd(max(differences)),
        change_variability_pct=rnd(np.std(differences)),seam_change_pct=rnd(seam),
        seam_to_mean=rnd(seam/mean) if mean>1e-8 else None,
        adjacent_mask_iou_pct=rnd(np.mean(overlaps)),seam_mask_iou_pct=rnd(alpha_iou(prev,first)),
        foreground_area_range_pct=rnd(max(areas)-min(areas)),centroid_drift_px=rnd(drift),
        bottom_edge_range_px=rnd(max(bottoms)-min(bottoms)) if bottoms else None,
        encoded_bytes=sum(len(s) for s in d["frames"]))
