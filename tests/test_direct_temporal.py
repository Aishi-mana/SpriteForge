"""CPU conservative temporal repair."""
from _common import *
from engine import direct_temporal as T
def frame(color):
    im=Image.new("RGBA",(8,8))
    im.paste((*color,255),(2,2,6,6))
    return data_url(im)
a=frame((30,40,50));x=frame((80,90,100));y=frame((140,150,160))
src=dict(version=1,name="original",width=8,height=8,pivot=[4,7],fps=12,frames=[a]*3)
candidate={**src,"frames":[x,y,x]}
body=dict(original=src,candidate=candidate,options=dict(strength=100,max_change=64))
report=T.process(body)
ok(report["rows"][0]["rgb_outliers"]==16 and report["changed"]==[],"analysis only")
result=T.process(body,apply=True)
ok(result["changed"]==[1],"isolated interior correction")
ok(from_url(result["replacements"][0]["image"]).getpixel((3,3))==(80,90,100,255),"correct color outlier")
ok(candidate["frames"]==[x,y,x],"original candidate untouched")
moving={**src,"frames":[a,frame((200,200,200)),a]}
ok(T.process({**body,"original":moving},apply=True)["changed"]==[],"source motion gate protects changing pixels")
ok(T.process({**body,"candidate":{**src,"frames":[a,y,x]}},apply=True)["changed"]==[],"skip unchanged neighbors")
locked={**src,"keyframes":[1],"locked_frames":[1]}
try:T.process({**body,"original":locked,"candidate":{**candidate,"keyframes":[1],"locked_frames":[1]}});ok(False,"reject changed locked frame")
except ValueError:ok(True,"reject changed locked frame")
done("test_direct_temporal")
