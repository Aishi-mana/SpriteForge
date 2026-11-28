import sys,io,base64
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import visual_motion as V

def uri(color,size=(64,64)):
    b=io.BytesIO();Image.new("RGBA",size,color).save(b,"PNG")
    return "data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()

def run():
    a=uri((255,0,0,255));b=uri((0,0,255,255))
    body={"width":256,"height":256,"frames":9,"fps":16,"keys":[{"at":0,"image":a},{"at":100,"image":b}]}
    frames,fps=V.render(body)
    assert len(frames)==9 and fps==16
    assert frames[4].getpixel((128,128))==(255,0,0)
    assert frames[-1].getpixel((128,128))==(0,0,255)
    frames,_=V.render({**body,"mode":"blend"})
    assert frames[4].getpixel((128,128))==(127,0,127)
    for keys in ([{"at":0,"image":a},{"at":90,"image":b}],[{"at":0,"image":a},{"at":100,"image":uri((0,0,0,255),(32,64))}]):
        try:V.render({**body,"keys":keys})
        except ValueError:pass
        else:raise AssertionError("Invalid key poses accepted")
    print("ok aligned visual motion guide")
if __name__=="__main__":run()
