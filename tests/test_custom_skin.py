"""CPU multi-bone weight normalization, paint, mesh deformation, persistence."""
from _common import *
from engine import custom_skeleton as C,custom_skin as S,projects
p=C.preset("chain")
p["skin"]={"mode":"weighted","blend":.2,"resolution":32,"strokes":[]}
p=C.validate(p)
size=(64,64);m,segments=C.transforms(p,size)
uv,w,ids=S.build_weights(p,size,segments)
ok(np.allclose(w.sum(axis=-1),1) and np.all(w>=0),"auto weights normalized")
ok(np.any((w>1e-5).sum(axis=-1)>=3),"three or more bones influence a vertex")
def stamp(bone,value):
    return {"bone":bone,"x":.5,"y":.5,"radius":.25,"value":value,"strength":1}
p["skin"]["strokes"]=[stamp("tip",1)]
_,a,_=S.build_weights(p,size,segments)
ok(abs(a[16,16,ids.index("tip")]-1)<1e-8,"paint can fully assign selected bone")
p["skin"]["strokes"].append(stamp("tip",0))
_,b,_=S.build_weights(p,size,segments)
ok(b[16,16,ids.index("tip")]<1e-8 and np.allclose(b.sum(axis=-1),1),"erasing full influence redistributes weights")
im=Image.new("RGBA",size,(0,0,0,0));im.paste((40,180,80,255),(10,26,58,39))
rest,_=C.render(im,p,0)
ok(rest.tobytes()==im.tobytes(),"rest pose identity")
p["bones"][1]["angle"]=45
weighted,pts=C.render(im,p,16)
rigid,_=C.render(im,{**p,"skin":{**p["skin"],"mode":"rigid"}},16)
ok(weighted.size==rigid.size and weighted.tobytes()!=rigid.tobytes(),"weighted pose differs from rigid")
ok(weighted.getchannel("A").getbbox() is not None and np.allclose(pts["root"][1],pts["segment_2"][0]),"weighted pose connected and nonempty")
heat=S.heatmap(p,size,segments,"tip")
ok(heat.size==size and heat.mode=="L","weight heatmap")
p=C.validate(p)
root=tmpdir();projects.save(root,"Weighted",{"custom_skeleton":p,"images":{"customrig":data_url(im)}})
ok(projects.load(root,"Weighted")["custom_skeleton"]==p,"paint and mesh settings persisted")
bad=json.loads(json.dumps(p));bad["skin"]["strokes"][0]["bone"]="missing"
try:C.validate(bad);ok(False,"missing paint bone")
except ValueError:ok(True,"missing paint bone rejected")
bad=json.loads(json.dumps(p));bad["skin"]["strokes"]=[stamp("tip",1)]*257
try:C.validate(bad);ok(False,"stamp budget")
except ValueError:ok(True,"stamp budget enforced")
done("test_custom_skin")
