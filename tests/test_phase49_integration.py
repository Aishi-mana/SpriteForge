"""CPU scene integration benchmark; run from repo root with Python.
Reports wall-clock timings, not GPU or browser performance.
"""
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from engine import modular, scenes, vfx


def fixture(actor_count=8, effect_count=12):
    frames = []
    for i in range(8):
        im = Image.new("RGBA", (48, 64))
        ImageDraw.Draw(im).rectangle((8+i, 8, 38, 55), fill=(210, 90, 30, 255))
        frames.append(modular.png_uri(im))
    actors = [
        dict(id=f"a{i}", x=40+i*55, y=100+i%2*80, end_x=65+i*55,
             flip=bool(i%2), scale=100+i*5, opacity=90, z=i,
             clip=dict(name=f"actor{i}", frames=frames, pivot=[24, 56], fps=8+i))
        for i in range(actor_count)
    ]
    effects = [
        dict(id=f"e{i}", kind=vfx.KINDS[i%len(vfx.KINDS)],
             actor=f"a{i%actor_count}", x=8, y=-20, radius=20,
             seed=i, start=i%4, end=23, pixel=bool(i%2), z=i)
        for i in range(effect_count)
    ]
    return dict(name="Phase49", width=512, height=384, count=24,
                fps=12, actors=actors, effects=effects)


def run():
    scene = fixture()
    timings = []
    for _ in range(3):
        start = time.perf_counter()
        frames, meta = scenes.render(scene)
        timings.append(time.perf_counter()-start)
        assert len(frames) == 24 and meta["indices"] == list(range(24))
        assert all(im.size == (512, 384) and im.mode == "RGBA" for im in frames)
    restored = json.loads(json.dumps(scene))
    replay, replay_meta = scenes.render(restored)
    assert replay_meta == meta
    assert all(a.tobytes() == b.tobytes() for a,b in zip(frames,replay))
    for i in (23, 0, 11, 5):
        scrub, _ = scenes.render(restored, frame=i)
        assert scrub[0].tobytes() == frames[i].tobytes()
    for bad in (dict(scene, actors=scene["actors"]+[scene["actors"][0]]),
                dict(scene, effects=scene["effects"]+[scene["effects"][0]]),
                dict(scene, width=1024, height=1024)):
        try:
            scenes.render(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("Scene budget not enforced")
    median = statistics.median(timings)
    print("ok scene roundtrip, scrub equivalence and budget rejection")
    print(json.dumps(dict(workload="8 actors / 12 effects / 24 frames",
                          seconds=timings, median_seconds=median,
                          rendered_frames_per_second=24/median), indent=2))


if __name__ == "__main__":
    run()
