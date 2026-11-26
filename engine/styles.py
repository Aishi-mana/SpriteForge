"""Phase 23: full-colour character styles and non-quantizing sprite finishing."""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

PRESETS = {
    "pixel": "pixel art",
    "anime": "modern anime illustration, refined linework, cel shading",
    "rpg_chibi": "stylized JRPG chibi, three-head-tall proportions, clean linework",
    "super_chibi": "super-deformed cartoon chibi, oversized head, compact proportions",
    "soft_chibi": "soft pastel chibi illustration, gentle shading, rounded shapes",
    "premium_chibi": "polished RPG chibi illustration, refined linework, clean shading",
    # Head count means total standing height divided by head height, not head count.
    "head_2": "super-deformed chibi illustration, total standing height approximately twice head height, very large head, compact torso and short limbs",
    "head_3": "chibi illustration, total standing height approximately three times head height, large head, compact torso and limbs",
    "head_4": "stylized chibi illustration, total standing height approximately four times head height, moderately oversized head, balanced compact limbs",
    "head_5": "semi-chibi illustration, total standing height approximately five times head height, moderately stylized head and longer limbs",
    "head_6": "stylized anime illustration, total standing height approximately six times head height, balanced torso and elongated limbs",
    "head_7": "anime illustration, total standing height approximately seven times head height, natural stylized head-to-body ratio and long limbs",
    "custom": "stylized character illustration",
}
HD_NEGATIVE = "blurry, low quality, watermark, text, cropped, multiple characters, extra limbs, malformed hands, pixel art"

def finish(img, size=768, remove_bg=True, tolerance=40, background=None):
    """Preserve colour and aspect ratio. Flat-background and enclosed-pocket keying, with a soft edge.
    This is not semantic segmentation; foreground touching a matching background may be lost.
    """
    img = img.convert("RGBA")
    if remove_bg and img.getchannel("A").getextrema()==(255,255):
        from .alpha_cleanup import clean
        img,_ = clean(img,tolerance,mode="smart",background=background,soft=True)
    size = max(256, min(1024, int(size)))
    scale = size / max(img.size)
    target = tuple(max(1, round(v * scale)) for v in img.size)
    if target != img.size:
        img = img.resize(target, Image.Resampling.LANCZOS)
    return img, {"size": list(img.size), "pipeline": "hd"}
