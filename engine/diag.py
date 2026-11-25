"""Diagnostics: environment, GPU, model files, downloads, assistant, built-in self-tests and recent errors,
as a structured list plus a plain-text report that can be pasted into a bug report."""
import collections, ctypes, json, os, platform, shutil, socket, subprocess, sys, tempfile, time, traceback
from importlib import metadata
from pathlib import Path

ERRORS = collections.deque(maxlen=30)
_HDR = {}


def record_error(where, status, detail):
    ERRORS.append({"t": time.strftime("%H:%M:%S"), "where": where, "status": status, "detail": str(detail)[:400]})


def C(section, name, status, detail="", fix=""):
    return {"section": section, "name": name, "status": status, "detail": str(detail), "fix": fix}


# ---------------- safetensors inspection (also used to tag the model dropdowns) ----------------
def _classify(keys, is_lora):
    """Identify the model family from tensor names. Only positively identified incompatible families are 'dit'/'sd15'/'other';
    anything unrecognised is 'unknown' (never blocked). NB: real SDXL/SD1.5 files also contain 'transformer_blocks'."""
    ks = list(keys)
    has = lambda *subs: any(any(s in k for s in subs) for k in ks)
    if is_lora:
        if has("double_blocks", "single_blocks", "double_stream_blocks", "single_stream_blocks"):
            return "other"  # Flux / HiDream LoRA
        if has("lora_unet", "unet.", "input_blocks", "output_blocks", "down_blocks", "up_blocks", "mid_block"):
            return "sdxl" if has("lora_te2", "text_encoder_2", "te2_", "conditioner") else "unknown"  # SDXL or SD1.5 UNet LoRA
        if has("cross_attn", "transformer_blocks", "blocks.", "img_in", "txt_in"):
            return "other"  # Wan / Qwen / other DiT LoRA (no UNet blocks at all)
        return "unknown"
    if any(k.startswith("conditioner.embedder.1") or "label_emb" in k or "add_embedding" in k or k.startswith("text_encoder_2") for k in ks):
        return "sdxl"
    if any("cond_stage_model" in k for k in ks):
        return "sd15"
    if has("double_blocks", "single_blocks", "double_stream_blocks", "single_stream_blocks", "time_text_embed", "txt_in.", "img_in."):
        return "dit"  # Flux / HiDream / Qwen-Image ...
    return "unknown"


def inspect_file(path, is_lora=False):
    """-> {"status": ok|bad, "msg": str, "kind": sdxl|sd15|other|unknown|None}. Reads only the header, cached by mtime."""
    p = Path(path)
    try:
        st = p.stat()
    except OSError as e:
        return {"status": "bad", "msg": str(e), "kind": None}
    key = (str(p), st.st_mtime_ns, st.st_size, is_lora)
    if key in _HDR:
        return _HDR[key]
    try:
        with open(p, "rb") as f:
            n = int.from_bytes(f.read(8), "little")
            if n <= 0 or n > 400_000_000 or 8 + n > st.st_size:
                res = {"status": "bad", "msg": "not a valid .safetensors file (header size is wrong; incomplete download?)", "kind": None}
            else:
                h = json.loads(f.read(n))
                h.pop("__metadata__", None)
                end = max((v["data_offsets"][1] for v in h.values()), default=0)
                if 8 + n + end > st.st_size:
                    res = {"status": "bad", "kind": None,
                           "msg": f"file is truncated: should be {(8 + n + end) / 2**30:.2f} GB, is {st.st_size / 2**30:.2f} GB (re-download it)"}
                else:
                    res = {"status": "ok", "msg": "", "kind": _classify(h.keys(), is_lora)}
    except Exception as e:
        res = {"status": "bad", "msg": f"{type(e).__name__}: {e}", "kind": None}
    _HDR[key] = res
    return res


# ---------------- individual checks ----------------
def _ver(pkg):
    try:
        return metadata.version(pkg)
    except Exception:
        return None


def _ram():
    try:
        if os.name == "nt":
            class M(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong),
                            ("tpf", ctypes.c_ulonglong), ("apf", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong),
                            ("ae", ctypes.c_ulonglong)]
            m = M()
            m.l = ctypes.sizeof(M)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
            return m.tp / 2**30, m.ap / 2**30
        info = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo") if ":" in l}
        return info["MemTotal"] / 2**20, info["MemAvailable"] / 2**20
    except Exception:
        return None


