"""Reusable artwork references, independent text, project and archive validation."""
from _common import *
from engine import system_assets as S, projects
from PIL import Image
import json, copy
art=data_url(Image.new("RGBA",(24,16),(40,80,120,180)))
d={**S.default(),"palette":["#AABBCC","#aabbcc"],"assets":[dict(id="panel",role="panel",image=art)],"components":[
 dict(id="p1",kind="image",asset="panel",x=10,y=10,width=240,height=80),
 dict(id="p2",kind="image",asset="panel",x=300,y=10,width=120,height=40),
 dict(id="label",kind="text",text="Health",color="#ffffff",font_size=18),
 dict(id="bar",kind="rect",color="#aa4455",border_width=0)]}
d=S.validate(d)
ok(len(d["assets"])==1 and len(d["components"])==4,"reuse artwork independently")
ok(d["assets"][0]["width"]==24 and d["assets"][0]["height"]==16,"decoded dimensions authoritative")
ok(d["palette"]==["#aabbcc"] and d["components"][2]["text"]=="Health","normalized palette and editable text")
ok(S.validate(json.loads(json.dumps(d)))==d,"portable theme roundtrip")
for bad in ({**d,"version":2},{**d,"width":3072,"height":3072},{**d,"assets":[]},
            {**d,"assets":d["assets"]*2},{**d,"components":d["components"]*2},
            {**d,"assets":[{**d["assets"][0],"image":"bad"}]},
            {**d,"components":[{**d["components"][2],"font_size":999}]},
            {**d,"palette":["not a color"]}):
    try:S.validate(bad);ok(False,"reject invalid theme")
    except ValueError:ok(True,"reject invalid theme")
root=tmpdir()
projects.save(root,"Theme",{"system_theme":d,"tab":19})
ok(projects.load(root,"Theme")["system_theme"]==d,"save/load")
projects.restore_bundle(root,"Copy",projects.bundle(root,"Theme"))
ok(projects.load(root,"Copy")["system_theme"]==d,"archive restore")
try:projects.save(root,"Theme",{"system_theme":{**d,"assets":[]}});ok(False,"reject broken references")
except ValueError:ok(projects.load(root,"Theme")["system_theme"]==d,"invalid save preserves prior theme")
projects.save(root,"Legacy",{})
ok(projects.load(root,"Legacy").get("system_theme") is None,"legacy compatible")
from engine import system_kit as K
profile={"name":"Shared", "notes":"silver filigree", "palette":["#aabbcc"], "accents":True}
theme=S.validate({**d,"prompt":"Moonlit fantasy","style_profile":profile})
ok(S.validate(theme)==theme,"shared profile roundtrip")
ok("silver filigree" in K.prompt(theme,"starter","panel"),"shared style prompt")
ok("no lettering" in K.prompt(theme,"starter","button"),"editable labels remain separate")
_,roles=K.plan(theme,"starter")
transparent=data_url(Image.new("RGBA",(24,16),(40,80,120,180)))
result=K.assemble(theme,"starter",{role:transparent for role in roles})
ok(len(result["assets"])==len(theme["assets"])+6 and result["components"]==theme["components"],"append kit atomically")
ok(len(theme["assets"])==1,"original unchanged")
for assets in ({}, {role:data_url(Image.new("RGBA",(24,16),(40,80,120,255))) for role in roles}):
    try:K.assemble(theme,"starter",assets);ok(False,"reject invalid kit")
    except ValueError:ok(True,"reject invalid kit")
projects.save(root,"Shared",{"system_theme":result})
ok(projects.load(root,"Shared")["system_theme"]==result,"profile and kit persist")
sliced=copy.deepcopy(result)
sliced["components"][0]["slice"]=dict(left=4,top=3,right=5,bottom=3)
sliced=S.validate(sliced)
ok(sliced["components"][0]["slice"]["right"]==5,"nine-slice margins preserved")
ok(S.validate(json.loads(json.dumps(sliced)))==sliced,"nine-slice JSON roundtrip")
for margins in ({"left":24},{"top":8,"bottom":8},{"left":-1},{"right":1.5},[]):
    bad=copy.deepcopy(sliced);bad["components"][0]["slice"]=margins
    try:S.validate(bad);ok(False,"invalid nine-slice")
    except ValueError:ok(True,"invalid nine-slice rejected")
projects.save(root,"Sliced",{"system_theme":sliced})
projects.restore_bundle(root,"SlicedCopy",projects.bundle(root,"Sliced"))
ok(projects.load(root,"SlicedCopy")["system_theme"]==sliced,"nine-slice archive persistence")
controlled=copy.deepcopy(sliced)
controlled["components"][0]["control"]=dict(mode="toggle",states={"hovered":"kit_1"})
controlled=S.validate(controlled)
ok(controlled["components"][0]["control"]["enabled"],"control defaults")
ok(S.validate(json.loads(json.dumps(controlled)))==controlled,"control roundtrip")
for control in ({"mode":"bad"},{"states":{"bad":"kit_1"}},{"states":{"pressed":"missing"}},{"enabled":"yes"}):
    bad=copy.deepcopy(controlled);bad["components"][0]["control"]=control
    try:S.validate(bad);ok(False,"invalid control")
    except ValueError:ok(True,"invalid control rejected")
projects.save(root,"Controls",{"system_theme":controlled})
ok(projects.load(root,"Controls")["system_theme"]==controlled,"control persistence")
from engine import system_icons as I
from engine import world
opts=dict(category="weapon",name="Moonblade",subject="silver crescent sword",size=64)
ok("silver filigree" in I.prompt(theme,opts) and "silver crescent sword" in I.prompt(theme,opts),"icon shared guidance")
raw=Image.new("RGBA",(100,80),(0,0,0,0))
raw.paste((120,90,40,255),(30,10,70,70))
uri=I.normalize(raw,(0,0,0),30,False,64)
im=world.image(uri)
ok(im.size==(64,64) and im.getchannel("A").getbbox() is not None and im.getpixel((0,0))[3]==0,"square transparent icon")
with_icon=I.append(controlled,opts,uri)
ok(with_icon["assets"][-1]["icon"]["category"]=="weapon" and len(with_icon["assets"])==len(controlled["assets"])+1,"categorized append")
ok(S.validate(with_icon)==with_icon,"icon metadata roundtrip")
for bad in ({**opts,"size":33},{**opts,"category":"unknown"}):
    try:I.settings(bad);ok(False,"invalid icon options")
    except ValueError:ok(True,"invalid icon rejected")
projects.save(root,"Icons",{"system_theme":with_icon})
ok(projects.load(root,"Icons")["system_theme"]==with_icon,"icon persistence")
done("test_system_assets")
