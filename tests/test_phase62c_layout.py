from _common import *
from pathlib import Path
import re
ui=(Path(__file__).resolve().parents[1]/"ui/index.html").read_text(encoding="utf-8")
nav=re.search(r'<nav class="tabs sf62nav".*?</nav>',ui,re.S).group()
ids=[int(v) for v in re.findall(r'id="t(\d+)"',nav)]
ok(sorted(ids)==list(range(1,21)),"all 20 workspace buttons retained exactly once")
ok(len(re.findall(r'id="nav62g\d+"',nav))==6,"six categories")
ok('class="sf62queue"' in nav and 'id="t9"' in nav.split('class="sf62queue"')[1],"queue always outside category panels")
render=ui.split("function render(results,target)")[1].split("/*IE61-START*/")[0]
actions=set(re.findall(r'data-a="([^"]+)"',render))
ok(set("instruction history alpha edit rig ref identity modular customrig anim fullframe tile save 1 8".split())<=actions,"all result actions retained")
ok('class="sf62resultMore"' in render and 'class="sf62resultActions"' in render,"primary and advanced actions grouped")
ok("if(group>=0)nav62Show(group)" in ui,"direct navigation opens matching category")
done("test_phase62c_layout")
