"""Shared descriptive character identity; reference conditioning is not a hard identity lock."""
FIELDS = ("name", "appearance", "hair", "eyes", "palette", "accessories")
LOCKS = ("appearance", "hair", "eyes", "palette", "accessories", "outfit")

def validate(value):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Invalid character identity")
    out = {}
    for key in FIELDS:
        v = value.get(key, "")
        if not isinstance(v, str) or len(v) > (60 if key == "name" else 300):
            raise ValueError("Invalid identity field: " + key)
        out[key] = v.strip()
    outfits = value.get("outfits", [])
    if not isinstance(outfits, list) or len(outfits) > 8:
        raise ValueError("At most eight outfits")
    clean = []
    names = set()
    for o in outfits:
        if not isinstance(o, dict):
            raise ValueError("Invalid outfit")
        name, desc = o.get("name"), o.get("description")
        if not isinstance(name,str) or not name.strip() or len(name)>60 or name.strip() in names or not isinstance(desc,str) or len(desc)>300:
            raise ValueError("Invalid or duplicate outfit")
        names.add(name.strip())
        clean.append({"name":name.strip(), "description":desc.strip()})
    active = value.get("active_outfit", "")
    if not isinstance(active,str) or (active and active not in names):
        raise ValueError("Unknown active outfit")
    locks = value.get("locks", [])
    if not isinstance(locks,list) or any(not isinstance(k,str) or k not in LOCKS for k in locks) or len(set(locks))!=len(locks):
        raise ValueError("Invalid identity locks")
    return dict(out,outfits=clean,active_outfit=active,locks=locks)

def prompt(profile, extra=""):
    p = validate(profile)
    if p is None:
        return extra
    parts = [p[k] for k in FIELDS[1:] if p[k]]
    outfit = next((o["description"] for o in p["outfits"] if o["name"]==p["active_outfit"]), "")
    if outfit:
        parts.append(outfit)
    if p["locks"]:
        parts.append("preserve " + ", ".join(p["locks"]) + " consistently")
    if extra.strip():
        parts.append(extra.strip())
    return ", ".join(parts)
