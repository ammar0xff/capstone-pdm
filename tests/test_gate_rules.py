"""Characterization: where the Pi's fault rules and the RF stage-1 gate disagree TODAY.
These tests document current behaviour. They do not say which side is right."""
import os, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "edge")); sys.path.insert(0, os.path.join(ROOT, "ml"))
from gate_rules import edge_flags
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


if __name__ == "__main__":
    unittest.main()
