"""Opt-in live acceptance probe. Run against an already launched local SpriteForge."""
import argparse
import datetime
import json
import sys
import time
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8765"

def request(path, body=None, timeout=30):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data,
                                 headers={"Content-Type": "application/json"})
    # Never route local diagnostics through a configured proxy.
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req, timeout=timeout) as res:
        raw = res.read()
        return raw.decode("utf-8") if path == "/" else json.loads(raw)

def collect(args, call=request):
    rows = {}
    def probe(name, path, validate, body=None, timeout=30):
        start = time.monotonic()
        try:
            value = call(path, body, timeout)
            detail = validate(value)
            rows[name] = {"status": "pass", "seconds": round(time.monotonic()-start, 2), "detail": detail}
            return value
        except Exception as exc:
            rows[name] = {"status": "fail", "seconds": round(time.monotonic()-start, 2),
                          "detail": type(exc).__name__}
            return None
    def require(condition, detail):
        if not condition:
            raise ValueError("unexpected response")
        return detail
    probe("http_ui", "/", lambda x: require("SpriteForge" in x, "HTML served"))
    state = probe("state", "/api/state", lambda x: require(isinstance(x["checkpoints"], list),
                  {"gpu": x.get("gpu"), "checkpoint_count": len(x["checkpoints"])}))
    before = probe("resources_before", "/api/resources", lambda x: require(
        isinstance(x["cuda"], bool), {k: x.get(k) for k in ("cuda", "device", "busy", "cached", "memory")}))
    probe("queue", "/api/queue", lambda x: require(isinstance(x, (dict, list)), "JSON received"))
    probe("diagnostics", "/api/diag", lambda x: require(x["summary"].get("fail", 0) == 0,
          x["summary"]), timeout=120)
    rows["sdxl_gpu"] = {"status": "not_run", "detail": "explicit checkpoint required"}
    if args.checkpoint:
        if not state or not before or not before.get("cuda") or before.get("busy") or args.checkpoint not in state["checkpoints"]:
            rows["sdxl_gpu"] = {"status": "blocked", "detail": "CUDA, idle engine and installed checkpoint required"}
        else:
            probe("sdxl_gpu", "/api/diag/gpu_test", lambda x: require(
                all(isinstance(x[k], (int, float)) and x[k] >= 0 for k in
                    ("load_s", "run_s", "peak_vram_gb", "total_vram_gb"))
                and x["total_vram_gb"] > 0, x),
                {"checkpoint": args.checkpoint, "lora": args.lora}, args.gpu_timeout)
    probe("resources_after", "/api/resources", lambda x: require(
        isinstance(x["cuda"], bool), {k: x.get(k) for k in ("cuda", "device", "busy", "cached", "memory")}))
    return rows

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", help="Opt in to real SDXL inference; use an installed checkpoint")
    parser.add_argument("--lora", default="")
    parser.add_argument("--gpu-timeout", type=int, default=900)
    parser.add_argument("--output", type=Path, default=Path("acceptance-report.json"))
    args = parser.parse_args()
    if args.gpu_timeout <= 0:
        parser.error("--gpu-timeout must be positive")
    rows = collect(args)
    report = {"timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "scope": "local API and optional SDXL inference; not desktop interaction",
              "checks": rows}
    # Avoid accidentally overwriting earlier evidence.
    with args.output.open("x", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    for name, row in rows.items():
        print(name, row["status"])
    print("Report:", args.output)
    return int(any(r["status"] in ("fail", "blocked") for r in rows.values()))

if __name__ == "__main__":
    sys.exit(main())
