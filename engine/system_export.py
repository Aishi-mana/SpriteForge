"""Portable System Studio asset packs; engine mappings are data, not native scenes."""
import io, json, zipfile
from . import system_assets as S, world

def bundle(theme):
    d=S.validate(theme)
    assets=[]
    output=io.BytesIO()
    with zipfile.ZipFile(output,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for a in d["assets"]:
            category=a.get("icon",{}).get("category")
            path=("icons/"+category if category else "art/"+a["role"])+"/"+a["id"]+".png"
            im=world.image(a["image"]);buf=io.BytesIO();im.save(buf,"PNG")
            z.writestr(path,buf.getvalue())
            assets.append({**{k:v for k,v in a.items() if k!="image"},"path":path})
        lookup={a["id"]:a["path"] for a in assets}
        parts=[]
        for order,p in enumerate(d["components"]):
            part={**p,"order":order}
            if p["kind"]=="image":
                part["path"]=lookup[p["asset"]]
                if p.get("control"):
                    part["state_paths"]={k:lookup[v] for k,v in p["control"]["states"].items()}
            parts.append(part)
        manifest=dict(format="spriteforge-system-pack",version=1,name=d["name"],width=d["width"],height=d["height"],pixel=d["pixel"],style=d["style"],palette=d["palette"],origin="top-left",units="pixels",assets=assets,components=parts)
        def write_json(path,obj):z.writestr(path,json.dumps(obj,ensure_ascii=False,indent=2))
        write_json("manifest.json",manifest)
        write_json("theme.json",dict(format="spriteforge-system-theme",version=1,theme=d))
        godot=[];unity=[]
        for p in parts:
            g=dict(id=p["id"],node="NinePatchRect" if "slice" in p else {"image":"TextureRect","rect":"ColorRect","text":"Label"}[p["kind"]],position=[p["x"],p["y"]],size=[p["width"],p["height"]],order=p["order"])
            q=dict(id=p["id"],component={"image":"Image","rect":"Image","text":"Text"}[p["kind"]],anchor=[0,1],pivot=[0,1],anchored_position=[p["x"],-p["y"]],size_delta=[p["width"],p["height"]],order=p["order"])
            if "path" in p:g["texture"]=q["texture"]=p["path"]
            if "slice" in p:
                b=p["slice"];g["patch_margins"]=b;q["sprite_border"]=[b[k] for k in ("left","bottom","right","top")];q["image_type"]="Sliced"
            godot.append(g);unity.append(q)
        write_json("godot/layout.json",dict(format="spriteforge-godot-hints",version=1,components=godot))
        write_json("unity/layout.json",dict(format="spriteforge-unity-hints",version=1,components=unity))
        z.writestr("README.txt","SpriteForge System UI pack\n\nmanifest.json is the authoritative layout, states, resources and motion data. theme.json is the editable SpriteForge roundtrip. PNG paths are relative to the archive root. Artwork alpha is preserved; opaque source art remains opaque. Components are back-to-front, pixel units, top-left origin. Godot and Unity JSON files are integration hints, not native scenes or import scripts. For Godot use Control nodes with top-left positioning and texture filter nearest for pixel art. For Unity use a top-left anchored Canvas, import PNGs as Sprite (2D and UI), apply borders in left,bottom,right,top order and use Sliced Image. Use manifest state_paths, resource and motion fields to implement runtime behavior. No gameplay scripts are included.\n")
    return output.getvalue()
