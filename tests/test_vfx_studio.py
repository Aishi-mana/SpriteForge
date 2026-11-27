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
# Exact path endpoints, arc height, fixed canvas, portable recipes.
for kind in vfx.PROJECTILE_KINDS:
    recipe=next(p for p in presets if p["kind"]==kind)
    for path in vfx.PATHS:
        custom=V.validate({**recipe,"count":9,"start":0,"end":8,"path":path,"travel_x":-120,"travel_y":40,"arc_height":64})
        ok(vfx.projectile_offset(custom,0)==(0,0) and vfx.projectile_offset(custom,8)==(-120,40),"exact endpoints "+kind+" "+path)
        expected={"linear":(-60,20),"arc":(-60,-44),"ease_in":(-30,10),"ease_out":(-90,30)}[path]
        ok(vfx.projectile_offset(custom,4)==expected,"midpoint "+path)
        frames,meta=V.render(custom)
        ok(len(frames)==9 and all(im.getbbox() and im.size==tuple(meta["size"]) for im in frames),"visible fixed cells "+kind)
        ok(all(0<im.getbbox()[0]<im.getbbox()[2]<im.width and 0<im.getbbox()[1]<im.getbbox()[3]<im.height for im in frames),"unclipped projectile "+kind)
        single,_=V.render(custom,4)
        ok(single[0].tobytes()==frames[4].tobytes(),"deterministic projectile scrub")
        ok(V.validate(json.loads(json.dumps(custom)))==custom,"projectile portable recipe")
for key,val in (("path","unknown"),("travel_x",513),("travel_y",-513),("arc_height",257)):
    try:V.validate({**r,key:val});ok(False,"reject invalid "+key)
    except ValueError:ok(True,"reject invalid "+key)
# Single-recipe flight/impact sequences, including short impact and inactive frames.
base=next(p for p in presets if p["kind"]=="fireball")
for kind in vfx.IMPACT_KINDS[1:]:
    chain=V.validate({**base,"count":16,"start":2,"end":13,"impact_kind":kind,"impact_frames":5,
                      "impact_scale":180,"impact_color":"#aabbcc","travel_x":-100,"travel_y":40,"path":"arc"})
    ok(vfx.flight_end(chain)==8,"impact flight timing")
    ok(vfx.projectile_offset(chain,8)==(-100,40) and vfx.projectile_offset(chain,13)==(-100,40),"impact anchored at arrival")
    ok(vfx.stage(chain,8)["kind"]=="fireball" and vfx.stage(chain,9)["kind"]==kind,"exact stage transition")
    ok(vfx.stage(chain,9)["color"]=="#aabbcc" and vfx.stage(chain,9)["radius"]==58,"impact settings")
    frames,meta=V.render(chain)
    ok(frames[0].getbbox() is None and frames[15].getbbox() is None,"chain inactive range")
    ok(all(frames[i].getbbox() for i in (2,8,9)),"visible flight and impact")
    same,_=V.render(chain,9)
    ok(same[0].tobytes()==frames[9].tobytes(),"chain deterministic scrub")
    ok(V.validate(json.loads(json.dumps(chain)))==chain,"chain portable recipe")
    short,_=V.render({**chain,"count":3,"start":0,"end":2,"impact_frames":1})
    ok(all(im.getbbox() for im in short),"single frame impact")
    w,h,x,y=vfx.effect_canvas(chain)
    ok(w>=vfx.max_surface_side(chain)+100 and h>=vfx.max_surface_side(chain),"chain canvas bounds")
for bad in ({**base,"impact_kind":"unknown"},{**base,"impact_kind":"explosion","impact_frames":16},
            {**base,"impact_scale":201},{**base,"impact_color":"bad"},
            {**presets[0],"impact_kind":"explosion"}):
    try:V.validate(bad);ok(False,"reject invalid chain")
    except ValueError:ok(True,"reject invalid chain")
