from PIL import Image
import numpy as np
from . import pixelize as px, styles

def palette_from_art(image, colors=16, tolerance=40):
    rgb = np.asarray(px.remove_bg(image,tolerance))
    pixels = rgb[rgb[...,3]>=128,:3]
    if not len(pixels):
        raise ValueError("Master has no visible foreground")
    if len(pixels)>65536:
        pixels=pixels[np.linspace(0,len(pixels)-1,65536,dtype=int)]
    q=Image.fromarray(pixels.reshape(1,-1,3)).quantize(colors=colors,dither=Image.Dither.NONE)
    pal=np.asarray(q.getpalette(),dtype=np.uint8).reshape(-1,3)
    return pal[np.unique(np.asarray(q))]

def finish(image, style, size, colors, palette=None, tolerance=40):
    if style=="pixel":
        im,info=px.pixelize(image,"fixed",size,colors,palette if palette is not None else "none",True,tolerance)
    else:
        im,info=styles.finish(image,size,True,tolerance)
        im=px.crop_to_content(im)
    if not im.getchannel("A").getbbox():
        raise ValueError("Sprite has no visible foreground")
    info.update(size=list(im.size),palette_locked=palette is not None and style=="pixel")
    return im,info
