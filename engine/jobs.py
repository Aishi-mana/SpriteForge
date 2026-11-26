"""Generation queue + history.

One background worker runs jobs one at a time (the GPU can only do one SDXL job anyway). Every job is stored on disk under
<app>/history/<id>/ : job.json (kind, params, UI snapshot, status, timings, result info) + PNG files, so the history survives
restarts and each result can be re-run, forked (new seed) or have its settings loaded back into the UI.

  history/<id>/job.json      params, ui, status, created/started/finished, results[{info, sprite, raw}], error, fav, note
  history/<id>/in_ref.png    reference sprite (reference jobs)        in_pose.png  skeleton render (ControlNet jobs)
  history/<id>/r<i>.png      final sprite i                            raw<i>.png   raw SDXL output (384 px)

The worker does not know about SDXL: `executor(kind, params, inputs, progress)` is injected (main.py), which keeps this module
testable with a fake executor. Jobs that were queued/running when the app closed come back as "interrupted" (re-run them).
"""
import base64, copy, io, json, re, shutil, threading, time
from pathlib import Path
from PIL import Image

KINDS = ("generate", "reference")
ACTIVE = ("queued", "running")
MAX_KEPT = 300          # history cap; favourites are never pruned
MAX_QUEUED = 50


class JobError(ValueError):
    pass


def _png_bytes(data_url, max_bytes=12_000_000):
    """data URL -> sanitized PNG bytes (re-encoded through PIL so only real images are written)."""
    if not isinstance(data_url, str) or "," not in data_url:
        raise JobError("bad image data")
    raw = base64.b64decode(data_url.split(",", 1)[1])
    if len(raw) > max_bytes:
        raise JobError("image too large")
    buf = io.BytesIO()
    Image.open(io.BytesIO(raw)).convert("RGBA").save(buf, "PNG")
    return buf.getvalue()


def _enc(path):
    return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()


def _pil_to_png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def data_url_to_pil(u):
    return Image.open(io.BytesIO(base64.b64decode(u.split(",", 1)[1])))


