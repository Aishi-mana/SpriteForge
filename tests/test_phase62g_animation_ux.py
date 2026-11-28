from pathlib import Path
from html.parser import HTMLParser

class Layout(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.ids = {}
    def handle_starttag(self, tag, attrs):
        if tag == "details":
            self.depth += 1
        ident = dict(attrs).get("id")
        if ident:
            self.ids.setdefault(ident, []).append(self.depth)
    def handle_endtag(self, tag):
        if tag == "details":
            self.depth -= 1

def run():
    ui = (Path(__file__).resolve().parents[1] / "ui" / "index.html").read_text(encoding="utf-8")
    block = ui.split('id="fullFrameCard"', 1)[1].split('id="systemCard"', 1)[0]
    layout = Layout()
    layout.feed("<div " + block)
    for ident in ("ffReference", "ffPrompt", "ffPreset", "ffVideoModel", "ffVideoCount",
                  "ffVideoFps", "ffGenerateMain", "ffVideoStatus", "ffAutoExtract",
                  "ffReplaceFrames", "ffCanvas", "ffFrames"):
        assert layout.ids[ident] == [0], ident
    assert all(len(v) == 1 for v in layout.ids.values())
    assert "if(FF.doc.frames.length&&!replace)" in ui
    assert "FF.quickVideoRev!==FF.rev" in ui
    assert "if(await ffVideoGenerate())" in ui
    print("ok visible generation and timeline safety contracts")

if __name__ == "__main__":
    run()
