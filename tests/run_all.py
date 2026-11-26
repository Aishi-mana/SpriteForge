"""Run every test file and print one summary. Usage:  python tests/run_all.py   (from the project folder)"""
import subprocess, sys, time, os
from pathlib import Path
here = Path(__file__).parent
files = sorted(here.glob("test_*.py")); rows = []
for f in files:
    t = time.time()
    try:
        r = subprocess.run([sys.executable, str(f)], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=here,
                           timeout=180, env={**os.environ,"PYTHONUTF8":"1","HF_HUB_OFFLINE":"1","TRANSFORMERS_OFFLINE":"1"})
    except subprocess.TimeoutExpired:
        print(f"\\n--- {f.stem} timed out after 180 seconds ---")
        rows.append((f.stem,False,0,1,time.time()-t));continue
    out = r.stdout.strip().splitlines(); n_ok = sum(1 for l in out if l.startswith("ok")); fails = [l for l in out if l.startswith("FAIL")]
    rows.append((f.stem, r.returncode == 0, n_ok, len(fails), time.time() - t))
    if r.returncode != 0:
        print(f"\n--- {f.stem} failed ---"); print("\n".join(fails) or (r.stdout + r.stderr)[-1500:])
print("\n" + "=" * 64)
for name, good, n_ok, nf, dt in rows: print(f"{'PASS' if good else 'FAIL'}  {name:26s} {n_ok:4d} checks  {dt:5.1f}s")
tot = sum(r[2] for r in rows); bad = [r[0] for r in rows if not r[1]]
print("=" * 64 + f"\n{tot} checks, " + ("ALL TEST FILES PASSED" if not bad else f"FAILED: {', '.join(bad)}"))
sys.exit(1 if bad else 0)
