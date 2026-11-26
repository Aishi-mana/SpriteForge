"""The web page: script syntax, element ids, and the JavaScript unit tests (needs node)."""
import re, shutil, subprocess
from _common import *

html = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")
ids = set(re.findall(r'id="([^"]+)"', html)); used = set(re.findall(r"\$\('([^']+)'\)", html))
missing = sorted(u for u in used if u not in ids and u != "t" and not u.startswith(("xc_", "xp_", "dc_")))
ok(not missing, "every $('id') used by the script exists in the page" + (f" MISSING {missing}" if missing else ""))
ok(len(re.findall(r'id="([^"]+)"', html)) == len(ids), "no duplicate element ids")
node = shutil.which("node")
if not node:
    ok(True, "node not installed: JavaScript tests skipped")
else:
    script = re.search(r"<script>(.*)</script>", html, re.S).group(1); tmp = tmpdir() / "ui.js"; tmp.write_text(script, encoding="utf-8")
    r = subprocess.run([node, "--check", str(tmp)], capture_output=True, text=True); ok(r.returncode == 0, "the page script parses" + ("" if r.returncode == 0 else "\n" + r.stderr[:400]))
    for f in ("pxe_test.js", "options_test.js", "editor_test.js", "queue_test.js", "pose_presets_test.js", "phase61_test.js", "phase61f_test.js"):
        r = subprocess.run([node, str(Path(__file__).parent / "js" / f)], capture_output=True, text=True)
        out = r.stdout.strip().splitlines(); ok(r.returncode == 0 and out and out[-1].strip() == "ALL PASSED", f"js/{f}: " + (out[-1] if out else r.stderr[:200]) + f" ({sum(1 for l in out if l.startswith('ok'))} checks)")
        if r.returncode != 0:
            print("\n".join(l for l in out if l.startswith("FAIL")))
            print(r.stderr[-4000:])
done("test_ui")