def check_system(root):
    out, S = [], "System"
    phases = sorted(p.stem for p in Path(root).glob("PHASE*.md"))
    out.append(C(S, "Python / OS", "ok", f"Python {platform.python_version()} · {platform.platform()} · app files: {', '.join(phases) or 'unknown'}"))
    need = {"torch": "", "diffusers": "", "transformers": "", "accelerate": "", "safetensors": "", "peft": "",
            "numpy": "", "scipy": "", "pillow": "", "fastapi": "", "uvicorn": "", "pydantic": "", "python-multipart": ""}
    missing, vers = [], []
    for k in need:
        v = _ver(k)
        (vers if v else missing).append(f"{k} {v}" if v else k)
    out.append(C(S, "Python packages", "fail" if missing else "ok", "missing: " + ", ".join(missing) if missing else ", ".join(vers),
                 "Run:  pip install -r requirements.txt  (inside the app's .venv)" if missing else ""))
    ram = _ram()
    if ram:
        out.append(C(S, "System RAM", "warn" if ram[0] < 15 else "ok", f"{ram[1]:.1f} GB free of {ram[0]:.1f} GB",
                     "SDXL with CPU offload wants about 16 GB or more" if ram[0] < 15 else ""))
    for label, path in (("App folder", root),):
        try:
            u = shutil.disk_usage(path)
            out.append(C(S, f"Disk space ({label})", "warn" if u.free < 10 * 2**30 else "ok", f"{u.free / 2**30:.0f} GB free",
                         "Downloads (IP-Adapter, ControlNet) need about 6 GB" if u.free < 10 * 2**30 else ""))
        except OSError:
            pass
    try:  # can we write next to the app?
        t = Path(root) / ".diag_write_test"
        t.write_text("x")
        t.unlink()
        out.append(C(S, "App folder writable", "ok", "projects, exports and logs can be saved"))
    except OSError as e:
        out.append(C(S, "App folder writable", "fail", str(e), "Move the app to a normal folder (not Program Files)"))
    return out


def check_gpu():
    S = "GPU"
    try:
        import torch
    except Exception as e:
        return [C(S, "PyTorch", "fail", f"{type(e).__name__}: {e}", "Run run.bat / spriteforge.bat so the .venv is created, or pip install torch")]
    out = [C(S, "PyTorch", "ok", f"torch {torch.__version__} · built for CUDA {torch.version.cuda}")]
    if torch.version.cuda is None:
        out[0]["status"], out[0]["fix"] = "fail", "This is a CPU-only PyTorch. Install the CUDA build: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128"
        return out
    if not torch.cuda.is_available():
        out.append(C(S, "CUDA device", "fail", "torch.cuda.is_available() is False", "Update the NVIDIA driver; make sure no other process hides the GPU"))
        return out
    cap = torch.cuda.get_device_capability(0)
    name = torch.cuda.get_device_name(0)
    arch, archs = f"sm_{cap[0]}{cap[1]}", torch.cuda.get_arch_list()
    free, total = torch.cuda.mem_get_info()
    out.append(C(S, "GPU", "ok", f"{name} · compute {cap[0]}.{cap[1]} · {total / 2**30:.1f} GB VRAM, {free / 2**30:.1f} GB free"))
    if arch not in archs and not any(a.startswith("compute_") and a[8:] == arch[3:] for a in archs):
        out.append(C(S, "PyTorch supports this GPU", "fail", f"{arch} is not in this build ({' '.join(archs)})",
                     "RTX 50-series needs a CUDA 12.8+ build: pip install --upgrade torch torchvision --index-url https://download.pytorch.org/whl/cu128"))
    else:
        out.append(C(S, "PyTorch supports this GPU", "ok", f"{arch} is included in this build"))
    if free < 6 * 2**30:
        out.append(C(S, "Free VRAM", "warn", f"only {free / 2**30:.1f} GB free", "Close browsers, games and other AI tools: SDXL needs about 6 GB free with CPU offload"))
    try:
        t = torch.ones(1024, 1024, device="cuda", dtype=torch.float16) @ torch.ones(1024, 1024, device="cuda", dtype=torch.float16)
        torch.cuda.synchronize()
        out.append(C(S, "GPU math test", "ok", "fp16 matrix multiply works"))
        del t
    except Exception as e:
        out.append(C(S, "GPU math test", "fail", f"{type(e).__name__}: {e}", "Driver / PyTorch mismatch: reinstall the cu128 build and update the NVIDIA driver"))
    return out


