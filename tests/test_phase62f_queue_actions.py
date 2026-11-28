from pathlib import Path

def run():
    ui = (Path(__file__).resolve().parents[1] / "ui" / "index.html").read_text(encoding="utf-8")
    block = ui.split("async function hOpen(id)", 1)[1].split("function hUse(j)", 1)[0]
    assert "render(j.results,$('hres'))" in block
    assert "if(b.closest('#hres'))return;b.onclick=" in block
    print("ok history toolbar excludes result card buttons")

if __name__ == "__main__":
    run()
