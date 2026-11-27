"""CPU tests for the dedicated VFX Studio; no GPU/model required."""
from _common import *
from engine import vfx_studio as V, scenes, exporter, vfx
import json

presets=V.presets()
ok({r["kind"] for r in presets}==set(vfx.KINDS),"every existing effect has a standalone preset")
for recipe in presets:
    ok(V.validate(json.loads(json.dumps(recipe)))==recipe,"portable recipe "+recipe["kind"])
    frames,meta=V.render(recipe)
    ok(len(frames)==recipe["count"] and meta["fps"]==recipe["fps"] and meta["loop"]==recipe["loop"],"timing "+recipe["kind"])
    ok(all(im.mode=="RGBA" and im.size==tuple(meta["size"]) for im in frames),"fixed transparent cell "+recipe["kind"])
    ok(any(im.getchannel("A").getbbox() is not None for im in frames),"visible effect "+recipe["kind"])
    i=recipe["count"]//2
    single,_=V.render(recipe,i)
    ok(single[0].tobytes()==frames[i].tobytes(),"scrub equals full render "+recipe["kind"])
    same,_=scenes.render(V.scene(recipe))
    ok(same[i].tobytes()==frames[i].tobytes(),"scene renderer parity "+recipe["kind"])
r={**presets[0],"count":8,"start":2,"end":5,"pixel":False}
frames,meta=V.render(r)
ok(frames[0].getbbox() is None and frames[7].getbbox() is None,"inactive frames transparent")
root=tmpdir()
out=exporter.export_pack([{**meta,"frames":frames}],{"layout":"grid","columns":4,"crop":False,"gif":False,"godot":False,"unity":False,"frames":True},"effect",root)
ok(out["frames"]==8 and out["cell"]==meta["size"],"fixed canvas sheet export")
for bad in ({**r,"kind":"unknown"},{**r,"end":9},{**r,"count":33},{**r,"color":"bad"},{**r,"loop":"yes"},None):
    try:V.validate(bad);ok(False,"reject malformed recipe")
    except ValueError:ok(True,"reject malformed recipe")
# Advanced ribbons preserve recipe fields and are deterministic in pixel/smooth modes.
for kind in vfx.SLASH_KINDS:
    recipe=next(p for p in presets if p["kind"]==kind)
    for pixel in (True,False):
        custom={**recipe,"sweep":135,"thickness":35,"trail":70,"glow":90,"pixel":pixel,"seed":91}
        normalized=V.validate(custom)
        ok(all(normalized[k]==custom[k] for k in ("sweep","thickness","trail","glow")),"advanced settings roundtrip "+kind)
        frames,_=V.render(custom)
        ok(len({im.tobytes() for im in frames})>2,"animated ribbon "+kind)
        ok(all(im.getchannel("A").getextrema()[0]==0 for im in frames),"transparent background "+kind)
        same,_=V.render(custom,len(frames)//2)
        ok(same[0].tobytes()==frames[len(frames)//2].tobytes(),"deterministic scrub "+kind)
    short,_=V.render({**recipe,"count":2,"start":0,"end":1})
    ok(any(im.getchannel("A").getbbox() for im in short),"short clip visible "+kind)
for key,val in (("sweep",361),("thickness",0),("trail",-1),("glow",101)):
    try:V.validate({**r,key:val});ok(False,"reject invalid "+key)
    except ValueError:ok(True,"reject invalid "+key)
legacy={k:v for k,v in presets[0].items() if k not in ("sweep","thickness","trail","glow")}
ok(V.validate(legacy)==presets[0],"old recipes get compatible defaults")
done("test_vfx_studio")
