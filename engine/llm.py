"""Local assistant: loads a GGUF by running llama.cpp's llama-server (found in e.g. C:/AI) on demand,
streams chat replies, and unloads the model when idle. CPU by default so it never competes with SDXL for VRAM."""
import json, os, subprocess, threading, time, urllib.error, urllib.request
from pathlib import Path

from . import diag

SERVER_NAMES = {"llama-server.exe", "llama-server"}
SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "site-packages", "__pycache__", "$recycle.bin", "windows"}

SYSTEM = """You are the SpriteForge Assistant inside a local pixel-art sprite tool (SDXL with a pixel-art LoRA, a reference/pose generator, and a rig-based animator). Help the user write prompts, choose settings and plan animations. Be brief and practical.

To put something into the app, use a tag the user can apply with one click: <set field="NAME">VALUE</set>
Fields:
- prompt: what to draw (subject, outfit, colours, pose). The app already adds "pixel art", "single character", "full body" and a plain background, so do not repeat those.
- negative: extra things to avoid.
- character: short identity description (used with the reference sprite and AI cleanup).
- pose: pose / action text for the reference tab.
- anim: one of idle, walk, run, climb, cheer, attack, cast, block, jump, hurt, death.
- template: what the sprite is, for the Template tab (e.g. "knight in blue plate armor with a red cape").
- portrait: prompt for the Portrait tab (face, hair, eye colour, clothing at the collar).
- expression: one extra custom facial expression for the Portrait tab (e.g. "winking, tongue out").
- ip_strength: 0 to 1 (reference strength; higher keeps the look closer but fights the pose).
- skeleton_strength: 0 to 1.5 (how strictly the skeleton pose is followed).
- cleanup_strength: 0.1 to 0.9 (AI joint cleanup; higher repaints more).
Rules: use at most 4 tags per reply, only when the user asks for a prompt or setting or you are confident it helps. Prompts are short comma-separated phrases. Never say you generated or exported anything: the user presses the buttons. If a result looks wrong, suggest one concrete setting change.

Current app state:
"""


class LlmError(RuntimeError):
    pass


def _norm(p):
    return str(p or "").strip().strip('"').replace("\\", "/")


def _walk(root, depth=4, limit=30000):
    root = Path(root)
    if not root.exists():
        return
    base, seen = len(root.parts), 0
    for dp, dns, fns in os.walk(root):
        seen += len(fns) + len(dns)
        if seen > limit:
            return
        if len(Path(dp).parts) - base >= depth:
            dns[:] = []
        dns[:] = [d for d in dns if d.lower() not in SKIP_DIRS]
        for f in fns:
            yield Path(dp) / f


def find_server(search_dir):
    for p in _walk(search_dir):
        if p.name.lower() in SERVER_NAMES:
            return str(p).replace("\\", "/")
    return ""


def find_models(search_dir):
    out = []
    for p in _walk(search_dir):
        if p.suffix.lower() == ".gguf" and "mmproj" not in p.name.lower():
            try:
                mb = p.stat().st_size // (1024 * 1024)
            except OSError:
                continue
            if mb >= 50:
                out.append({"path": str(p).replace("\\", "/"), "name": p.name, "mb": mb})
    return sorted(out, key=lambda m: (m["mb"], m["name"]))


