from _common import *
import re
ui=(ROOT/"ui/index.html").read_text(encoding="utf-8")
ok('data-a="send"' in ui and "xs66Open(d.sprite,'Generated sprite')" in ui,"result and queue-history cards share direct transfer action")
ok('onclick="xs66Scene()"' in ui and 'xs66Open(FF.doc.frames[FF.index]' in ui,"animation and frame shortcuts")
ok("await worldImportLayer(input)" in ui and "await sysImportArt(input)" in ui and "await vfxStudioImportArt(input)" in ui,"reuse validated import paths")
ok("now.rev!==initial.rev||mode!==origin" in ui and "if(success)xs66Close()" in ui,"stale and failure guards")
ok("await scnAppend(clip,rev,epoch)" in ui and "SCN.epoch!==epoch||SCN.rev===rev" in ui,"scene append uses existing validation and guards")
ok("Existing frames are kept." in ui and "Replace the current pose reference?" in ui,"explicit replacement confirmations")
done("test_phase66c_transfer")
