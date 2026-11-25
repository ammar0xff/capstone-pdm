import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ml"))
import latency_harness as L


class T(unittest.TestCase):
    def test_percentiles(self):
        xs = list(range(1, 101))
        s = L.summarize([float(x) for x in xs])
        self.assertEqual(s["max_ms"], 100.0); self.assertEqual(s["p50_ms"], 51.0); self.assertEqual(s["n"], 100)

    def test_breach_path_runs_rf_and_nominal_does_not(self):
        from rf_predictor import PdMClassifier
        c = PdMClassifier()
        self.assertFalse(c.predict(L.NOMINAL, return_gate_info=True)[-1]["rf_executed"])
        self.assertTrue(c.predict(L.BREACH, return_gate_info=True)[-1]["stage1_breached"])


if __name__ == "__main__":
    unittest.main()
