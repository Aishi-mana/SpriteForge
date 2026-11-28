from _common import *
from pathlib import Path
ui=(Path(__file__).resolve().parents[1]/"ui/index.html").read_text(encoding="utf-8")
ok('data-a="fullframe"' in ui and "b.dataset.a=='fullframe'?ffFromResult(d.sprite)" in ui,"result full-frame action wired")
ok("if(!restore)tab(4)" in ui and "aImg.onerror=" in ui,"rig navigation and decode failure")
ok("await ffCommit({...FF.doc,reference:src})" in ui,"reference handoff preserves existing frames")
ok("ticket!==(QS.historyTicket||0)||page!==QS.page" in ui,"history stale response guard")
done("test_phase62a_ui_contract")