class Manager:
    load_timeout = 300

    def __init__(self, root, get_cfg, set_cfg):
        self.root, self.get_cfg, self.set_cfg = Path(root), get_cfg, set_cfg
        self.proc, self._ready, self._busy = None, False, 0
        self.last_used = time.time()
        self._lock = threading.Lock()
        self._scan = (0, "", [])
        threading.Thread(target=self._idle_loop, daemon=True).start()

    # ---- settings ----
    def settings(self):
        c = self.get_cfg()
        return {"server": _norm(c.get("llm_server")), "model": _norm(c.get("llm_model")),
                "gpu_layers": int(c.get("llm_gpu_layers", 0)), "ctx": int(c.get("llm_ctx", 4096)),
                "idle_min": int(c.get("llm_idle_min", 10)), "search_dir": _norm(c.get("llm_search_dir")) or "C:/AI",
                "port": int(c.get("llm_port", 8766))}

    def update(self, **kw):
        keymap = {"server": "llm_server", "model": "llm_model", "gpu_layers": "llm_gpu_layers", "ctx": "llm_ctx",
                  "idle_min": "llm_idle_min", "search_dir": "llm_search_dir"}
        old = self.settings()
        if kw.get("server") and Path(_norm(kw["server"])).name.lower() not in SERVER_NAMES:
            raise LlmError("the server file must be named llama-server (llama-server.exe on Windows)")
        if kw.get("model") and not _norm(kw["model"]).lower().endswith(".gguf"):
            raise LlmError("the model must be a .gguf file")
        upd = {}
        for k, v in kw.items():
            if k in keymap:
                upd[keymap[k]] = _norm(v) if isinstance(v, str) else v
        if "llm_gpu_layers" in upd:
            upd["llm_gpu_layers"] = max(0, min(int(upd["llm_gpu_layers"]), 200))
        if "llm_ctx" in upd:
            upd["llm_ctx"] = max(512, min(int(upd["llm_ctx"]), 32768))
        if "llm_idle_min" in upd:
            upd["llm_idle_min"] = max(0, min(int(upd["llm_idle_min"]), 240))
        self.set_cfg(upd)
        new = self.settings()
        if any(old[k] != new[k] for k in ("server", "model", "gpu_layers", "ctx")):
            self.stop()  # a running server would still be using the old settings
        if "search_dir" in kw or "server" in kw:
            self._scan = (0, "", [])

    def state(self, rescan=False):
        s = self.settings()
        if rescan or time.time() - self._scan[0] > 120:
            self._scan = (time.time(), find_server(s["search_dir"]), find_models(s["search_dir"]))
        _, found, models = self._scan
        server = s["server"] if s["server"] and Path(s["server"]).exists() else found
        if s["model"] and Path(s["model"]).exists() and all(m["path"] != s["model"] for m in models):
            models = models + [{"path": s["model"], "name": Path(s["model"]).name, "mb": Path(s["model"]).stat().st_size // 1048576}]
        return {"settings": s, "server": server, "models": models, "running": self._alive(), "ready": self._alive() and self._ready}

    # ---- process ----
    def _alive(self):
        return self.proc is not None and self.proc.poll() is None

    def _spawn(self):
        st = self.state()
        s = st["settings"]
        if not st["server"]:
            raise LlmError(f"llama-server not found. Set its path in the assistant settings (it comes with llama.cpp, e.g. in {s['search_dir']}).")
        if not s["model"] or not Path(s["model"]).exists():
            raise LlmError("Choose a .gguf model in the assistant settings first.")
        if Path(st["server"]).name.lower() not in SERVER_NAMES or not s["model"].lower().endswith(".gguf"):
            raise LlmError("refusing to start: server must be llama-server and the model a .gguf file")
        cmd = [st["server"], "-m", s["model"], "-c", str(s["ctx"]), "-ngl", str(s["gpu_layers"]),
               "--host", "127.0.0.1", "--port", str(s["port"])]
        log = open(self.root / "llm.log", "w")
        kw = {}
        if os.name == "nt":
            kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        try:
            self.proc = subprocess.Popen(cmd, stdout=log, stderr=log, cwd=str(Path(st["server"]).parent), **kw)
        except OSError as e:
            raise LlmError(f"could not start llama-server: {e}")
        self._ready = False

    def _tail_log(self, n=500):
        try:
            return (self.root / "llm.log").read_text(errors="ignore")[-n:].strip() or "(no output)"
        except OSError:
            return "(no log)"

    def _health(self):
        port = self.settings()["port"]
        for path in ("/health", "/v1/models"):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=1.5) as r:
                    if r.status == 200:
                        return True
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    continue
                return False  # 503 = still loading
            except Exception:
                return False
        return False

    def ensure_started(self):
        """Generator of status strings while the model loads; raises LlmError on failure."""
        with self._lock:
            if self._alive() and self._ready:
                return
            if not self._alive():
                self._spawn()
        t0 = time.time()
        while True:
            if not self._alive():
                raise LlmError("the model server stopped while loading. Log: " + self._tail_log())
            if self._health():
                self._ready = True
                return
            if time.time() - t0 > self.load_timeout:
                self.stop()
                raise LlmError("the model took too long to load (try a smaller model or fewer context tokens)")
            yield f"Loading model… {int(time.time() - t0)} s"
            time.sleep(1)

    def start(self):
        for _ in self.ensure_started():
            pass

    def stop(self):
        p, self.proc, self._ready = self.proc, None, False
        if p is not None and p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=4)
            except subprocess.TimeoutExpired:
                p.kill()

    def _idle_loop(self):
        while True:
            time.sleep(15)
            idle = self.settings()["idle_min"]
            if self._alive() and self._busy == 0 and idle > 0 and time.time() - self.last_used > idle * 60:
                self.stop()

    def selftest(self):
        """Diagnostics: load the model, ask for one word, report load time and speed."""
        t0 = time.time()
        self.start()
        load_s, text, toks, t1 = time.time() - t0, "", 0, time.time()
        for e in self.chat_events([{"role": "user", "content": "Reply with exactly: OK"}], "diagnostics test"):
            o = json.loads(e[5:])
            if "error" in o:
                raise LlmError(o["error"])
            if "token" in o:
                text += o["token"]
                toks += 1
        return {"load_s": round(load_s, 1), "reply": text.strip()[:80], "tokens": toks,
                "tok_per_s": round(toks / max(time.time() - t1, 1e-3), 1)}

    # ---- chat ----
    def chat_events(self, messages, context=""):
        ev = lambda o: "data: " + json.dumps(o) + "\n\n"
        msgs = [{"role": "system", "content": SYSTEM + str(context)[:1500]}]
        for m in list(messages)[-20:]:
            if isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str):
                msgs.append({"role": m["role"], "content": m["content"][:4000]})
        if len(msgs) < 2 or msgs[-1]["role"] != "user":
            yield ev({"error": "nothing to answer"})
            return
        try:
            for status in self.ensure_started():
                yield ev({"status": status})
        except LlmError as e:
            yield ev({"error": str(e)})
            return
        self._busy += 1
        try:
            yield ev({"status": "Model ready"})
            body = json.dumps({"model": "local", "messages": msgs, "stream": True, "temperature": 0.6, "max_tokens": 500}).encode()
            req = urllib.request.Request(f"http://127.0.0.1:{self.settings()['port']}/v1/chat/completions", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                for raw in r:
                    line = raw.decode("utf-8", "ignore").strip()
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        delta = json.loads(payload)["choices"][0].get("delta", {}).get("content")
                    except (ValueError, KeyError, IndexError):
                        continue
                    if delta:
                        yield ev({"token": delta})
            yield ev({"done": True})
        except Exception as e:
            diag.record_error("llm/chat", "SSE", f"{type(e).__name__}: {e}")
            yield ev({"error": f"{type(e).__name__}: {e}"})
        finally:
            self._busy -= 1
            self.last_used = time.time()
