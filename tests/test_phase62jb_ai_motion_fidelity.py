import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from engine import wan_video

class WanMotionFidelityTests(unittest.TestCase):
    def test_native_graph_keeps_reference_conditioning_and_enables_cfg(self):
        for conditioning in ("i2v", "flf"):
            q = wan_video.settings({"guidance": {"preset": "idle_minimal"}, "conditioning": conditioning, "wan_quality": "native", "seed": 42})
            self.assertEqual(q["steps"], 20)
            graph = wan_video.graph(q)
            for suffix in ("h", "l"):
                self.assertNotIn("lora_" + suffix, graph)
                self.assertEqual(graph["sh_" + suffix]["inputs"]["model"], ["unet_" + suffix, 0])
            for key in ("ks1", "ks2"):
                self.assertEqual(graph[key]["inputs"]["cfg"], 3.5)
                self.assertEqual(graph[key]["inputs"]["negative"], ["i2v", 1])
            self.assertIn("blinking", graph["neg"]["inputs"]["text"])
            if conditioning == "flf":
                self.assertEqual(graph["i2v"]["inputs"]["start_image"], ["ref1", 0])
                self.assertEqual(graph["i2v"]["inputs"]["end_image"], ["ref2", 0])

    def test_fast_graph_unchanged(self):
        q = wan_video.settings({"guidance": {"preset": "idle_minimal"}})
        graph = wan_video.graph(q)
        self.assertEqual(q["steps"], 4)
        self.assertEqual(graph["ks1"]["inputs"]["cfg"], 1.0)
        self.assertIn("lora_h", graph)
        self.assertIn("lora_l", graph)

    def test_native_rejects_distilled_step_count(self):
        with self.assertRaises(ValueError):
            wan_video.settings({"wan_quality": "native", "steps": 4, "prompt": "idle"})

if __name__ == '__main__':
    unittest.main()