def check_models(models_dir):
    S = "Models"
    out = []
    md = Path(models_dir) if models_dir else None
    if not md or not md.exists():
        return [C(S, "Models folder", "fail", f"not found: {models_dir or '(not set)'}", "Set it in the sidebar (the folder that contains checkpoints/ and loras/)")]
    out.append(C(S, "Models folder", "ok", str(md)))
    from . import model_families as mf
    ck = sorted(p for p in (md / "checkpoints").iterdir() if (p.is_file() and p.suffix==".safetensors") or (p.is_dir() and (p/"model_index.json").is_file())) if (md / "checkpoints").exists() else []
    from . import local_runtime as lr
    qwen=md/"diffusion_models"/lr.QWEN
    if qwen.is_file() and not any(p.name==qwen.name for p in ck):ck.append(qwen)
    lo = sorted((md / "loras").glob("*.safetensors")) if (md / "loras").exists() else []
    sdxl, rows, supported = [], [], []
    for p in ck:
        r=mf.describe(p)
        rows.append(f"{p.name}: {r['label']} — {r['detail']}")
        if r["supported"]: supported.append(p.name)
        if r["family"] in ("sdxl","unknown") and r["supported"]: sdxl.append(p.name)
    out.append(C(S,"Checkpoints","fail" if not supported else ("warn" if len(supported)<len(ck) else "ok"),
                 f"{len(supported)} selectable of {len(ck)}: "+"; ".join(rows[:12]),
                 "SDXL: skeleton/inpaint; local NetaYume/Qwen: image references; other architectures: text-to-image. See Phase 28 setup."))
    base = [n for n in sdxl if n.startswith("sd_xl_base")]
    out.append(C(S, "Recommended base (sd_xl_base_1.0)", "ok" if base else "warn", base[0] if base else "not found",
                 "" if base else "The pixel-art-xl LoRA was trained on SDXL base; other SDXL checkpoints may give different looks"))
    lrows, usable = [], []
    for p in lo:
        kind = mf.identify(p, True)
        lrows.append(f"{p.name}: {kind}")
        if kind in ("sdxl", "unknown"):
            usable.append(p.name)
    pix = [n for n in usable if "pixel" in n.lower()]
    out.append(C(S, "Pixel-art LoRA", "ok" if pix else "warn", pix[0] if pix else f"none found among {len(lo)} LoRAs",
                 "" if pix else "Put pixel-art-xl-v1.1.safetensors in loras/ (nerijs/pixel-art-xl)"))
    out.append(C(S, "LoRA files", "info", f"{len(lo)} found (compatibility depends on selected model): " + "; ".join(lrows[:12])))
    return out


def _hf_cache():
    return Path(os.environ.get("HF_HUB_CACHE") or (Path(os.environ.get("HF_HOME") or Path.home() / ".cache" / "huggingface") / "hub"))


def _size(path):
    return sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file() and not f.is_symlink()) / 2**30


def check_downloads(models_dir):
    S = "Downloads"
    hub = _hf_cache()
    out = []
    off = os.environ.get("HF_HUB_OFFLINE") == "1"
    ipa = list(hub.glob("models--h94--IP-Adapter/snapshots/*/sdxl_models/ip-adapter_sdxl.safetensors"))
    enc = list(hub.glob("models--h94--IP-Adapter/snapshots/*/sdxl_models/image_encoder/*.safetensors"))
    d = hub / "models--h94--IP-Adapter"
    out.append(C(S, "IP-Adapter (Reference pose, portraits from sprite)", "ok" if ipa and enc else "info",
                 f"downloaded ({_size(d):.1f} GB)" if ipa and enc else "not downloaded yet (about 3 GB, fetched on first use)",
                 "Needs internet once" if not (ipa and enc) else ""))
    cn_local = [p.name for p in (Path(models_dir) / "controlnet").glob("*.safetensors")] if models_dir and (Path(models_dir) / "controlnet").exists() else []
    cn_local = [n for n in cn_local if "openpose" in n.lower() and "xl" in n.lower()]
    cn_hf = list(hub.glob("models--xinsir--controlnet-openpose-sdxl-1.0/snapshots/*/*.safetensors"))
    if cn_local:
        out.append(C(S, "OpenPose ControlNet (skeleton mode)", "ok", f"local file: {cn_local[0]}"))
    else:
        out.append(C(S, "OpenPose ControlNet (skeleton mode)", "ok" if cn_hf else "info",
                     f"downloaded ({_size(hub / 'models--xinsir--controlnet-openpose-sdxl-1.0'):.1f} GB)" if cn_hf else "not downloaded yet (about 2.5 GB, fetched on first skeleton use)"))
    missing = not (ipa and enc) or not (cn_local or cn_hf)
    try:
        old = socket.getdefaulttimeout()
        socket.setdefaulttimeout(3)
        socket.getaddrinfo("huggingface.co", 443)
        socket.setdefaulttimeout(old)
        net = True
    except Exception:
        socket.setdefaulttimeout(None)
        net = False
    out.append(C(S, "Internet (huggingface.co)", ("ok" if net else ("warn" if missing else "info")), "reachable" if net else "not reachable",
                 "Needed once to download the files above" if (missing and not net) else ""))
    if off:
        out.append(C(S, "Offline mode", "warn" if missing else "info", "HF_HUB_OFFLINE=1 is set", "Unset it for the first download"))
    return out


