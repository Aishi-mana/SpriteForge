import sys
from pathlib import Path
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import semantic_alpha as S, full_frame_extract as E

def run():
    g=S.graph("frame-0000.png","alpha-0000")
    assert g["bgm"]["inputs"]["bg_removal_name"]==S.MODEL
    assert g["join"]["inputs"]["alpha"]==["inv",0]
    assert E.settings({"method":"birefnet"})["method"]=="birefnet"
    assert E.settings({})["method"]=="chroma"
    images=[Image.new("RGB",(8,8),"white") for _ in range(3)]
    masks=[Image.new("L",(8,8),255),Image.new("L",(8,8),0),Image.new("L",(8,8),255)]
    for a in masks:a.putpixel((3,3),0)
    out=E.stabilize(masks,images,100)
    assert out[1].getpixel((0,0))==255
    assert out[1].getpixel((3,3))==0
    images[1].putpixel((0,0),(0,0,0))
    assert E.stabilize(masks,images,100)[1].getpixel((0,0))==0
    print("ok semantic graph and temporal alpha")

if __name__=="__main__":run()
