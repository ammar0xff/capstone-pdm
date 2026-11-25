"""Characterization + parity. Reference_* below are the ORIGINAL inline expressions, kept verbatim
so the shared module is proven to preserve behaviour on a grid. Wiring tests check that
edge_daq and rf_predictor really use the module. Where the Pi's fault rules and the RF stage-1 gate disagree TODAY.
These tests document current behaviour. They do not say which side is right."""
import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ml"))
from gate_thresholds import edge_flags
from rf_predictor import PdMClassifier

UCL_W, UCL_F = 0.13, 0.155  # the comments in edge_daq give these example values


def rf_breached(rms=0.01, peak=0.02, cf=2.0, kurt=3.0, temp=25.0, slope=0.0):
    c = PdMClassifier(model_path="/nonexistent")
    c.model = None
    r = c.predict({"rms_dyn": rms, "peak_dyn": peak, "crest_factor": cf, "kurtosis": kurt,
                   "temp_c": temp, "temp_slope": slope}, return_gate_info=True)
    return r[-1]["stage1_breached"]


def edge(**k):
    d = dict(rms_dyn=0.01, kurtosis=3.0, peak_dyn=0.02, temp_c=25.0, temp_slope=0.0, sound_db=60.0, sound_zcr=0.02)
    d.update(k)
    return edge_flags(ucl_warning=UCL_W, ucl_fault=UCL_F, **d)


class T(unittest.TestCase):
    def test_quiet_state_agrees(self):
        self.assertFalse(rf_breached()); self.assertFalse(edge()["any_fault"])

    def test_crest_factor_over_4_trips_rf_only(self):
        self.assertTrue(rf_breached(cf=4.5)); self.assertFalse(edge()["any_fault"])  # edge ignores crest factor

    def test_temp_55_to_70_trips_rf_not_edge_fault(self):
        self.assertTrue(rf_breached(temp=60.0))
        e = edge(temp_c=60.0); self.assertFalse(e["thermal_fault"]); self.assertTrue(e["thermal_warn"])

    def test_kurtosis_5_to_7_trips_rf_edge_only_warns_when_rms_low(self):
        self.assertTrue(rf_breached(kurt=6.0))
        self.assertFalse(edge(kurtosis=6.0, rms_dyn=0.05)["vib_fault"])
        self.assertTrue(edge(kurtosis=6.0, rms_dyn=0.05)["vib_warn"])

    def test_sound_is_a_fault_rule_on_edge_only(self):
        self.assertTrue(edge(sound_db=90.0)["any_fault"]); self.assertFalse(rf_breached())

    def test_rms_between_rf_fixed_limit_and_edge_ucl(self):
        self.assertTrue(rf_breached(rms=0.125))   # RF: rms > 0.120
        self.assertFalse(edge(rms_dyn=0.125)["vib_fault"])  # edge: needs > ucl_fault


def ref_edge(rms, kurt, peak, temp, slope, db, zcr, uw, uf):
    tf = (temp > 70.0) or (slope > 10.0); tw = (temp > 50.0) or (slope > 5.0)
    vf = (rms > uf) or (kurt > 7.0 and rms > 0.03) or (peak > 0.40)
    vw = (rms > uw) or (kurt > 5.0 and rms > 0.03) or (peak > 0.25)
    sf = (db > 88.0) or (zcr > 0.28)
    return tf, tw, vf, vw, sf


def ref_rf(rms, kurt, cf, temp, slope, base=0.080, sig=0.025, zt=2.0, st=5.0):
    z = (rms - base) / max(1e-5, sig)
    return (z > zt or kurt > 5.0 or cf > 4.0 or rms > 0.120) or (abs(slope) > st or temp > 55.0)


class Parity(unittest.TestCase):
    def test_edge_grid_identical_to_original(self):
        import itertools
        g = itertools.product([0.01, 0.03, 0.031, 0.12, 0.13, 0.131, 0.155, 0.16], [3, 5, 5.01, 7, 7.01],
                              [0.1, 0.25, 0.251, 0.4, 0.401], [25, 50, 50.1, 70, 70.1], [0, 5, 5.1, 10, 10.1, -20],
                              [60, 88, 88.1], [0.02, 0.28, 0.281])
        n = 0
        for rms, k, pk, t, sl, db, zc in g:
            f = edge_flags(rms, k, pk, t, sl, db, zc, UCL_W, UCL_F)
            self.assertEqual((f["thermal_fault"], f["thermal_warn"], f["vib_fault"], f["vib_warn"], f["sound_fault"]),
                             ref_edge(rms, k, pk, t, sl, db, zc, UCL_W, UCL_F)); n += 1
        self.assertGreater(n, 50000)

    def test_rf_grid_identical_to_original_via_predict(self):
        import itertools
        n = 0
        for rms, k, cf, t, sl in itertools.product([0.01, 0.08, 0.119, 0.12, 0.121, 0.13, 0.131, 0.2], [3, 5, 5.01],
                                                   [2, 4, 4.01], [25, 55, 55.1], [0, 5, 5.1, -5.1]):
            self.assertEqual(rf_breached(rms=rms, kurt=k, cf=cf, temp=t, slope=sl), ref_rf(rms, k, cf, t, sl)); n += 1
        self.assertGreater(n, 800)

    def test_rf_custom_instance_params_still_honoured(self):
        c = PdMClassifier(model_path="/nonexistent", spc_baseline_rms=0.2, spc_sigma_rms=0.01, spc_z_thresh=1.0)
        c.model = None
        r = c.predict({"rms_dyn": 0.215, "temp_c": 25.0}, return_gate_info=True)
        self.assertEqual(r[-1]["stage1_breached"], ref_rf(0.215, 3.0, 2.0, 25.0, 0.0, 0.2, 0.01, 1.0))

    def test_wiring_no_inline_thresholds_left(self):
        src = open(os.path.join(ROOT, "edge", "edge_daq.py")).read()
        self.assertIn("edge_flags(", src)
        for lit in ("> 70.0", "> 88.0", "> 0.28", "> 0.40"):
            self.assertNotIn(lit, src)
        rf = open(os.path.join(ROOT, "ml", "rf_predictor.py")).read()
        self.assertIn("rf_stage1(", rf); self.assertNotIn("is_vibration_anomaly", rf)


if __name__ == "__main__":
    unittest.main()
