"""Standalone lossless WebP downloads; project and engine pack formats stay PNG."""
import base64
import binascii
import io
from PIL import Image, features

MAX_PIXELS = 16_000_000
MAX_ENCODED = 48_000_000
MAX_SIDE = 16383  # WebP bitstream dimension limit

def encode(image, scale=1):
    if type(scale) is not int or scale not in (1, 8):
        raise ValueError("Choose 1x or 8x export")
    prefix = "data:image/png;base64,"
    if not isinstance(image,str) or not image.startswith(prefix) or len(image)>MAX_ENCODED:
        raise ValueError("Expected a bounded PNG image")
    if not features.check("webp"):
        raise ValueError("WebP encoder unavailable in this Pillow installation")
    try:
        raw=base64.b64decode(image[len(prefix):],validate=True)
        with Image.open(io.BytesIO(raw),formats=["PNG"]) as src:
            w,h=src.width*scale,src.height*scale
            if max(w,h)>MAX_SIDE or w*h>MAX_PIXELS:
                raise ValueError("WebP export exceeds image budget (16 million pixels)")
            im=src.convert("RGBA")
        if scale!=1:
            im=im.resize((w,h),Image.Resampling.NEAREST)
        out=io.BytesIO()
        im.save(out,format="WEBP",lossless=True,quality=90,method=4,exact=True)
        return "data:image/webp;base64,"+base64.b64encode(out.getvalue()).decode("ascii")
    except (OSError,binascii.Error,Image.DecompressionBombError) as e:
        raise ValueError("Cannot encode WebP: "+str(e)) from e
