"""Phase 23: full-colour character styles and non-quantizing sprite finishing."""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

PRESETS = {
    "pixel": "pixel art",
    "anime": "modern anime illustration, refined linework, detailed costume, cel shading",
    "rpg_chibi": "stylized JRPG chibi, three-head-tall proportions, detailed costume",
    "super_chibi": "super-deformed cartoon chibi, oversized head, compact proportions",
    "soft_chibi": "soft pastel chibi illustration, gentle shading, rounded shapes",
    "premium_chibi": "polished fantasy RPG chibi illustration, intricate costume, clean shading",
    "custom": "stylized character illustration",
}
HD_NEGATIVE = "blurry, low quality, watermark, text, cropped, multiple characters, extra limbs, malformed hands, pixel art"

def finish(img, size=768, remove_bg=True, tolerance=40):
    """Preserve colour and aspect ratio. Border-connected keying, with a soft edge.
    This is not semantic segmentation; foreground touching a matching background may be lost.
    """
    img = img.convert("RGBA")
    a = np.array(img)
    if remove_bg and a[..., 3].min() == 255:
        rgb = a[..., :3].astype(np.float32)
        border = np.concatenate((rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]))
        keys, counts = np.unique((border / 16).astype(np.int16), axis=0, return_counts=True)
        bg = border[((border / 16).astype(np.int16) == keys[counts.argmax()]).all(axis=1)].mean(axis=0)
        distance = np.max(np.abs(rgb - bg), axis=2)
        tol = max(1, min(100, int(tolerance)))
        labels, _ = ndi.label(distance <= tol)
        edge = np.unique(np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1])))
        mask = np.isin(labels, edge[edge != 0])
        rim = ndi.binary_dilation(mask) & ~mask
        a[..., 3][mask] = 0
        a[..., 3][rim] = np.clip((distance[rim] - tol) / max(1, tol) * 255, 0, 255).astype(np.uint8)
        img = Image.fromarray(a)
    size = max(256, min(1024, int(size)))
    scale = size / max(img.size)
    target = tuple(max(1, round(v * scale)) for v in img.size)
    if target != img.size:
        img = img.resize(target, Image.Resampling.LANCZOS)
    return img, {"size": list(img.size), "pipeline": "hd"}
