from _common import *
import io,json,zipfile
from engine import asset_library as L, library_backup as B, modular as M, modular_rig as R, full_frame, visual_motion
from PIL import Image
root=tmpdir();dest=tmpdir()
body,joints,_=synth_sprite();image=M.png_uri(body)
recipe={"width":body.width,"height":body.height,"pixel":True,"layers":[{"name":"Base","category":"body","image":image}]}
recipe["rig"]={"body_key":R.describe(recipe)["body_key"],"joints":joints}
for kind in ("character","asset","rig"):
    L.save(root,{"kind":kind,"name":kind,"recipe":recipe,"index":0})
still=L.save(root,{"kind":"image","name":"Hero","image":image,"collection":"Forest","favorite":True,"tags":["hero"]})
raw=visual_motion.encode([Image.new("RGB",(32,32),"red"),Image.new("RGB",(32,32),"blue")],8,root/"sample.mp4")
video=L.save_video(root,raw,{"name":"Motion","parent_id":still["id"],"relation":"generated_from"})
doc=full_frame.default();doc.update(width=body.width,height=body.height,pivot=[0,0],frames=[image,image],fps=8)
anim=L.save(root,{"kind":"animation","name":"Idle","document":doc,"parent_id":video["id"],"relation":"extracted_from"})
archive=io.BytesIO();ok(B.export(root,archive)==6,"all asset types exported")
archive.seek(0);result=B.restore(dest,archive)
ok(result=={"imported":6,"remapped":0,"detached":0},"complete restore")
ok(L.video_path(dest,video["id"]).read_bytes()==raw,"original MP4")
ok(L.load(dest,anim["id"])["payload"]==L.load(root,anim["id"])["payload"],"original animation")
ok(L.load(dest,still["id"])["meta"]["favorite"],"favorite preserved")
ok(L.relationships(dest,anim["id"])["parent"]["id"]==video["id"],"relationship preserved")
archive.seek(0);result=B.restore(dest,archive)
ok(result["remapped"]==6 and len(L.list_entries(dest))==12,"collision restore copies")
new=next(m for m in L.list_entries(dest,"animation") if m["id"]!=anim["id"])
ok(new["parent_id"]!=video["id"] and L.relationships(dest,new["id"])["parent"]["kind"]=="video","collision relationship remapped")
single=io.BytesIO();B.export(root,single,anim["id"]);single.seek(0)
ok(B.restore(dest,single)["detached"]==1,"single asset external link detached")
before=len(L.list_entries(dest))
for mode in ("path","checksum","duplicate","missing"):
    invalid=io.BytesIO()
    archive.seek(0)
    with zipfile.ZipFile(archive) as src,zipfile.ZipFile(invalid,"w") as out:
        for name in src.namelist():
            if mode=="missing" and name==still["id"]+"/preview.png":continue
            data=src.read(name)
            if mode=="checksum" and name==still["id"]+"/payload.json":data=b"x"+data[1:]
            out.writestr(name,data)
        if mode=="path":out.writestr("../escape","bad")
        if mode=="duplicate":out.writestr("manifest.json","{}")
    invalid.seek(0)
    try:B.restore(dest,invalid);ok(False,"reject "+mode)
    except ValueError:ok(True,"reject "+mode)
    ok(len(L.list_entries(dest))==before,"invalid restore has no partial results")
old=L.MAX_ENTRIES
try:
    L.MAX_ENTRIES=before
    archive.seek(0)
    try:B.restore(dest,archive);ok(False,"capacity rejection")
    except ValueError:ok(True,"capacity rejection")
finally:L.MAX_ENTRIES=old
done("test_library_backup")
