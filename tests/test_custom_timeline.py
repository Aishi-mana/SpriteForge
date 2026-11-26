"""CPU timeline interpolation, shared binding, animation export and persistence."""
from _common import *
from engine import custom_skeleton as C,custom_timeline as T,custom_skin as S,projects,exporter
from unittest.mock import patch
p=C.preset("chain")
p["skin"]={"mode":"weighted","resolution":16}
p["timeline"]={"name":"wave","count":5,"fps":12,"loop":False,"tracks":{"segment_2":[
 {"frame":4,"angle":80,"curve":"linear"},{"frame":0,"angle":0,"curve":"ease"}],
 "tip":[{"frame":1,"angle":30,"curve":"step"},{"frame":3,"angle":-30,"curve":"linear"}]}}
p=C.validate(p);clip=p["timeline"];keys=clip["tracks"]["segment_2"]
ok(keys[0]["frame"]==0 and T.sample(keys,1,0)==12.5,"sorted keys and eased interpolation")
ok(T.sample([{**keys[0],"curve":"linear"},keys[1]],1,0)==20,"linear interpolation")
ok(T.sample(clip["tracks"]["tip"],0,0)==30 and T.sample(clip["tracks"]["tip"],2,0)==30 and T.sample(clip["tracks"]["tip"],3,0)==-30,"hold and stepped key boundaries")
ok(T.pose(p,2)["bones"][1]["angle"]==40 and p["bones"][1]["angle"]==0,"pose evaluation does not mutate base")
im=Image.new("RGBA",(64,64));im.paste((60,180,100,255),(10,25,60,39))
uri=data_url(im)
with patch.object(S,"build_weights",wraps=S.build_weights) as bind:
    frames,meta=T.render(uri,p,8)
    ok(bind.call_count==1,"weighted binding reused across clip")
ok(len(frames)==5 and meta["fps"]==12 and not meta["loop"],"clip timing")
ok(all(x.size==(80,80) for x in frames) and frames[0].tobytes()!=frames[-1].tobytes(),"consistent canvas and animated motion")
single,one=T.render(uri,p,8,frame=2)
ok(one["indices"]==[2] and single[0].tobytes()==frames[2].tobytes(),"scrub frame matches complete clip")
root=tmpdir()
result=exporter.export_pack([{**meta,"frames":frames}],{"crop":False,"gif":False,"godot":False,"unity":False},"wave",root)
ok(Path(result["dir"]).is_dir(),"custom spritesheet exported")
projects.save(root,"Timeline",{"custom_skeleton":p,"images":{"customrig":uri}})
ok(projects.load(root,"Timeline")["custom_skeleton"]==p,"timeline project persistence")
for bad in ({"missing":keys},{"segment_2":[keys[0],keys[0]]},{"segment_2":[{"frame":5,"angle":0}]}):
    try:C.validate({**p,"timeline":{**clip,"tracks":bad}});ok(False,"invalid timeline")
    except ValueError:ok(True,"invalid timeline rejected")
done("test_custom_timeline")
