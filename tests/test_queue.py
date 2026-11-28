"""Generation queue + history: the job manager (fake executor) and the endpoints (fake SDXL)."""
import threading, time
from _common import *
from PIL import ImageDraw
stubbed = install_fastapi_stubs()
from engine import jobs, main as M
HTTPException = http_exception()


def fake_result(seed):
    s = Image.new("RGBA", (16, 16), (0, 0, 0, 0)); ImageDraw.Draw(s).rectangle([4, 4, 11, 11], fill=(200, 30, 30, 255))
    return {"sprite": data_url(s), "raw": data_url(Image.new("RGB", (384, 384), (9, 9, 9))), "info": {"seed": seed, "size": [16, 16]}}


# ---------------- the manager with a fake executor ----------------
tmp = tmpdir(); order = []; gate = threading.Event(); gate.set()
def ex(kind, params, inputs, progress):
    order.append((kind, params.get("prompt"))); gate.wait(5)
    if params.get("prompt") == "boom": raise RuntimeError("out of memory: pretend")
    n = params.get("n", 1)
    for i in range(n): progress(i + 1, n)
    return [fake_result(params.get("seed", 0) + i) for i in range(n)]
m = jobs.Manager(tmp, ex)
P = lambda prompt, **k: {**dict(prompt=prompt, checkpoint="x", seed=10, n=2), **k}

m.set_paused(True)
# IDs must remain ordered even across a clock rollback or same-millisecond burst.
clock=jobs.time.time_ns
try:
    jobs.time.time_ns=lambda: 1700000000999999999
    first=m._new_id()
    jobs.time.time_ns=lambda: 1700000000000000000
    second=m._new_id()
    ok(first<second,"monotonic job IDs across clock rollback")
finally:
    jobs.time.time_ns=clock
a = m.add("generate", P("a"), {"steps": "25", "prompt": "a"}); b = m.add("generate", P("b")); c = m.add("generate", P("c"))
ok([j["status"] for j in m.queue()["jobs"]] == ["queued"] * 3 and not order, "paused queue holds jobs without running them")
ok(m.cancel(b["id"])["status"] == "cancelled" and len(m.queue()["jobs"]) == 2, "a waiting job can be cancelled")
m.set_paused(False); ok(m.wait_idle(10), "queue drains")
ok([o[1] for o in order] == ["a", "c"], "jobs run one at a time, oldest first, cancelled ones skipped")
h = m.history()
ok(h["total"] == 3 and [j["status"] for j in h["jobs"]] == ["done", "cancelled", "done"], "history lists finished jobs newest first")
ja = m.get(a["id"]); ok(len(ja["results"]) == 2 and from_url(ja["results"][0]["sprite"]).size == (16, 16) and ja["results"][0]["raw"] and ja["ui"]["steps"] == "25",
                         "a job keeps its results, raw images and the UI snapshot")
ok(ja["results"][1]["info"]["seed"] == 11 and h["jobs"][2]["thumb"].startswith("data:image/png") and h["jobs"][2]["seeds"] == [10, 11], "seeds and thumbnails in the summary")

# error, and the next job still runs
d = m.add("generate", P("boom")); e = m.add("generate", P("after")); m.wait_idle(10)
ok(m.get(d["id"])["status"] == "error" and "out of memory" in m.get(d["id"])["error"] and m.get(e["id"])["status"] == "done", "a failed job records its error and does not stop the queue")

# Corrupt or missing input must fail one job, not terminate the worker.
m.set_paused(True)
broken=m.add("reference",P("corrupt"),images={"ref":fake_result(1)["sprite"]})
missing=m.add("reference",P("missing"),images={"ref":fake_result(1)["sprite"]})
(m.dir/broken["id"]/"in_ref.png").write_bytes(b"broken image")
(m.dir/missing["id"]/"in_ref.png").unlink()
next_job=m.add("generate",P("after bad input"))
m.set_paused(False)
ok(m.wait_idle(10),"queue drains after corrupt or missing reference")
ok(m.get(broken["id"])["status"]=="error" and m.get(missing["id"])["status"]=="error","bad inputs recorded as errors")
ok(m.get(next_job["id"])["status"]=="done" and m.thread.is_alive(),"worker survives input decode failures")

