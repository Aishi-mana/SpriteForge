from _common import *
from engine import body_base, main, projects, modular
from fastapi import HTTPException

for build in body_base.BUILDS:
    for prop in body_base.PROPORTIONS:
        for view in body_base.VIEWS:
            for pose in body_base.POSES:
                im=body_base.render(build,prop,view,pose,64)
                box=im.getchannel("A").getbbox()
                ok(im.size==(64,64) and box is not None and box[0]>0 and box[1]>0 and box[2]<64 and box[3]<64,"bounded mannequin "+"/".join((build,prop,view,pose)))
a=body_base.render()
b=body_base.render()
ok(a.tobytes()==b.tobytes(),"deterministic template")
ok(body_base.render(pose="t_pose").tobytes()!=a.tobytes(),"pose changes geometry")
ok(body_base.render(view="side").tobytes()!=a.tobytes(),"side projection changes geometry")
ok(body_base.render(size=256,pixel=False).size==(256,256),"HD sampling")
for opts in ({"size":2048},{"color":"bad"},{"view":"bad"}):
    try:
        main.character_body_base(main.BodyBaseParams(**opts))
        ok(False,"invalid preset")
    except HTTPException as e:
        ok(e.status_code==400,"invalid preset rejected")
res=main.character_body_base(main.BodyBaseParams())
ok(res["size"]==[128,128],"CPU endpoint produces default base")
root=tmpdir()
projects.save(root,"bodybase",{"images":{"bodybase":res["sprite"],"characterart":modular.png_uri(a)}})
saved=projects.load(root,"bodybase")["images"]
ok(saved["bodybase"] and saved["characterart"],"independent base and artwork persisted")
projects.save(root,"legacy",{})
ok(projects.load(root,"legacy")["images"]["bodybase"] is None,"legacy project compatible")
done("test_body_base")
