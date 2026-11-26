"""Plaus: display-only plausibility caps in the dashboard template (g32). Runs the real JS block with node."""
import os, re, subprocess, json, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "..", "pi_deployed", "staged_not_applied", "templates_index.html.g32")


def run(readings):
    s = open(P, encoding="utf-8").read()
    blk = next(b for b in re.findall(r"<script>(.*?)</script>", s, re.S) if "const Plaus" in b)
    prog = blk + "\nconst rs=%s;const out=rs.map(r=>{const o=Plaus.apply(r);return {d:o.d,cl:o.cl,fl:o.fl}});console.log(JSON.stringify(out));" % json.dumps(readings)
    open("/tmp/_pl.js", "w").write(prog)
    return json.loads(subprocess.run(["node", "/tmp/_pl.js"], capture_output=True, text=True, check=True).stdout)


def r(temp=40.0, slope=0.5, rms=0.4, peak=0.6, kurt=2.0, crest=1.5, ax=0.1, z=1.0, db=70.0, fs=390.0):
    return {"online": True, "state": "Healthy", "temperature": {"temp_c": temp, "slope_c_per_min": slope},
            "vibration": {"rms_dyn": rms, "peak_dyn": peak, "kurtosis": kurt, "crest_factor": crest, "ax_dyn": ax, "ay_dyn": 0.0, "az_dyn": 0.0, "fs_hz": fs},
            "spc": {"z_score": z}, "acoustic": {"db_spl": db}}


class T(unittest.TestCase):
    def test_normal_values_untouched(self):
        o = run([r()])[0]
        self.assertEqual(o["cl"], {}); self.assertEqual(o["fl"], {"temp": False, "vib": False, "snd": False})
        self.assertEqual(o["d"]["temperature"]["temp_c"], 40.0)

    def test_temp_never_above_60_and_marked(self):
        for raw in (60.5, 147.5, 312.25, 1023.75):
            o = run([r(temp=raw)])[0]
            self.assertEqual(o["d"]["temperature"]["temp_c"], 60); self.assertTrue(o["cl"]["temp"]); self.assertTrue(o["fl"]["temp"])

    def test_exactly_60_is_a_plain_value(self):
        o = run([r(temp=60.0)])[0]
        self.assertFalse(o["cl"].get("temp")); self.assertEqual(o["d"]["temperature"]["temp_c"], 60)

    def test_zero_dropout_is_held_and_flagged(self):
        o = run([r(temp=55.0), r(temp=0.0), r(temp=55.25)])
        self.assertEqual(o[1]["d"]["temperature"]["temp_c"], 55.0); self.assertTrue(o[1]["fl"]["temp"]); self.assertFalse(o[2]["fl"]["temp"])

    def test_jump_held_then_accepted_after_three(self):
        o = run([r(temp=30.0)] + [r(temp=45.0)] * 5)
        self.assertEqual([x["d"]["temperature"]["temp_c"] for x in o], [30.0, 30.0, 30.0, 30.0, 45.0, 45.0])
        self.assertTrue(o[1]["fl"]["temp"]); self.assertFalse(o[5]["fl"]["temp"])

    def test_slope_hidden_when_temp_unreliable(self):
        o = run([r(temp=200.0, slope=100.32)])[0]
        self.assertTrue(o["cl"]["slope_na"])

    def test_vibration_caps(self):
        o = run([r(rms=20.0, peak=176.6, kurt=119.4, crest=40.0, ax=-30.0, z=565.9)])[0]
        d = o["d"]["vibration"]
        self.assertEqual((d["rms_dyn"], d["peak_dyn"], d["kurtosis"], d["crest_factor"], d["ax_dyn"]), (16, 16, 30, 16, -16))
        self.assertEqual(o["d"]["spc"]["z_score"], 20); self.assertTrue(o["fl"]["vib"])
        for k in ("rms", "kurt", "crest", "ax", "z"): self.assertTrue(o["cl"][k])

    def test_low_sampling_flags_vibration_but_keeps_value(self):
        o = run([r(fs=54.6)])[0]
        self.assertTrue(o["fl"]["vib"]); self.assertEqual(o["d"]["vibration"]["fs_hz"], 54.6)

    def test_sound_cap(self):
        o = run([r(db=130.0)])[0]
        self.assertEqual(o["d"]["acoustic"]["db_spl"], 110); self.assertTrue(o["fl"]["snd"])

    def test_reference_data_untouched(self):
        x = r(temp=500.0); x["reference_data"] = {"label_en": "x"}
        o = run([x])[0]
        self.assertEqual(o["d"]["temperature"]["temp_c"], 500.0)

    def test_state_and_input_not_changed(self):
        x = r(rms=50.0); x["state"] = "Fault"
        o = run([x])[0]
        self.assertEqual(o["d"]["state"], "Fault")

    def test_template_wiring(self):
        s = open(P, encoding="utf-8").read()
        for k in ("Plaus.apply(d)", "Plaus.fmt(d.__cl.temp", "plaus-bar", "Sensor unreliable", "d.__held=heldSev(d)"):
            self.assertIn(k, s)
        self.assertEqual(s.count("StateHold.update"), 1)


if __name__ == "__main__":
    unittest.main()
