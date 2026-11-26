import json, os, random, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "edge"))
import commissioning as c


class Clock:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t
    def tick(self, s): self.t += s


def run(comm, clk, gen, seconds=600, step=0.1, valid=lambda i: True):
    done, i = False, 0
    for i in range(int(seconds / step) + 2):
        clk.tick(step)
        done = comm.feed(gen(i), valid(i)) or done
    return done


class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.p = os.path.join(self.d, "commissioned_baseline.json")
        self.clk = Clock()
        self.cm = c.Commissioner(self.p, clock=self.clk)
        self.rng = random.Random(1)

    def healthy(self, mu=0.03, sd=0.004):
        return lambda i: max(0.0, self.rng.gauss(mu, sd))


class TestDefaults(Base):
    def test_default_until_commissioned(self):
        s = self.cm.status()
        self.assertEqual((s["baseline_source"], s["mu"], s["sigma"]), ("default", 0.080, 0.025))
        self.assertFalse(s["motor_running_verified"])

    def test_default_limits_unchanged(self):
        lim = c.limits(c.default_baseline())
        self.assertAlmostEqual(lim["ucl_warning"], 0.130)
        self.assertAlmostEqual(lim["ucl_fault"], 0.155)

    def test_feed_ignored_when_idle(self):
        self.assertFalse(self.cm.feed(0.03, True))
        self.assertEqual(self.cm.windows_seen, 0)


class TestRun(Base):
    def test_accepts_stable_run_and_saves(self):
        self.assertTrue(self.cm.start())
        self.assertTrue(run(self.cm, self.clk, self.healthy()))
        s = self.cm.status()
        self.assertEqual(s["state"], "done")
        self.assertEqual(s["baseline_source"], "commissioned")
        self.assertAlmostEqual(s["mu"], 0.03, delta=0.002)
        self.assertGreater(s["sigma"], 0.002)
        saved = json.load(open(self.p))
        self.assertFalse(saved["motor_running_verified"])
        self.assertGreaterEqual(saved["n_windows"], c.MIN_SAMPLES)

    def test_reload_after_restart(self):
        self.cm.start(); run(self.cm, self.clk, self.healthy())
        again = c.Commissioner(self.p, clock=self.clk)
        self.assertEqual(again.baseline["source"], "commissioned")
        self.assertAlmostEqual(again.baseline["mu"], self.cm.baseline["mu"])

    def test_samples_are_non_overlapping(self):
        self.cm.start(); run(self.cm, self.clk, self.healthy(), seconds=60)
        self.assertLessEqual(self.cm.windows_seen, int(60 / c.MIN_SAMPLE_GAP_S) + 2)

    def test_start_while_running_is_ignored(self):
        self.assertTrue(self.cm.start())
        self.assertFalse(self.cm.start())

    def test_progress_reported(self):
        self.cm.start(); run(self.cm, self.clk, self.healthy(), seconds=120)
        s = self.cm.status()
        self.assertEqual(s["state"], "running")
        self.assertAlmostEqual(s["progress_s"], 120, delta=1)
        self.assertEqual(s["baseline_source"], "default")  # fallback while collecting


class TestRejections(Base):
    def _failed(self, gen, **kw):
        self.cm.start(); run(self.cm, self.clk, gen, **kw)
        s = self.cm.status()
        self.assertEqual(s["state"], "failed", s)
        self.assertEqual(s["baseline_source"], "default")
        self.assertFalse(os.path.exists(self.p))
        return s

    def test_noise_floor_refused(self):
        self._failed(lambda i: 0.0008)

    def test_above_default_fault_limit_refused(self):
        s = self._failed(self.healthy(mu=0.2, sd=0.01))
        self.assertIn("above the default fault limit", s["message"])

    def test_drift_refused(self):
        self._failed(lambda i: 0.02 + 0.04 * (i / 6000.0) + self.rng.gauss(0, 0.001))

    def test_too_many_outliers_refused(self):
        g = lambda i: 0.09 if self.rng.random() < 0.15 else self.rng.gauss(0.03, 0.002)
        self._failed(g)

    def test_invalid_windows_refused(self):
        s = self._failed(self.healthy(), valid=lambda i: i % 5 != 0)
        self.assertIn("invalid", s["message"])

    def test_nan_counts_as_invalid(self):
        self._failed(lambda i: float("nan"))

    def test_cancel_keeps_baseline(self):
        self.cm.start(); run(self.cm, self.clk, self.healthy(), seconds=30)
        self.assertTrue(self.cm.cancel())
        self.assertEqual(self.cm.status()["baseline_source"], "default")


class TestSigmaFloorAndReset(Base):
    def write(self, text):
        with open(self.p, "w") as f:
            f.write(text)

    def test_sigma_floor(self):
        ok, res, _ = c.compute_baseline([0.03] * 300)
        self.assertTrue(ok)
        self.assertGreaterEqual(res["sigma"], c.SIGMA_REL_FLOOR * 0.03)

    def test_reset_keeps_old_file(self):
        self.cm.start(); run(self.cm, self.clk, self.healthy())
        self.assertTrue(os.path.exists(self.p))
        self.cm.reset()
        self.assertEqual(self.cm.baseline["source"], "default")
        self.assertFalse(os.path.exists(self.p))
        kept = [f for f in os.listdir(self.d) if ".reset-" in f]
        self.assertEqual(len(kept), 1)

    def test_corrupt_file_falls_back_to_default(self):
        self.write("{not json")
        self.assertEqual(c.Commissioner(self.p).baseline["source"], "default")
        self.write(json.dumps({"source": "commissioned", "mu": -1, "sigma": 0.01}))
        self.assertEqual(c.Commissioner(self.p).baseline["source"], "default")
        self.write(json.dumps({"source": "commissioned", "mu": 0.5, "sigma": 0.01}))
        self.assertEqual(c.Commissioner(self.p).baseline["source"], "default")


if __name__ == "__main__":
    unittest.main()
