from _common import *
from engine import character_identity as I, projects
p={"name":"Knight","hair":"red hair","eyes":"blue eyes","outfits":[{"name":"Armor","description":"blue armor"},{"name":"Casual","description":"linen shirt"}],"active_outfit":"Armor","locks":["hair","outfit"]}
clean=I.validate(p)
s=I.prompt(clean,"waving")
ok("red hair" in s and "blue eyes" in s and "blue armor" in s and "linen shirt" not in s and "waving" in s and "preserve hair, outfit" in s,"identity prompt and active outfit")
for bad in (dict(p,active_outfit="missing"),dict(p,locks=["bad"]),dict(p,outfits=p["outfits"]*2),dict(p,hair="x"*301)):
    try:
        I.validate(bad)
        ok(False,"invalid identity")
    except ValueError:
        ok(True,"invalid identity rejected")
root=tmpdir()
projects.save(root,"identity",{"character_identity":p})
ok(projects.load(root,"identity")["character_identity"]==clean,"identity project roundtrip")
projects.save(root,"legacy",{})
ok(projects.load(root,"legacy").get("character_identity") is None,"legacy project compatible")
done("test_character_identity")
