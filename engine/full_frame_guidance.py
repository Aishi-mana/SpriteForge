"""Reference-conditioned sprite motion guidance; prompts are not hard identity locks."""
from . import world, motion_templates

PRESETS={
    "custom":"",
    "idle":"Very slow, barely visible breathing; tiny chest movement only, feet planted, head, hands, weapon and torso position steady, mouth closed, no gestures or weight shifts.",
    "idle_minimal":"Near-still idle, tiny periodic breathing only; keep silhouette, expression, limbs, hair, clothing and weapon almost stationary. No bouncing, swaying, gestures or camera motion.",
    "alert":"Alert idle, steady gaze, small shoulder tension, planted feet.",
    "floating":"Gentle floating idle, relaxed limbs, stable expression.",
    "weapon_ready":"Steady weapon-ready stance, subtle breathing, fixed grip.",
    "walk":"Natural alternating steps, coordinated arm swing and planted feet.",
    "run":"Energetic running stride, coordinated arms, believable weight transfer.",
    "jump":"Anticipation crouch, takeoff, airborne arc, soft landing and recovery.",
    "attack":"Anticipation, decisive attack, follow-through and recovery.",
    "cast":"Gather energy, deliberate casting gesture, release and recovery.",
    "hurt":"Brief recoil and recovery while maintaining balance.",
    "slash":"Weapon swing with clear windup, sweeping arc, contact pose and recovery.",
    "thrust":"Controlled forward thrust, extension and return to ready stance.",
    "heavy":"Slow windup, forceful full-body attack, follow-through and recovery.",
    "ranged":"Aim, release, recoil and reset; maintain consistent equipment.",
    "block":"Raise guard, brace on impact and return to ready stance.",
    "dodge":"Quick evasive movement, controlled landing and recovery.",
    "parry":"Brief defensive deflection and return to ready stance.",
    "defeat":"Loss of balance, controlled fall and final resting pose.",
}
INTENSITIES={"auto":"","minimal":"Use the smallest visible motion appropriate to the requested action; avoid unnecessary secondary motion, exaggerated gestures and displacement.","subtle":"Restrained, controlled movement with modest amplitude and minimal secondary motion.","normal":"Natural motion appropriate to the action.","dynamic":"Expressive motion appropriate to the action, while preserving the character."}
VIEWS={"reference":"Preserve the reference viewing angle.","front":"Front view.","side":"Side view.","quarter":"Three-quarter view.","back":"Rear view."}
BACKGROUNDS={"neutral":((240,240,240),"light neutral gray"),"green":((0,255,0),"solid chroma green"),"magenta":((255,0,255),"solid chroma magenta"),"blue":((0,0,255),"solid chroma blue")}
def settings(value=None):
    if value is None:value={}
    if not isinstance(value,dict):raise ValueError("Invalid motion guidance")
    out={}
    for key,choices,default in (("preset",PRESETS,"custom"),("view",VIEWS,"reference"),("background",BACKGROUNDS,"neutral"),("intensity",INTENSITIES,"auto")):
        q=value.get(key,default)
        if not isinstance(q,str) or q not in choices:raise ValueError("Invalid motion "+key)
        out[key]=q
    for key in ("identity","camera","in_place","loop"):
        out[key]=world.boolean(value.get(key,True),"motion "+key)
    out["margin"]=world.integer(value.get("margin",10),0,30,"reference margin")
    out["poses"]=motion_templates.validate(value.get("poses"))
    return out

def prompt(text,guidance=None):
    q=settings(guidance)
    text=world.label(text,"motion description",2000,True)
    if not text and q["preset"]=="custom" and not q["poses"]:raise ValueError("Describe the motion or choose a preset")
    parts=[text,PRESETS[q["preset"]],INTENSITIES[q["intensity"]],motion_templates.describe(q["poses"])]
    if q["preset"] in ("idle","idle_minimal","alert","weapon_ready") and q["identity"]:
        parts.append("Maintain the original facial expression and eye state throughout; lips and jaw remain still, no speech, blinking or facial animation. Breathing is confined to tiny chest movement; head, hands and equipment remain steady.")
    if q["identity"]:parts.append("Same character as reference, consistent face, body proportions, hairstyle, outfit, accessories, colors and original art style; coherent complete character poses.")
    parts.append(VIEWS[q["view"]])
    if q["camera"]:parts.append("Fixed camera, fixed framing and scale, no zoom, pan, cuts or camera rotation.")
    if q["in_place"]:parts.append("Animate in place, keep character centered horizontally, stable ground contact except intentional airborne motion.")
    if q["loop"]:parts.append("Return to the starting pose for a seamless repeating cycle.")
    parts.append("Single full-body character entirely in frame, uniform "+BACKGROUNDS[q["background"]][1]+" background, no scenery, lettering or extra characters.")
    return " ".join(p for p in parts if p)


def negative(guidance=None):
    q=settings(guidance)
    base="blurry, distorted, watermark, text"
    if q["preset"] in ("idle","idle_minimal","alert","weapon_ready") and q["identity"]:
        return base+", talking, lip movement, jaw movement, changing expression, blinking, head turning, arm gestures, exaggerated breathing"
    return base