# progress is visible while running
gate.clear(); f = m.add("generate", P("slow", n=3)); time.sleep(0.4)
q = m.queue(); ok(q["running"] == f["id"] and q["jobs"][0]["status"] == "running", "queue shows the running job")
cr = m.cancel(f["id"]); gate.set(); m.wait_idle(10)
ok(m.get(f["id"])["status"] == "cancelled" and m.get(f["id"])["results"] == [], "cancelling a running job discards its results")
try: m.delete(f["id"]); ok(True, "a cancelled job can be deleted once it has ended")
except jobs.JobError: ok(False, "delete finished job")

# favourites, notes, search, re-run, fork
m.update(a["id"], fav=True, note="best knight"); ok(m.history(fav_only=True)["total"] == 1 and m.history(text="knight")["total"] == 1 and m.history(text="zzz")["total"] == 0, "favourite + note + search")
r1 = m.rerun(a["id"]); r2 = m.rerun(a["id"], new_seed=True); m.wait_idle(10)
ok(m.get(r1["id"])["params"]["seed"] == 10 and m.get(r2["id"])["params"]["seed"] == -1 and m.get(r1["id"])["source"] == a["id"], "re-run keeps the seed, fork asks for a new one, both remember their source")
ok(m.clear_history(keep_favs=True) >= 5 and m.history()["total"] == 1 and m.get(a["id"])["fav"], "clearing history keeps favourites")
m.delete(a["id"]); ok(m.history()["total"] == 0, "delete a job")

# validation
for bad, msg in ((("nope", {}), "unknown kind"), (("reference", {"checkpoint": "x"}), "reference without image"), (("generate", "text"), "params not an object")):
    try: m.add(*bad); ok(False, msg)
    except jobs.JobError: ok(True, msg + " -> JobError")
try: m.get("../../etc"); ok(False, "id traversal")
except jobs.JobError: ok(True, "job ids cannot escape the history folder")

# reference jobs keep their input images
im = Image.new("RGBA", (8, 8), (50, 60, 70, 255)); rj = m.add("reference", dict(checkpoint="x", seed=1), images={"ref": data_url(im), "pose": data_url(im)}); m.wait_idle(10)
g = m.get(rj["id"]); ok(set(g["images"]) == {"ref", "pose"} and from_url(g["images"]["ref"]).size == (8, 8), "reference jobs store their reference and pose images")

# restart: active jobs come back as interrupted; history persists
m.set_paused(True); gate.set(); w = m.add("generate", P("w")); m.shutdown(); time.sleep(1.2)
m2 = jobs.Manager(tmp, ex, start_worker=False)
ok(m2.get(w["id"])["status"] == "interrupted" and m2.history()["total"] >= 2, "after a restart waiting jobs are 'interrupted' and history is still there")
m2.shutdown()

# pruning keeps favourites and the newest jobs
tmp2 = tmpdir(); jobs.MAX_KEPT = 4; mp = jobs.Manager(tmp2, ex)
mp.set_paused(True); ids = [mp.add("generate", P(f"p{i}", n=1))["id"] for i in range(8)]; mp.update(ids[0], fav=True); mp.set_paused(False); mp.wait_idle(15); mp.prune()
left = {j["id"] for j in mp.history(limit=100)["jobs"]}
ok(len(left) == 5 and ids[0] in left and ids[-1] in left and ids[1] not in left, "history is capped (favourites exempt, oldest dropped)"); mp.shutdown(); jobs.MAX_KEPT = 300

# ---------------- endpoints with a fake SDXL ----------------
tmp3 = tmpdir(); M.ROOT = tmp3; M.CFG_PATH = tmp3 / "config.json"
md = tmp3 / "models"; (md / "checkpoints").mkdir(parents=True); (md / "loras").mkdir(); mock_sdxl_checkpoint(md / "checkpoints" / "sd_xl_base_1.0.safetensors")
M.CFG_PATH.write_text(json.dumps({"models_dir": str(md)}))
gcalls = []; progress_seen = []; sampler_seen = []
def fake_generate(*a, **k):
    sampler_seen.append(getattr(M.gen._job_context,'sampler',None)); gcalls.append(a); img = Image.new("RGB", (1024, 1024), (255, 255, 255)); ImageDraw.Draw(img).ellipse([300, 150, 700, 800], fill=(40, 90, 200)); n = a[13]
    out = []
    for i in range(n):
        out.append((img, a[8] + i))
        if getattr(M.gen._job_context,'progress',None): M.gen._progress(i + 1,n); progress_seen.append(i + 1)
    return out
