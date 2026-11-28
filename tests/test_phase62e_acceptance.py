from types import SimpleNamespace
from live_acceptance import collect

def fake(path, body, timeout):
    return {"/": "SpriteForge", "/api/state": {"checkpoints": ["model"], "gpu": "test"},
            "/api/resources": {"cuda": True, "busy": False, "memory": {}},
            "/api/queue": {}, "/api/diag": {"summary": {"ok": 1}},
            "/api/diag/gpu_test": {"load_s": 1, "run_s": 2, "peak_vram_gb": 3, "total_vram_gb": 8}}[path]

def run():
    args = SimpleNamespace(checkpoint=None, lora="", gpu_timeout=10)
    calls = []
    def record(path, body, timeout):
        calls.append(path)
        return fake(path, body, timeout)
    assert collect(args, record)["sdxl_gpu"]["status"] == "not_run"
    assert "/api/diag/gpu_test" not in calls
    args.checkpoint = "missing"
    assert collect(args, record)["sdxl_gpu"]["status"] == "blocked"
    args.checkpoint = "model"
    assert collect(args, record)["sdxl_gpu"]["status"] == "pass"
    def fail(path, body, timeout):
        if path == "/api/diag":
            return {"summary": {"fail": 1}}
        return fake(path, body, timeout)
    assert collect(args, fail)["diagnostics"]["status"] == "fail"
    print("ok live acceptance status and opt-in GPU contract")

if __name__ == "__main__":
    run()
