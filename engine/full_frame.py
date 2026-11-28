"""Independent full-frame animation document. No skeletal dependencies."""
from . import world

MAX_FRAMES=120
MAX_ENCODED=24_000_000
MAX_PIXELS=24_000_000

def default():
    return dict(version=1,name="New animation",prompt="",reference=None,width=512,height=512,pivot=[256,480],fps=12,loop=True,pixel=False,frames=[])

def validate(value):
    if not isinstance(value,dict) or type(value.get("version",1)) is not int or value.get("version",1)!=1:
        raise ValueError("Invalid full-frame animation version")
    n=world.integer
    w=n(value.get("width",512),1,2048,"frame width");h=n(value.get("height",512),1,2048,"frame height")
    pivot=value.get("pivot",[w//2,h-1])
    if not isinstance(pivot,list) or len(pivot)!=2:raise ValueError("Invalid frame pivot")
    pivot=[n(pivot[0],0,w-1,"pivot X"),n(pivot[1],0,h-1,"pivot Y")]
    frames=value.get("frames",[])
    ref=value.get("reference")
    if not isinstance(frames,list) or len(frames)>MAX_FRAMES or any(not isinstance(f,str) for f in frames):raise ValueError("Invalid frames or frame count")
    if ref is not None and not isinstance(ref,str):raise ValueError("Invalid reference")
    if sum(map(len,frames))+(len(ref) if ref else 0)>MAX_ENCODED:raise ValueError("Animation exceeds encoded artwork budget")
    pixels=w*h*len(frames)
    if ref is not None:
        im=world.image(ref);pixels+=im.width*im.height
    if pixels>MAX_PIXELS:raise ValueError("Animation exceeds decoded pixel budget")
    for frame in frames:
        if world.image(frame).size!=(w,h):raise ValueError("All frames must match the animation canvas")
    keys=value.get("keyframes",[]);locks=value.get("locked_frames",[])
    for indices in (keys,locks):
        if not isinstance(indices,list) or any(type(k) is not int or not 0<=k<len(frames) for k in indices) or len(set(indices))!=len(indices):raise ValueError("Invalid frame markers")
    if not set(locks)<=set(keys):raise ValueError("Locked frames must be keyframes")
    from . import full_frame_guidance
    result=dict(keyframes=sorted(keys),locked_frames=sorted(locks),guidance=full_frame_guidance.settings(value.get("guidance")),version=1,name=world.label(value.get("name","New animation"),"animation name"),
        prompt=world.label(value.get("prompt",""),"motion description",2000,True),reference=ref,width=w,height=h,pivot=pivot,
        fps=n(value.get("fps",12),1,60,"animation FPS"),loop=world.boolean(value.get("loop",True),"animation loop"),
        pixel=world.boolean(value.get("pixel",False),"animation sampling"),frames=frames)

    from . import full_frame_directions as D
    return D.validate_library(value,result)
