"""Bounded portable effect artwork. No model dependency in rendering."""
from functools import lru_cache
from PIL import Image
from . import modular

MAX_ART_URI=100000
MAX_ART_SIZE=128

def normalize(image,pixel=True):
    im=image.convert("RGBA")
    bbox=im.getchannel("A").getbbox()
    if not bbox:raise ValueError("Artwork is fully transparent")
    im=im.crop(bbox)
    if max(im.size)>MAX_ART_SIZE:
        im.thumbnail((MAX_ART_SIZE,MAX_ART_SIZE),Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS)
    uri=modular.png_uri(im)
    if len(uri)>MAX_ART_URI:raise ValueError("Artwork exceeds portable recipe budget")
    return uri

@lru_cache(maxsize=32)
def decoded(uri):
    if not isinstance(uri,str) or len(uri)>MAX_ART_URI or not uri.startswith("data:image/png;base64,"):
        raise ValueError("Invalid or oversized effect artwork")
    im=modular.decode(uri)
    if max(im.size)>MAX_ART_SIZE or not im.getchannel("A").getbbox():
        raise ValueError("Effect artwork must be visible and at most 128 px per side")
    return im

def validate(uri):
    if uri is None:return None
    if not isinstance(uri,str):raise ValueError("Invalid effect artwork")
    decoded(uri)
    return uri

def overlay(canvas,uri,radius,angle,alpha,scale,pixel):
    if not uri or alpha<=0:return
    source=decoded(uri)
    size=max(1,round(2*radius*scale))
    factor=size/max(source.size)
    resample=Image.Resampling.NEAREST if pixel else Image.Resampling.BICUBIC
    im=source.resize(tuple(max(1,round(v*factor)) for v in source.size),resample)
    if angle:im=im.rotate(-angle,resample=resample,expand=True)
    im.putalpha(im.getchannel("A").point([round(v*min(1,max(0,alpha))) for v in range(256)]))
    canvas.alpha_composite(im,((canvas.width-im.width)//2,(canvas.height-im.height)//2))
