import json, os, sys, tempfile, unittest
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "edge"))
import reference_replay as rr  # noqa: E402


def make_bearing(n=120, grow_from=90, seed=0):
    """Synthetic stand-in files in the PRONOSTIA layout: 6 columns, 2560 samples, columns 5 and 6 are the axes."""
    d = tempfile.mkdtemp(); rng = np.random.default_rng(seed); t = np.arange(2560) / rr.FS
    for i in range(n):
        amp = 0.4 + (0.12 * (i - grow_from) if i >= grow_from else 0.0)
        h = amp * np.sin(2 * np.pi * 60 * t) + rng.normal(0, 0.05, 2560) + 2.0 * np.sin(2 * np.pi * 4000 * t)
        v = 0.6 * amp * np.sin(2 * np.pi * 60 * t + 1) + rng.normal(0, 0.05, 2560)
        rows = np.column_stack([np.full(2560, 9), np.full(2560, 39), np.full(2560, 39), np.arange(2560), h, v])
        np.savetxt(os.path.join(d, "acc_%05d.csv" % (i + 1)), rows, delimiter=",", fmt="%g")
    return d


class TestFeatures(unittest.TestCase):
    def test_bandlimit_removes_high_tone_keeps_low(self):
        t = np.arange(2560) / rr.FS
        low, high = np.sin(2 * np.pi * 60 * t), np.sin(2 * np.pi * 4000 * t)
        self.assertLess(np.std(rr.bandlimit(high, 180)), 0.01)
        self.assertGreater(np.std(rr.bandlimit(low, 180)), 0.6)

    def test_dc_removed_and_finite(self):
        f = rr.snapshot_features(np.full(2560, 5.0), np.full(2560, -3.0))
        self.assertAlmostEqual(f["rms_dyn"], 0.0, places=6)
        self.assertEqual(f["kurtosis"], 3.0)

    def test_rms_follows_amplitude(self):
        t = np.arange(2560) / rr.FS
        a = rr.snapshot_features(np.sin(2 * np.pi * 60 * t), np.zeros(2560))["rms_dyn"]
        b = rr.snapshot_features(2 * np.sin(2 * np.pi * 60 * t), np.zeros(2560))["rms_dyn"]
        self.assertAlmostEqual(b / a, 2.0, places=2)


