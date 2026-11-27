"""VFX origin, full-alpha animation, atlas metadata and bundle regression checks."""
from _common import *
from engine import vfx_export as E, vfx_studio as V, vfx, exporter
from PIL import Image, features
from pathlib import Path
import json, zipfile, hashlib

r=V.validate(dict(kind="fireball",name="flight",count=9,start=1,end=7,fps=12,travel_x=-120,travel_y=30,
                  path="arc",radius=12,impact_kind="explosion",impact_frames=2,
                  keyframes=[dict(frame=0,dx=100,dy=-100),dict(frame=6,dx=150,dy=-100)],loop=False))
frames,meta=V.render(r)
w,h,x,y=vfx.effect_canvas(r)
ok(meta["pivot"]==[x,y] and 0<=x<w and 0<=y<h,"actual origin remains inside cell with shifted keys")
ok(frames[0].getbbox() is None and frames[-1].getbbox() is None,"inactive frames preserved")
root=tmpdir()
out=E.effect_pack(r,dict(layout="grid",columns=3,apng=True,webp=features.check("webp"),gif=True,frames=True),root)
d=Path(out["dir"])
ok(out["pivot"]==[x,y] and out["cell"]==[w,h],"pack preserves pivot")
atlas=json.loads((d/"flight_atlas.json").read_text())
ok(all(f["pivotPx"]==dict(x=x,y=y) for f in atlas["frames"].values()),"atlas exact pivot")
unity=json.loads((d/"flight_unity.json").read_text())
ok(abs(unity["pivotX"]-x/w)<.00001 and abs(unity["pivotY"]-(h-y)/h)<.00001,"Unity pivot coordinates")
ok(f"offset = Vector2({-x}, {-y})" in (d/"flight.tscn").read_text(),"Godot origin")
payload=json.loads((d/"flight_vfx.json").read_text())
ok(payload["recipe"]==r and payload["frame_count"]==len(frames),"portable export recipe")
with zipfile.ZipFile(d/"flight_game_assets.zip") as z:
    manifest=json.loads(z.read("flight_manifest.json"))
    ok(all(hashlib.sha256(z.read(f["path"])).hexdigest()==f["sha256"] for f in manifest["files"]),"bundle integrity")
    ok("flight_vfx.json" in z.namelist() and "flight_flight.apng" in z.namelist(),"sidecar and APNG bundled")
with Image.open(d/"flight_sheet.png") as sheet:
    for i,item in enumerate(atlas["frames"].values()):
        b=item["frame"];im=sheet.crop((b["x"],b["y"],b["x"]+b["w"],b["y"]+b["h"]))
        ok(im.tobytes()==frames[i].tobytes(),"atlas frame "+str(i))
ims=[Image.new("RGBA",(8,8),(10+i*30,50,90,40+i*60)) for i in range(3)]
for kind in ("apng","webp"):
    if kind=="webp" and not features.check("webp"):continue
    p=Path(root)/("alpha."+kind)
    exporter._animated(ims,12,False,p,kind)
    with Image.open(p) as a:
        ok(a.n_frames==3 and a.info.get("loop")==1,kind+" animation and play once")
        for i,expected in enumerate(ims):
            a.seek(i)
            ok(a.convert("RGBA").tobytes()==expected.tobytes(),kind+" alpha roundtrip "+str(i))
ok(sum(exporter._durations(12,12))==1000,"cumulative duration rounding")
actor=dict(id="a",clip=dict(name="attack",fps=12,pivot=[4,4],frames=[data_url(ims[0])]),flip=True)
effect=dict(id="fx",name="mirror",kind="fireball",radius=8,actor="a",face_actor=True,start=1,end=5,travel_x=60)
scene=dict(name="combat",width=256,height=128,count=8,fps=12,actors=[actor],effects=[effect])
mir,mm,_,flag=E.standalone_scene_effect(scene,"fx")
plain,pm,_,_=E.standalone_scene_effect({**scene,"actors":[{**actor,"flip":False}]},"fx")
ok(flag and mm["pivot"][0]==mir[0].width-pm["pivot"][0],"mirrored origin")
ok(all(a.tobytes()==b.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes() for a,b in zip(mir,plain)),"mirrored export parity")
sout=E.scene_pack(scene,dict(gif=False,godot=False,unity=False),root)
event=json.loads((Path(sout["dir"])/"combat_vfx.json").read_text())["effect_cues"][0]
ok(event["start"]==1 and event["end"]==5 and event["arrival"]==5,"scene cue metadata")
done("test_vfx_export")