class Manager:
    def __init__(self, root, executor, start_worker=True):
        self.dir = Path(root) / "history"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.executor = executor
        self.cv = threading.Condition()
        self.paused = False
        self.running = None          # job id
        self.progress = {}           # id -> [done, total]
        self._seq = 0
        self._stop = False
        self._cancel_running = set()
        self._cache = {}             # id -> job dict (in-memory index of history/*/job.json; the worker polls often)
        for d in self.dir.iterdir():
            try:
                j = json.loads((d / "job.json").read_text(encoding="utf-8"))
                self._cache[j["id"]] = j
            except Exception:
                pass
        self._recover()
        self.thread = None
        if start_worker:
            self.thread = threading.Thread(target=self._loop, name="spriteforge-queue", daemon=True)
            self.thread.start()

    # ---------- storage ----------
    def _jdir(self, jid):
        jid = re.sub(r"[^0-9A-Za-z_]", "", str(jid))
        d = (self.dir / jid).resolve()
        if self.dir.resolve() not in d.parents or not jid:
            raise JobError("invalid job id")
        return d

    def _read(self, jid):
        d = self._jdir(jid)
        j = self._cache.get(d.name)
        if j is None:
            raise JobError(f"job not found: {jid}")
        return copy.deepcopy(j)

    def _remove(self, jid):
        self._cache.pop(self._jdir(jid).name, None)
        shutil.rmtree(self._jdir(jid), ignore_errors=True)

    def _write(self, job):
        d = self._jdir(job["id"])
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / "job.json.tmp"
        tmp.write_text(json.dumps(job, indent=1), encoding="utf-8")
        tmp.replace(d / "job.json")  # atomic
        self._cache[job["id"]] = copy.deepcopy(job)

    def _recover(self):
        for j in list(self._cache.values()):
            if j.get("status") in ACTIVE:
                j = copy.deepcopy(j)
                j["status"] = "interrupted"
                j["error"] = "the app was closed before this job finished"
                self._write(j)

    def _new_id(self):
        with self.cv:
            self._seq += 1
            return time.strftime("%Y%m%d_%H%M%S") + f"_{int(time.time() * 1000) % 1000:03d}{self._seq % 100:02d}"

    # ---------- public API ----------
    def add(self, kind, params, ui=None, images=None, source=None):
        """Queue a job. `images` = {"ref": data URL, "pose": data URL} for reference jobs. Returns the job summary."""
        if kind not in KINDS:
            raise JobError(f"unknown job kind: {kind}")
        if not isinstance(params, dict):
            raise JobError("params must be an object")
        images = images or {}
        if kind == "reference" and not images.get("ref"):
            raise JobError("a reference job needs a reference image")
        if sum(1 for j in self._all() if j["status"] == "queued") >= MAX_QUEUED:
            raise JobError(f"the queue is full ({MAX_QUEUED} waiting jobs): wait or cancel some")
        staged = {k: _png_bytes(v) for k, v in images.items() if v and k in ("ref", "pose")}
        jid = self._new_id()
        job = {"id": jid, "kind": kind, "status": "queued", "params": params, "ui": ui or {}, "created": time.time(),
               "started": None, "finished": None, "results": [], "error": None, "fav": False, "note": "",
               "inputs": sorted(staged), "source": source}
        d = self._jdir(jid)
        d.mkdir(parents=True, exist_ok=True)
        for k, b in staged.items():
            (d / f"in_{k}.png").write_bytes(b)
        self._write(job)
        with self.cv:
            self.cv.notify_all()
        return self._summary(job)

    def add_batch(self, entries, batch_id, batch_name):
        """Publish prevalidated generation jobs together while the worker is locked."""
        if not isinstance(entries,list) or not 1<=len(entries)<=24:
            raise JobError("Choose 1–24 characters")
        with self.cv:
            if sum(j["status"]=="queued" for j in self._all())+len(entries)>MAX_QUEUED:
                raise JobError("Not enough queue capacity for this batch")
            added=[]
            try:
                for e in entries:
                    ui=copy.deepcopy(e.get("ui") or {})
                    ui["__batch"]={"id":batch_id,"name":batch_name,"index":e["index"],"character":e["name"]}
                    added.append(self.add("generate",e["params"],ui))
            except Exception:
                for item in added:self._remove(item["id"])
                raise
            return added

    def batches(self):
        """Group retained jobs by batch and row, keeping latest attempt for each row."""
        with self.cv:
            groups={}
            for j in sorted(self._all(),key=lambda j:(j["created"],j["id"])):
                b=(j.get("ui") or {}).get("__batch")
                if not isinstance(b,dict) or not isinstance(b.get("id"),str) or not isinstance(b.get("index"),int):continue
                g=groups.setdefault(b["id"],{"id":b["id"],"name":b.get("name","batch"),"created":j["created"],"rows":{}})
                g["rows"][b["index"]]={**self._summary(j), "index":b["index"],"character":b.get("character","character")}
            return sorted([{**g,"rows":sorted(g["rows"].values(),key=lambda r:r["index"])} for g in groups.values()],
                          key=lambda g:g["created"],reverse=True)

    def cancel(self, jid):
        """Cancel a waiting job. A running job cannot be interrupted mid-image: its results are discarded when it ends."""
        with self.cv:
            j = self._read(jid)
            if j["status"] == "queued":
                j["status"], j["finished"] = "cancelled", time.time()
                self._write(j)
                return self._summary(j)
            if j["status"] == "running":
                self._cancel_running.add(j["id"])
                return {**self._summary(j), "note": "will be discarded when the current image finishes"}
            raise JobError(f"job is already {j['status']}")

    def cancel_all(self):
        n = 0
        with self.cv:
            for j in self._all():
                if j["status"] == "queued":
                    j = copy.deepcopy(j)
                    j["status"], j["finished"] = "cancelled", time.time()
                    self._write(j)
                    n += 1
        return n

    def set_paused(self, paused):
        with self.cv:
            self.paused = bool(paused)
            self.cv.notify_all()
        return self.paused

    def _all(self):
        return list(self._cache.values())  # read-only use: callers copy before changing

    def _summary(self, j, thumb=False):
        s = {k: j.get(k) for k in ("id", "kind", "status", "created", "started", "finished", "error", "fav", "note", "source")}
        p = j.get("params") or {}
        s["prompt"] = (p.get("prompt") or p.get("character") or p.get("pose") or "")[:200]
        s["sub"] = p.get("kind") or ""  # tile / prop / icon / ui for generate jobs
        s["n_results"] = len(j.get("results") or [])
        s["seeds"] = [(r.get("info") or {}).get("seed") for r in (j.get("results") or [])]
        s["progress"] = self.progress.get(j["id"])
        if thumb and j.get("results"):
            f = self._jdir(j["id"]) / "r0.png"
            s["thumb"] = _enc(f) if f.exists() else None
        return s

    def queue(self):
        """Waiting + running jobs (oldest first) and the last few finished ones."""
        jobs = sorted(self._all(), key=lambda j: j["id"])
        act = [self._summary(j) for j in jobs if j["status"] in ACTIVE]
        act.sort(key=lambda s: (s["status"] != "running", s["id"]))
        return {"paused": self.paused, "running": self.running, "jobs": act}

    def history(self, limit=40, offset=0, fav_only=False, text="", kind=""):
        jobs = [j for j in self._all() if j["status"] not in ACTIVE]
        if fav_only:
            jobs = [j for j in jobs if j.get("fav")]
        if kind:
            jobs = [j for j in jobs if j["kind"] == kind]
        t = (text or "").strip().lower()
        if t:
            jobs = [j for j in jobs if t in json.dumps(j.get("params", {})).lower() or t in (j.get("note") or "").lower()]
        jobs.sort(key=lambda j: j["id"], reverse=True)
        total = len(jobs)
        limit = max(1, min(int(limit), 100))
        return {"total": total, "jobs": [self._summary(j, thumb=True) for j in jobs[max(0, int(offset)):max(0, int(offset)) + limit]]}

    def get(self, jid):
        """Full job: params, ui snapshot, input images and every result as data URLs."""
        j = self._read(jid)
        d = self._jdir(jid)
        j["images"] = {k: _enc(d / f"in_{k}.png") for k in j.get("inputs", []) if (d / f"in_{k}.png").exists()}
        for i, r in enumerate(j.get("results", [])):
            r["sprite"] = _enc(d / f"r{i}.png") if (d / f"r{i}.png").exists() else None
            r["raw"] = _enc(d / f"raw{i}.png") if (d / f"raw{i}.png").exists() else None
        j["progress"] = self.progress.get(jid)
        return j

    def update(self, jid, fav=None, note=None):
        with self.cv:
            j = self._read(jid)
            if fav is not None:
                j["fav"] = bool(fav)
            if note is not None:
                j["note"] = str(note)[:300]
            self._write(j)
        return self._summary(j)

    def delete(self, jid):
        with self.cv:
            j = self._read(jid)
            if j["status"] == "running":
                raise JobError("this job is running: cancel it first")
            self._remove(jid)

    def clear_history(self, keep_favs=True):
        n = 0
        with self.cv:
            for j in self._all():
                if j["status"] in ACTIVE or (keep_favs and j.get("fav")):
                    continue
                self._remove(j["id"])
                n += 1
        return n

    def rerun(self, jid, new_seed=False):
        """Queue a copy of a finished job. Same seed -> same pictures; new_seed=True -> a variation (a 'fork')."""
        old = self.get(jid)
        params = json.loads(json.dumps(old["params"]))
        if new_seed:
            params["seed"] = -1
        return self.add(old["kind"], params, old.get("ui"), old.get("images"), source=old["id"])

    def prune(self):
        jobs = sorted((j for j in self._all() if j["status"] not in ACTIVE and not j.get("fav")), key=lambda j: j["id"])
        excess = len(jobs) - MAX_KEPT
        for j in jobs[:max(0, excess)]:
            self._remove(j["id"])

    # ---------- worker ----------
    def _next(self):
        queued = sorted((j for j in self._all() if j["status"] == "queued"), key=lambda j: j["id"])
        return queued[0] if queued else None

    def _loop(self):
        while True:
            with self.cv:
                while not self._stop:
                    job = None if self.paused else self._next()
                    if job:
                        break
                    self.cv.wait(timeout=1.0)
                if self._stop:
                    return
                job = copy.deepcopy(job)
                job["status"], job["started"] = "running", time.time()
                self.running = job["id"]
                self._write(job)
            self._run_one(job)
            with self.cv:
                self.running = None
                self.cv.notify_all()

    def _run_one(self, job):
        jid, d = job["id"], self._jdir(job["id"])
        inputs = {k: data_url_to_pil(_enc(d / f"in_{k}.png")).convert("RGB" if k == "pose" else "RGBA") for k in job.get("inputs", [])
                  if (d / f"in_{k}.png").exists()}
        self.progress[jid] = [0, int(job["params"].get("n") or 1)]
        try:
            def progress(done,total):self.progress[jid]=[done,total]
            progress.cancelled=lambda:self._stop or jid in self._cancel_running
            results = self.executor(job["kind"], job["params"], inputs, progress)
            if jid in self._cancel_running:
                job["status"], job["error"] = "cancelled", "cancelled while running (results discarded)"
            else:
                job["results"] = []
                for i, r in enumerate(results):
                    (d / f"r{i}.png").write_bytes(_png_bytes(r["sprite"]))
                    if r.get("raw"):
                        (d / f"raw{i}.png").write_bytes(_png_bytes(r["raw"]))
                    job["results"].append({"info": r.get("info") or {}})
                job["status"] = "done"
        except Exception as e:  # keep the readable message (HTTPException has .detail)
            job["status"] = "cancelled" if jid in self._cancel_running else "error"
            job["error"] = "cancelled while running (results discarded)" if job["status"]=="cancelled" else str(getattr(e, "detail", None) or f"{type(e).__name__}: {e}")
        job["finished"] = time.time()
        self._cancel_running.discard(jid)
        self.progress.pop(jid, None)
        self._write(job)
        try:
            self.prune()
        except Exception:
            pass

    def wait_idle(self, timeout=30):
        """Block until nothing is queued or running (used by tests and by 'run and follow')."""
        end = time.time() + timeout
        while time.time() < end:
            if self.running is None and not any(j["status"] in ACTIVE for j in self._all()):
                return True
            if self.paused:
                return False
            time.sleep(0.05)
        return False

    def shutdown(self):
        with self.cv:
            self._stop = True
            self.cv.notify_all()