def check_assistant(llm_state, llm_log):
    S = "Assistant"
    st, s = llm_state, llm_state["settings"]
    out = []
    srv = st.get("server")
    if not srv:
        out.append(C(S, "llama-server", "info", f"not found under {s['search_dir']}", "Optional. Download llama.cpp (CPU build) into that folder, then press Scan in the assistant settings"))
    else:
        ver = ""
        try:
            kw = {"creationflags": 0x08000000} if os.name == "nt" else {}
            r = subprocess.run([srv, "--version"], capture_output=True, text=True, timeout=10, cwd=str(Path(srv).parent), **kw)
            txt = (r.stdout + "\n" + r.stderr).strip().splitlines()
            ver = next((l for l in txt if "version" in l.lower()), txt[0] if txt else "")[:160]
            cuda = " · CUDA build" if any("cuda" in l.lower() for l in txt) else (" · Vulkan build" if any("vulkan" in l.lower() for l in txt) else "")
            out.append(C(S, "llama-server", "ok", f"{srv}\n{ver}{cuda}"))
        except Exception as e:
            out.append(C(S, "llama-server", "warn", f"{srv}: could not run ({type(e).__name__}: {e})", "Re-download llama.cpp; check antivirus"))
    m = s.get("model")
    out.append(C(S, "Assistant model", "ok" if m and Path(m).exists() else "info", m or "no model chosen", "" if m else "Pick a .gguf in the assistant settings"))
    if m and Path(m).exists():
        sz = Path(m).stat().st_size / 2**30
        out.append(C(S, "Model size vs settings", "warn" if sz > 6 and s["gpu_layers"] == 0 else "ok", f"{sz:.1f} GB, GPU layers {s['gpu_layers']}, context {s['ctx']}",
                     "A model this large is slow on CPU; use a 3-4B Q4 model" if sz > 6 and s["gpu_layers"] == 0 else ""))
    out.append(C(S, "Assistant server state", "info", "running and ready" if st.get("ready") else "running, loading" if st.get("running") else "idle (starts on first message)"))
    return out


def check_config(root):
    S = "Config"
    f = Path(root) / "config.json"
    if not f.exists():
        return [C(S, "config.json", "warn", "missing", "It is created when you press Set on the models folder")]
    try:
        json.loads(f.read_text(encoding="utf-8-sig"))
        return [C(S, "config.json", "ok", "valid JSON")]
    except Exception as e:
        return [C(S, "config.json", "warn", f"not valid JSON ({e}); the app repairs backslashes automatically", "Use forward slashes in paths")]


