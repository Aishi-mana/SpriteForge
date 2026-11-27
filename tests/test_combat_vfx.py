"""Combat cue scheduling, mirrored attachment, target flight and preview."""
from _common import *
from engine import combat_vfx as C, scenes as S, vfx
from PIL import Image
import copy
im=Image.new("RGBA",(8,8),(255,0,0,255))
clip=dict(name="attack",fps=6,pivot=[4,4],frames=[data_url(im)]*4,loop=False)
a=dict(id="a",name="caster",clip=clip,x=40,y=60,end_x=56,end_y=60,start=2,end=17,scale=150,flip=True,behavior="hold")
b=dict(id="b",name="target",clip=clip,x=130,y=60,end_x=160,end_y=80,start=0,end=17,behavior="hold")
effect=dict(id="fx",kind="fireball",start=0,end=7,x=0,y=0,radius=8,impact_kind="explosion",impact_frames=2)
scene=dict(name="combat",width=256,height=128,count=18,fps=12,actors=[a,b],effects=[effect])
req=dict(effect="fx",source="a",target="b",clip_frame=1,earliest=0,delay=1,x=10,y=-8,target_x=0,target_y=-8)
follow=C.cue(scene,{**req,"mode":"follow"})
e=follow["scene"]["effects"][0]
ok(follow["trigger"]==4 and follow["start"]==5 and follow["end"]==12,"source frame timing")
ok(e["actor"]=="a" and e["face_actor"] and (e["x"],e["y"])==(15,-12),"scaled mirrored attachment")
launch=C.cue(scene,{**req,"mode":"launch"})["scene"]["effects"][0]
ok(launch["actor"] is None and launch["world_flip"] and launch["travel_x"]==96 and launch["x"]==28,"launch captures facing and origin")
repeat=C.cue(C.cue(scene,{**req,"mode":"launch"})["scene"],{**req,"mode":"launch"})["scene"]["effects"][0]
ok(repeat==launch,"reapplying launch does not reverse direction")
aim=C.cue(scene,{**req,"mode":"projectile_target"})
e=aim["scene"]["effects"][0]
arr=aim["arrival"];target=aim["scene"]["actors"][1]
ax,ay=S.position(target,arr);dx,dy=vfx.motion_offset(e,arr)
ok((e["x"]+dx,e["y"]+dy)==(ax,ay-8),"target exact sampled arrival")
frames,meta=S.render(aim["scene"])
one,_=S.render(aim["scene"],arr)
ok(frames[arr].tobytes()==one[0].tobytes(),"combat scrub parity")
preview,meta=C.behavior_clip(follow["scene"],"fx")
ok(len(preview)==8 and meta["pivot"]==list(vfx.effect_canvas(follow["scene"]["effects"][0])[2:]),"behavior preview uses actual origin")
targeted=C.cue(scene,{**req,"mode":"target"})["scene"]["effects"][0]
ok(targeted["actor"] is None and (targeted["x"],targeted["y"])==(139,58),"target anchor sampled at trigger")
for bad in ({"source":"missing"},{"clip_frame":4},{"earliest":17},{"delay":63},{"mode":"projectile_target","target":"missing"}):
    try:C.cue(scene,{**req,**bad});ok(False,"reject invalid combat cue")
    except ValueError:ok(True,"reject invalid combat cue")
ok(scene["effects"][0]==effect,"cue does not mutate input")
done("test_combat_vfx")
