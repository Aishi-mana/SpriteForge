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
done("test_system_assets")
