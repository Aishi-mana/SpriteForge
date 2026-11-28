import sys
from pathlib import Path
from PIL import Image, ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import full_frame_extract as E, full_frame_guidance as G

def run():
    im=Image.new("RGBA",(64,64),(240,240,240,255))
    d=ImageDraw.Draw(im)
    d.rectangle((12,8,51,55),fill=(30,40,60,255))
    d.rectangle((20,15,43,25),fill=(240,240,240,255))
    d.rectangle((20,34,43,48),fill=(238,238,238,255))
    out=E.key_frame(im,E.settings({"background":"neutral"}))
    assert out.getpixel((0,0))[3]==0
    assert out.getpixel((30,20))==im.getpixel((30,20))
    assert out.getpixel((30,40))==im.getpixel((30,40))
    assert out.getpixel((12,8))[3]==255
    assert E.key_frame(im,E.settings({"background":"none"})).tobytes()==im.tobytes()
    assert "No bouncing" in G.prompt("",{"preset":"idle_minimal","intensity":"minimal"})
    assert "no gestures or weight shifts" in G.prompt("",{"preset":"idle"})
    assert G.settings()["intensity"]=="auto"
    root=Path(__file__).resolve().parents[1]
    assert "imageio-ffmpeg" in (root/"requirements.txt").read_text()
    assert "import imageio, imageio_ffmpeg" in (root/"spriteforge.bat").read_text()
    print("ok border-connected alpha and idle guidance")

if __name__=="__main__":
    run()