M.gen.generate = fake_generate
body = dict(kind="generate", params=dict(prompt="knight", checkpoint="sd_xl_base_1.0.safetensors", seed=5, n=2, size=32, mode="fixed", colors=8, sampler="dpmpp_2m_karras"), ui={"prompt": "knight"})
r = M.queue_add(body); M._jobmgr().wait_idle(15)
jb = M.job_get(r["id"]); ok(jb["status"] == "done" and len(jb["results"]) == 2 and from_url(jb["results"][0]["sprite"]).size[0] <= 32 and jb["results"][1]["info"]["seed"] == 6, "queued generate job runs the real handler and stores pixelised results")
ok(gcalls and gcalls[0][8] == 5 and sampler_seen[0] == 'dpmpp_2m_karras' and progress_seen == [1, 2] and getattr(M.gen._job_context,"progress",None) is None, "seed + sampler reach the pipeline, per-image progress is reported, hook is cleared")
ok(M.history_list()["total"] == 1 and M.queue_state()["jobs"] == [], "history endpoint lists it; queue is empty")
try: M.queue_add(dict(kind="generate", params=dict(prompt="x"))); ok(False, "no checkpoint")
except HTTPException as e: ok(e.status_code == 400, "queueing without a checkpoint -> 400")
try: M.job_get("20000101_000000_00000"); ok(False, "missing")
except HTTPException as e: ok(e.status_code == 400, "unknown job -> 400")
bad = M.queue_add(dict(kind="generate", params=dict(prompt="x", checkpoint="missing.safetensors"))); M._jobmgr().wait_idle(15)
ok(M.job_get(bad["id"])["status"] == "error" and "checkpoint not found" in M.job_get(bad["id"])["error"], "a bad checkpoint becomes a readable job error")

# reference job through the queue (skeleton mode)
ref = Image.new("RGBA", (32, 48), (0, 0, 0, 0)); ImageDraw.Draw(ref).rectangle([8, 8, 24, 40], fill=(180, 40, 40, 255)); pose = Image.new("RGB", (64, 64), (0, 0, 0))
rb = dict(kind="reference", params=dict(checkpoint="sd_xl_base_1.0.safetensors", character="hero", pose="walking", seed=3, n=1, canvas=64, colors=8), images={"ref": data_url(ref), "pose": data_url(pose)})
rr = M.queue_add(rb); M._jobmgr().wait_idle(15); jr = M.job_get(rr["id"])
ok(jr["status"] == "done" and jr["results"][0]["info"].get("seed") == 3 and gcalls[-1][14] is not None, "reference job passes the stored pose image as the ControlNet input")
c = M._coerce_ref(dict(ip_scale="0.55", n="2", lock_palette="false", crisp=True, seed="7", canvas="96.0"))
ok(c["ip_scale"] == .55 and c["n"] == 2 and c["lock_palette"] is False and c["crisp"] is True and c["seed"] == 7 and c["canvas"] == 96 and c["sampler"] == "euler_a", "reference fields sent as text are coerced to the right types")
try: M._coerce_ref(dict(steps="many")); ok(False, "bad value")
except HTTPException as e: ok(e.status_code == 400, "a non-numeric reference field -> 400")
ok(M.job_rerun(rr["id"], dict(new_seed=True))["source"] == rr["id"], "rerun endpoint")
M._jobmgr().wait_idle(15)
M.job_meta(r["id"], dict(fav=True, note="keeper")); ok(M.history_list(fav=True)["total"] == 1, "meta endpoint (favourite)")
ok(M.queue_pause(dict(paused=True))["paused"] and not M.queue_pause(dict(paused=False))["paused"], "pause / resume endpoint")
M.job_delete(bad["id"]); ok(M.history_list()["total"] >= 2 and M.history_clear(dict(keep_favs=True))["deleted"] >= 1, "delete + clear history")
M._jobmgr().shutdown()

# the direct endpoints behave exactly as before
M._JOBS = None
d = M.generate_ep(M.GenParams(prompt="k", checkpoint="sd_xl_base_1.0.safetensors", n=1, size=32, colors=8)); ok(len(d["results"]) == 1 and "sprite" in d["results"][0], "/api/generate still works directly")
done("test_queue")
