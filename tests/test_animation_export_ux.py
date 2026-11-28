from pathlib import Path

def run():
    root = Path(__file__).resolve().parents[1]
    ui = (root / "ui/index.html").read_text(encoding="utf-8")
    start = ui.index('id="ffFrames"')
    end = ui.index("Animation settings, canvas", start)
    visible = ui[start:end]
    for action in ("ffSaveFrame()", "ffExport('atlas')", "ffExport('png')", "ffExport('webp')"):
        assert action in visible, action
    assert ui.count('id="ffExportStatus"') == 1
    assert "flex:0 0 76px" in ui
    assert "return downloadImage(src,name+" in ui
    assert "Mandatory user-first UX policy" in (root / "AGENTS.md").read_text(encoding="utf-8")
    print("ok visible sprite exports, compact timeline and UX policy")

if __name__ == "__main__":
    run()
