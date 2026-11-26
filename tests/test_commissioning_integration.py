"""Runs the REAL edge_daq.main() loop with fake hardware (synthetic, no Pi) and drives a commissioning
run through the command file, the same path the dashboard uses. Short run constants; logic unchanged."""
import importlib.machinery, importlib.util, json, os, random, shutil, struct, sys, tempfile, threading, time, types, unittest, collections

HERE = os.path.dirname(os.path.abspath(__file__))
EDGE = os.path.join(HERE, "..", "edge")
STAGED = os.path.join(HERE, "..", "pi_deployed", "staged_not_applied")


class FakeBus:
    def __init__(self, n): pass
    def close(self): pass
    def read_byte_data(self, a, r): return 0xE5
    def write_byte_data(self, *a): pass
    def read_i2c_block_data(self, a, r, n):
        return list(struct.pack("<hhh", random.randint(-6, 6), random.randint(-6, 6), 256 + random.randint(-6, 6)))


class FakeSpi:
    max_speed_hz = 0; mode = 0
    def open(self, b, d): pass
    def close(self): pass
    def readbytes(self, n): return [0x03, 0x20]


def wait_for(path, pred, secs):
    t0 = time.time(); last = None
    while time.time() - t0 < secs:
        try:
            with open(path) as f:
                last = json.load(f)
            if pred(last):
                return last
        except Exception:
            pass
        time.sleep(0.2)
    raise AssertionError("timeout; last packet commissioning=%s spc=%s" % ((last or {}).get("commissioning"), (last or {}).get("spc")))


class TestLoop(unittest.TestCase):
    def test_start_accept_reset_through_real_loop(self):
        root = tempfile.mkdtemp(); d = os.path.join(root, "edge"); os.makedirs(d)
        st = os.path.join(root, "state"); os.makedirs(st)
        shutil.copy(os.path.join(EDGE, "commissioning.py"), d)
        shutil.copy(os.path.join(STAGED, "edge_daq.py.g28"), os.path.join(d, "edge_daq.py"))
        # stubs for hardware-bound / model modules
        with open(os.path.join(d, "adxl_fifo.py"), "w") as f:
            f.write('''import threading, time, random, collections
class ADXLFifoReader:
    def __init__(self, adxl, odr_hz=400):
        self.q = collections.deque(maxlen=4000); self.dt = 1.0 / odr_hz
    def start(self):
        threading.Thread(target=self.run, daemon=True).start()
    def run(self):
        while True:
            self.q.append((time.time(), random.gauss(0, 9), random.gauss(0, 9), 256 + random.gauss(0, 9)))
            time.sleep(self.dt)
''')
        mldir = os.path.join(root, "ml")  # edge_daq looks for ../ml relative to its own directory
        os.makedirs(mldir)
        with open(os.path.join(mldir, "rf_predictor.py"), "w") as f:
            f.write('''
class PdMClassifier:
    instances = []
    def __init__(self, model_path):
        self.spc_baseline_rms = 0.080; self.spc_sigma_rms = 0.025
        PdMClassifier.instances.append(self)
    def predict(self, fd, return_gate_info=False):
        return 0, "Normal Operation", 0.9, "Nominal.", {"response_plan": {}, "rf_executed": False, "gate_status": "Stage 1 Gated"}
''')
        os.environ["G12_STATE_DIR"] = st
        sys.modules["smbus2"] = types.SimpleNamespace(SMBus=FakeBus)
        sys.modules["spidev"] = types.SimpleNamespace(SpiDev=FakeSpi)
        sys.path.insert(0, d); sys.path.insert(0, mldir)
        import commissioning as c
        c.TARGET_S, c.MIN_SAMPLES, c.MIN_SAMPLE_GAP_S = 8.0, 15, 0.1
        c.NOISE_FLOOR_G = 0.001
        ld = importlib.machinery.SourceFileLoader("edge_daq_under_test", os.path.join(d, "edge_daq.py"))
        spec = importlib.util.spec_from_loader("edge_daq_under_test", ld)
        m = importlib.util.module_from_spec(spec); ld.exec_module(m)
        self.assertIs(m.commissioning, c)
        threading.Thread(target=m.main, daemon=True).start()
        sf = os.path.join(st, "latest_state.json"); cmd = os.path.join(st, "commission_cmd.json")

        p = wait_for(sf, lambda p: p.get("spc", {}).get("baseline_source") == "default" and p.get("commissioning"), 30)
        self.assertEqual(p["commissioning"]["state"], "idle")
        self.assertEqual((p["spc"]["baseline_mu"], p["spc"]["baseline_sigma"]), (0.080, 0.025))
        self.assertFalse(p["commissioning"]["motor_running_verified"])
        clf = importlib.import_module("rf_predictor").PdMClassifier.instances
        self.assertTrue(clf and clf[0].spc_baseline_rms == 0.080)

        with open(cmd, "w") as f: json.dump({"cmd": "start"}, f)
        p = wait_for(sf, lambda p: p["commissioning"]["state"] == "running", 15)
        self.assertEqual(p["spc"]["baseline_source"], "default")      # fallback stays active while collecting
        self.assertEqual(p["spc"]["baseline_mu"], 0.080)

        p = wait_for(sf, lambda p: p["commissioning"]["state"] in ("done", "failed"), 40)
        self.assertEqual(p["commissioning"]["state"], "done", p["commissioning"])
        self.assertEqual(p["spc"]["baseline_source"], "commissioned")
        mu = p["spc"]["baseline_mu"]
        self.assertLess(mu, 0.08); self.assertGreater(mu, 0.001)
        self.assertAlmostEqual(p["spc"]["ucl_fault"], mu + 3 * p["spc"]["baseline_sigma"], delta=0.001)
        self.assertAlmostEqual(clf[0].spc_baseline_rms, mu, places=5)   # RF stage-1 gate follows
        self.assertTrue(os.path.exists(os.path.join(d, "commissioned_baseline.json")))
        self.assertFalse(os.path.exists(cmd))                            # command consumed

        with open(cmd, "w") as f: json.dump({"cmd": "reset"}, f)
        p = wait_for(sf, lambda p: p["spc"]["baseline_source"] == "default", 15)
        self.assertEqual(p["spc"]["baseline_mu"], 0.080)
        self.assertEqual(clf[0].spc_baseline_rms, 0.080)
        self.assertFalse(os.path.exists(os.path.join(d, "commissioned_baseline.json")))
        self.assertTrue([f for f in os.listdir(d) if ".reset-" in f])    # kept, not deleted

        with open(cmd, "w") as f: f.write("{broken")                      # bad command must not stop the loop
        time.sleep(2.5)
        p1 = wait_for(sf, lambda p: True, 5); time.sleep(1.0); p2 = wait_for(sf, lambda p: True, 5)
        self.assertGreater(p2["seq"], p1["seq"])


if __name__ == "__main__":
    unittest.main()