# The Scene trajectory and impact controls must live in the Scene edit panel.
from pathlib import Path
html=(Path(__file__).resolve().parents[1]/"ui"/"index.html").read_text(encoding="utf-8")
ok(html.index('id="fxEdit"')<html.index('id="fxProjectileControls"')<html.index('id="fxName"'),"scene trajectory controls in scene panel")
ok(html.index('id="fxEdit"')<html.index('id="fxImpactControls"')<html.index('id="fxName"'),"scene impact controls in scene panel")
# Portable artwork is an optional layer; it never changes trajectory or impact timing.
from engine import vfx_art, modular
from PIL import Image, ImageDraw
im=Image.new("RGBA",(180,100))
ImageDraw.Draw(im).ellipse((5,5,175,95),fill=(220,50,170,255))
uri=vfx_art.normalize(im,False)
ok(max(vfx_art.decoded(uri).size)<=128,"artwork bounded")
base=next(p for p in presets if p["kind"]=="fireball")
custom=V.validate({**base,"artwork":uri,"artwork_opacity":100})
ok(V.validate(json.loads(json.dumps(custom)))==custom,"portable artwork recipe")
original,_=V.render(base,5)
painted,_=V.render(custom,5)
ok(original[0].size==painted[0].size and original[0].tobytes()!=painted[0].tobytes(),"artwork overlays same canvas")
hidden,_=V.render({**custom,"artwork_opacity":0},5)
ok(original[0].tobytes()==hidden[0].tobytes(),"zero opacity retains original")
chain=V.validate({**custom,"impact_kind":"explosion","impact_frames":5})
ok(vfx.stage(chain,chain["end"])["artwork"] is None,"impact does not inherit flight artwork")
for bad in ({"artwork":"bad"},{"artwork":[]},{"artwork_opacity":101},{"artwork":modular.png_uri(Image.new("RGBA",(129,1),(1,2,3,255)))}):
    try:V.validate({**base,**bad});ok(False,"reject invalid artwork")
    except ValueError:ok(True,"reject invalid artwork")
# Relative keyframe tracks preserve the old renderer when absent.
from engine import vfx_keyframes as K
keys=[dict(frame=0,dx=0,dy=0,scale=100,rotation=0,opacity=100,color="#ffffff",easing="linear"),
      dict(frame=8,dx=80,dy=-40,scale=150,rotation=90,opacity=0,color="#ff0000")]
track=V.validate({**base,"count":12,"start":2,"end":10,"keyframes":keys})
mid=vfx.keyframe(track,6)
ok((mid["dx"],mid["dy"],mid["scale"],mid["rotation"],mid["opacity"],mid["color"])==(40,-20,125,45,50,"#ff8080"),"linear keyframe interpolation")
ok(vfx.motion_offset(track,6)==(88,-20),"offset adds to projectile path")
ok(K.sample(K.validate([{**keys[0],"easing":"hold"},keys[1]],9),4)["dx"]==0,"hold keyframe")
ok(K.sample(K.validate([{**keys[0],"easing":"smooth"},keys[1]],9),2)["dx"]==12,"smooth keyframe")
frames,meta=V.render(track)
ok(frames[2].getbbox() is not None and frames[10].getbbox() is None,"keyframe opacity and active timing")
single,_=V.render(track,6)
ok(single[0].tobytes()==frames[6].tobytes(),"keyframe deterministic scrub")
shifted={**track,"count":9,"start":0,"end":8}
shifted_frames,_=V.render(shifted)
ok(shifted_frames[4].tobytes()==frames[6].tobytes(),"relative keys survive active range shift")
ok(V.validate(json.loads(json.dumps(track)))==track,"portable keyframes")
for bad in ([dict(frame=9)],[dict(frame=0),dict(frame=0)],[dict(frame=1,scale=201)],[dict(frame=1,easing="bad")],[dict(frame=1,color="bad")],None):
    try:V.validate({**track,"keyframes":bad});ok(False,"reject invalid keyframes")
    except ValueError:ok(True,"reject invalid keyframes")
done("test_vfx_studio")
