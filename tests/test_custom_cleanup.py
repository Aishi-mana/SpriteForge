"""CPU mock tests for mask boundaries, palette/alpha locks, provenance and accepted exports."""
from _common import *
from engine import custom_skeleton as C,custom_timeline as T,custom_cleanup as A,projects
sp,_,_=synth_sprite()
p=C.preset("humanoid")
p["timeline"]={"name":"cleanup","count":3,"tracks":{"head":[{"frame":0,"angle":0},{"frame":2,"angle":20}]}}
body={"image":data_url(sp),"profile":p,"padding":8,"frame":0,"mask":{"mode":"brush","strokes":[[.5,.45,.12]]}}
frame,mask,opts,meta=A.prepare(body)
ok(mask.any() and mask.sum()<frame.width*frame.height,"manual mask")
ok(np.all(np.asarray(frame)[...,3][mask]>0),"alpha-locked mask on visible pixels")
calls=[]
def fake(*args,**kw):
    calls.append((args,kw))
    return Image.new("RGB",args[6].size,(39,80,200))
out,info=A.cleanup(frame,mask,opts,fake,"x","","1","l","repair","",.35,20,5,1,512,True,"pixel")
a,b=np.asarray(frame),np.asarray(out)
ok(np.array_equal(a[~mask],b[~mask]),"outside mask byte identical")
ok(np.array_equal(a[...,3],b[...,3]),"alpha preserved exactly")
ok(info["palette_applied"] and len(calls)==1,"palette and one inpaint call")
ok(np.all(np.asarray(calls[0][0][7])>=0) and calls[0][0][7].getbbox() is not None,"nonempty model-space mask")
raw,full=T.render(body["image"],p,8)
ok(full["fingerprint"]==meta["fingerprint"],"single and full clip provenance match")
saved={"fingerprint":meta["fingerprint"],"frames":{"0":data_url(out)}}
mixed=A.apply(raw,full,saved)
ok(mixed[0].tobytes()==out.tobytes() and mixed[1].tobytes()==raw[1].tobytes(),"only accepted frame replaces original")
try:A.apply(raw,{**full,"fingerprint":"0"*64},saved);ok(False,"stale")
except ValueError:ok(True,"stale cleanup rejected")
try:A.apply(raw,full,{**saved,"frames":{"0":data_url(Image.new("RGBA",(1,1)))}});ok(False,"size")
except ValueError:ok(True,"mismatched canvas rejected")
root=tmpdir();projects.save(root,"Clean",{"custom_skeleton":p,"custom_cleanup":saved,"images":{"customrig":body["image"]}})
ok(projects.load(root,"Clean")["custom_cleanup"]==saved,"accepted cleanup persists separately")
try:A.prepare({**body,"fingerprint":"0"*64});ok(False,"stale mask")
except ValueError:ok(True,"stale mask rejected")
done("test_custom_cleanup")