class TestReplay(unittest.TestCase):
    def setUp(self):
        self.bd = make_bearing()
        self.sd = os.path.join(tempfile.mkdtemp(), "pdm_reference")
        self.pkts = []
        orig = rr.write_state
        def spy(sd, pkt):
            self.pkts.append(pkt); orig(sd, pkt)
        rr.write_state = spy
        self.addCleanup(setattr, rr, "write_state", orig)

    def go(self, **kw):
        args = dict(speed=0, ref_snapshots=10, commission_snapshots=60, min_samples=40, settle_snapshots=0)
        args.update(kw)
        return rr.run(self.bd, self.sd, **args)

    def test_label_and_schema_on_every_packet(self):
        self.go()
        self.assertEqual(len(self.pkts), 120)
        for p in self.pkts:
            self.assertEqual(p["reference_data"]["label_en"], "Reference data: PRONOSTIA, stand-in for the motor signal (public benchmark)")
            self.assertIn("بديل لإشارة الموتور", p["reference_data"]["label_ar"])
            for k in ("vibration", "spc", "commissioning", "state", "seq", "input_valid"):
                self.assertIn(k, p)
            self.assertNotIn("DEMO", json.dumps(p))

    def test_amplitude_scaled_to_healthy_level(self):
        self.go()
        first = [p["vibration"]["rms_dyn"] for p in self.pkts[:10]]
        self.assertAlmostEqual(float(np.median(first)), 0.03, delta=0.003)
        self.assertEqual(self.pkts[0]["reference_data"]["healthy_level_g"], 0.03)

    def test_default_then_commissioned_then_fault(self):
        self.go()
        self.assertEqual(self.pkts[5]["spc"]["baseline_source"], "default")
        self.assertEqual(self.pkts[5]["spc"]["baseline_mu"], 0.080)
        self.assertEqual(self.pkts[5]["commissioning"]["state"], "running")
        done = [p for p in self.pkts if p["commissioning"]["state"] == "done"]
        self.assertTrue(done)
        self.assertEqual(done[0]["spc"]["baseline_source"], "commissioned")
        self.assertAlmostEqual(done[0]["spc"]["baseline_mu"], 0.03, delta=0.004)
        self.assertFalse(done[0]["commissioning"]["motor_running_verified"])
        self.assertEqual(self.pkts[70]["state"], "Healthy")
        states = [p["state"] for p in self.pkts]
        self.assertIn("Fault", states[90:])
        self.assertEqual(self.pkts[-1]["fault_label"], "Rule-based fault state (elevated rms)")

    def test_gate_limits_follow_commissioned_baseline(self):
        self.go()
        p = self.pkts[-1]["spc"]
        self.assertAlmostEqual(p["ucl_fault"], p["baseline_mu"] + 3 * p["baseline_sigma"], places=3)

    def test_commissioning_waits_for_run_in(self):
        self.go(settle_snapshots=15, commission_snapshots=60)
        self.assertEqual(self.pkts[10]["commissioning"]["state"], "idle")
        self.assertEqual(self.pkts[20]["commissioning"]["state"], "running")
        self.assertTrue(any(p["commissioning"]["state"] == "done" for p in self.pkts))

    def test_trend_estimate_only_on_a_real_rise(self):
        self.go()
        self.assertEqual(self.pkts[40]["reference_data"]["rul_trend"]["status"], "insufficient")
        self.assertEqual(self.pkts[85]["reference_data"]["rul_trend"]["status"], "no_upward_trend")   # flat healthy part
        late = [p["reference_data"]["rul_trend"] for p in self.pkts[100:]]
        self.assertTrue(any(t["status"] in ("estimate", "at_limit") for t in late))
        est = [t for t in late if t["status"] == "estimate"]
        for t in est:
            self.assertGreater(t["hours_to_limit"], 0)
        self.assertEqual(self.pkts[-1]["reference_data"]["rul_trend"]["true_remaining_h"], 0.0)

    def test_trend_function_guards(self):
        flat = [0.03 + 0.0001 * ((i * 7) % 5) for i in range(100)]
        self.assertEqual(rr.rul_trend(flat, 0.2, 200, 100)["status"], "no_upward_trend")
        falling = [0.05 - 0.0002 * i for i in range(100)]
        self.assertEqual(rr.rul_trend(falling, 0.2, 200, 100)["status"], "no_upward_trend")
        rising = [0.03 + 0.001 * i for i in range(100)]
        r = rr.rul_trend(rising, 0.2, 200, 100)
        self.assertEqual(r["status"], "estimate")
        self.assertAlmostEqual(r["hours_to_limit"], (0.2 - 0.129) / (0.001 / 10) / 3600, delta=0.05)
        self.assertEqual(rr.rul_trend([0.3] * 100, 0.2, 200, 100)["status"], "at_limit")
        self.assertEqual(rr.rul_trend([0.03] * 10, 0.2, 200, 10)["status"], "insufficient")

    def test_no_autostart_keeps_default(self):
        self.go(autostart=False)
        self.assertTrue(all(p["spc"]["baseline_source"] == "default" for p in self.pkts))

    def test_reset_command_returns_to_default(self):
        sd = self.sd; os.makedirs(sd, exist_ok=True)
        n = {"i": 0}; orig = rr.write_state
        def spy(s, pkt):
            n["i"] += 1; orig(s, pkt)
            if n["i"] == 80:
                with open(os.path.join(sd, "commission_cmd.json"), "w") as f:
                    json.dump({"cmd": "reset"}, f)
        rr.write_state = spy
        self.addCleanup(setattr, rr, "write_state", orig)
        pk = self.go(speed=0)
        self.assertEqual(pk["spc"]["baseline_source"], "default")

    def test_writes_only_to_its_own_dir(self):
        live = tempfile.mkdtemp()
        os.environ["G12_STATE_DIR"] = live
        self.addCleanup(os.environ.pop, "G12_STATE_DIR", None)
        self.go()
        self.assertEqual(os.listdir(live), [])
        self.assertTrue(os.path.exists(os.path.join(self.sd, "latest_state.json")))

    def test_cli_refuses_live_state_dir(self):
        os.environ["G12_STATE_DIR"] = self.sd
        self.addCleanup(os.environ.pop, "G12_STATE_DIR", None)
        with self.assertRaises(SystemExit):
            rr.main(["--bearing-dir", self.bd, "--state-dir", self.sd, "--speed", "0"])

    def test_missing_dir(self):
        with self.assertRaises(FileNotFoundError):
            rr.run(tempfile.mkdtemp(), self.sd, speed=0)


if __name__ == "__main__":
    unittest.main()
