"""CPU direct video timestamp regression."""
from _common import *
from engine import direct_video as V
ok(V.sampling(0,1000,4,12)==[0,3,6,9],"source timestamps")
ok(V.sampling(500,1000,4,12)==[6,9],"nonzero start")
ok(V.sampling(0,500,8,4)==[0,0,1,1],"hold sampled source frames")
for args in [(1000,1000,12,12),(0,60000,30,30)]:
    try:V.sampling(*args);ok(False,"reject invalid range or budget")
    except ValueError:ok(True,"reject invalid range or budget")
try:V.edit(b"bad",{});ok(False,"reject non MP4")
except ValueError:ok(True,"reject non MP4")
done("test_direct_video")
