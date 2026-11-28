import sys, tempfile
from pathlib import Path
from unittest.mock import patch, Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine import wan_video as W

def render():
    with W.workspace():
        return b"mp4-result"

def run():
    with tempfile.TemporaryDirectory() as t:
        d=Path(t)/"job";d.mkdir()
        with patch.object(W.tempfile,"mkdtemp",return_value=str(d)), patch.object(W.local_runtime,"ROOT",Path(t)), patch.object(W.shutil,"rmtree",side_effect=PermissionError("locked engine.log")) as rm, patch.object(W.time,"sleep"):
            assert render()==b"mp4-result"
            assert rm.call_count==5
            try:
                with W.workspace():
                    raise ValueError("original inference error")
            except ValueError as e:
                assert str(e)=="original inference error"
            else:raise AssertionError("original error lost")
        child=Mock();child.poll.return_value=None
        W.stop_owned(child)
        child.terminate.assert_called_once()
        child.wait.assert_called_once_with(timeout=15)
    print("ok Windows cleanup preserves output and original error")

if __name__=="__main__":
    run()