# ---------------- built-in self-tests (CPU only, a couple of seconds) ----------------
def selftests(root):
    S = "Self-test"
    out = []
    import numpy as np
    from PIL import Image

    def run(name, fn):
        t = time.time()
        try:
            out.append(C(S, name, "ok", f"{fn()} ({time.time() - t:.1f}s)"))
        except Exception as e:
            out.append(C(S, name, "fail", f"{type(e).__name__}: {e} @ {traceback.extract_tb(e.__traceback__)[-1].name}", "Send this report to the developer"))

    def sprite():
        a = np.zeros((64, 40, 4), np.uint8)
        a[2:14, 15:25] = (240, 200, 160, 255); a[15:36, 13:27] = (40, 80, 200, 255)
        a[16:34, 9:13] = (200, 40, 40, 255); a[16:34, 27:31] = (200, 40, 40, 255)
        a[36:62, 14:19] = (60, 60, 70, 255); a[36:62, 21:26] = (60, 60, 70, 255)
        return Image.fromarray(a, "RGBA")

    def t_pixelize():
        from . import pixelize as px
        big = Image.new("RGBA", (512, 512), (255, 255, 255, 255)); big.alpha_composite(sprite().resize((240, 384), Image.NEAREST), (100, 60))
        s, i = px.pixelize(big, "auto", colors=8)
        s2, _ = px.pixelize(big, "fixed", 32, 8, outline="selective")
        return f"auto grid {i.get('grid')} -> {s.size}; fixed -> {s2.size}"

    def t_rig():
        from . import rig
        sp = sprite()
        j = rig.autoplace(sp)
        fr, meta = rig.render(sp, j, [], "walk", 4, "right", "r", "r", 1.0, 0, 1, 4)
        d, _ = rig.render(sp, j, [], "death", 3, "right", "r", "r", 1.0, 0, 1, 4)
        return f"walk {len(fr)} frames {fr[0].size}, death canvas {d[0].size}"

    def t_export():
        from . import exporter, rig
        sp = sprite(); j = rig.autoplace(sp)
        ent = []
        for a in ("idle", "walk"):
            fr, meta = rig.render(sp, j, [], a, 3, "right", "r", "r", 1.0, 0, 1, 2)
            ent.append({"name": a, "fps": 8, "loop": True, "frames": fr, "pivot": meta["pivot"]})
        with tempfile.TemporaryDirectory() as tmp:
            r = exporter.export_pack(ent, {"gif": True}, "diag", tmp)
            return f"{len(r['files'])} files, sheet {r['sheet']}"

    def t_projects():
        import base64, io
        from . import projects
        b = io.BytesIO(); sprite().save(b, "PNG"); u = "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
        with tempfile.TemporaryDirectory() as tmp:
            projects.save(tmp, "diag", {"settings": {"a": 1}, "images": {"ref": u}})
            return "save + load ok" if projects.load(tmp, "diag")["images"]["ref"] else "image missing"

    def t_template():
        from . import rig, templates
        sp, j, ov = templates.make_dummy(48, "normal", "side")
        fr, _ = rig.render(sp, j, ov, "walk", 3, "right", "r", "r", 1.0, 0, 1, 2)
        return f"dummy {sp.size} + its rig -> {len(fr)} frames"

    def t_portrait():
        from . import portrait
        im = Image.new("RGBA", (64, 64), (200, 200, 205, 255)); im.paste((240, 200, 165, 255), (16, 12, 48, 52)); im.paste((60, 110, 200, 255), (22, 26, 28, 30))
        def fake(*a):
            x = np.asarray(a[6]).copy(); x[np.asarray(a[7]) > 0] = (245, 120, 150); return Image.fromarray(x)
        ev = [json.loads(e[5:]) for e in portrait.expression_events(im, {"cx": .5, "cy": .5, "rx": .3, "ry": .3}, [("happy", "")], "c", "l", 1, "d", "", "", .8, 20, 7, 1, 4, inpaint_fn=fake)]
        return "expression pipeline ok" if any("result" in e for e in ev) else str(ev[-1])

    for n, f in (("Pixelize (crisp)", t_pixelize), ("Rig animation", t_rig), ("Export (Godot/Unity files)", t_export),
                 ("Projects save/load", t_projects), ("Template dummy + rig", t_template), ("Portrait expression pipeline (no AI)", t_portrait)):
        run(n, f)
    return out


def _tail(path, n):
    try:
        return "\n".join(Path(path).read_text(errors="ignore").splitlines()[-n:])
    except OSError:
        return ""


def build_text(checks, root):
    cnt = collections.Counter(c["status"] for c in checks)
    lines = [f"SpriteForge diagnostics · {time.strftime('%Y-%m-%d %H:%M:%S')}",
             f"Summary: {cnt['ok']} ok, {cnt['warn']} warn, {cnt['fail']} fail, {cnt['info']} info", ""]
    cur = None
    for c in checks:
        if c["section"] != cur:
            cur = c["section"]
            lines += ["", f"== {cur} =="]
        tag = {"ok": "OK  ", "warn": "WARN", "fail": "FAIL", "info": "INFO"}[c["status"]]
        lines.append(f"[{tag}] {c['name']}: {c['detail']}".replace("\n", "\n       "))
        if c["fix"] and c["status"] in ("warn", "fail", "info"):
            lines.append(f"       fix: {c['fix']}")
    if ERRORS:
        lines += ["", "== Recent API errors =="] + [f"{e['t']} {e['where']} {e['status']} {e['detail']}" for e in ERRORS]
    for name in ("engine.log", "llm.log"):
        t = _tail(Path(root) / name, 25 if name == "engine.log" else 12)
        if t:
            lines += ["", f"== {name} (last lines) ==", t]
    return "\n".join(lines)


def run_checks(root, models_dir, llm_state):
    checks = check_system(root) + check_config(root) + check_gpu() + check_models(models_dir) + check_downloads(models_dir) \
        + check_assistant(llm_state, Path(root) / "llm.log") + selftests(root)
    text = build_text(checks, root)
    try:
        (Path(root) / "diagnostics.txt").write_text(text)
    except OSError:
        pass
    cnt = collections.Counter(c["status"] for c in checks)
    return {"checks": checks, "summary": dict(cnt), "text": text}
