"""Sim: display-only auto/manual simulation in the dashboard template (g33). Runs the real JS blocks with node."""
import os, re, subprocess, json, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "..", "pi_deployed", "staged_not_applied", "templates_index.html.g33")


def run(expr):
    s = open(P, encoding="utf-8").read()
    bl = re.findall(r"<script>(.*?)</script>", s, re.S)
    plaus = next(b for b in bl if "const Plaus" in b); sim = next(b for b in bl if "const Sim" in b)
    prog = plaus + "\n" + sim + "\n" + expr
    open("/tmp/_sim.js", "w").write(prog)
    return json.loads(subprocess.run(["node", "/tmp/_sim.js"], capture_output=True, text=True, check=True).stdout)


def rd(temp=40.0, rms=0.39, fs=390.0, db=70.0, kurt=1.8, crest=1.5):
    return {"online": True, "state": "Fault", "temperature": {"temp_c": temp, "slope_c_per_min": 0.5, "open_tc": 0},
            "vibration": {"rms_dyn": rms, "peak_dyn": 0.6, "kurtosis": kurt, "crest_factor": crest, "ax_dyn": 0.1, "ay_dyn": 0, "az_dyn": 0, "fs_hz": fs},
            "spc": {"baseline_mu": 0.08, "baseline_sigma": 0.025, "z_score": 12.0}, "acoustic": {"db_spl": db}, "system": {}}


SETUP = "const rd=%s;function mk(o){const r=JSON.parse(JSON.stringify(rd));if(o.temp!==undefined)r.temperature.temp_c=o.temp;if(o.rms!==undefined)r.vibration.rms_dyn=o.rms;if(o.fs!==undefined)r.vibration.fs_hz=o.fs;if(o.db!==undefined)r.acoustic.db_spl=o.db;if(o.kurt!==undefined)r.vibration.kurtosis=o.kurt;return r}" \
        "function step(o,t){const raw=mk(o),P=Plaus.apply(raw),d=Sim.autoApply(P.d,raw,P.cl,P.fl,t);return {d:d,cl:P.cl,raw:raw}}" % json.dumps(rd())


class T(unittest.TestCase):
    def test_clean_readings_are_not_touched(self):
        o = run(SETUP + "const x=step({},1000);console.log(JSON.stringify([x.d.__sim||false,x.d.temperature.temp_c,x.d.vibration.rms_dyn]))")
        self.assertEqual(o, [False, 40.0, 0.39])

    def test_hot_glitch_wobbles_around_60_never_above_and_not_fixed(self):
        o = run(SETUP + "step({temp:40},0);const r=[];for(let t=1000;t<7200000;t+=1000){const x=step({temp:160+(t%7)*20},t);r.push([x.d.temperature.temp_c,x.d.__sim===true])}console.log(JSON.stringify(r))")
        v = [a for a, _ in o]
        self.assertLessEqual(max(v), 60.0); self.assertGreaterEqual(min(v), 55.0); self.assertGreater(len(set(v)), 6)
        self.assertTrue(all(s for _, s in o))

    def test_sustained_real_high_temp_also_simulated_by_decision(self):
        o = run(SETUP + "step({temp:50},0);let last;for(let t=1000;t<60000;t+=1000){last=step({temp:50+t/2000},t)}console.log(JSON.stringify([last.d.temperature.temp_c,last.raw.temperature.temp_c]))")
        self.assertLessEqual(o[0], 60.0); self.assertGreater(o[1], 60.0)

    def test_zero_dropout_stays_near_last_good(self):
        o = run(SETUP + "step({temp:41},0);const x=step({temp:0},1000);console.log(JSON.stringify([x.d.temperature.temp_c,x.d.__sim]))")
        self.assertTrue(40 <= o[0] <= 42 and o[1])

    def test_vibration_glitch_stays_near_last_good_and_clears_plus_marks(self):
        o = run(SETUP + "step({},0);const x=step({rms:14.2,kurt:119,fs:54.6},1000);console.log(JSON.stringify([x.d.vibration.rms_dyn,x.d.vibration.kurtosis,x.d.vibration.fs_hz,x.cl.kurt||false,x.d.state]))")
        self.assertTrue(0.3 < o[0] < 0.5); self.assertTrue(1.5 < o[1] < 2.2); self.assertTrue(390 < o[2] < 405); self.assertFalse(o[3]); self.assertEqual(o[4], "Fault")

    def test_sound_glitch(self):
        o = run(SETUP + "step({},0);const x=step({db:130},1000);console.log(JSON.stringify(x.d.acoustic.db_spl))")
        self.assertTrue(66 < o < 74)

    def test_hold_then_release_after_10s(self):
        o = run(SETUP + "step({},0);step({temp:300},1000);const a=step({temp:41},5000);const b=step({temp:41},12000);console.log(JSON.stringify([a.d.__sim===true,b.d.__sim===true]))")
        self.assertEqual(o, [True, False])

    def test_footer_text_lists_sensors_both_languages_and_raw_temp(self):
        o = run(SETUP + "step({temp:160},1000);console.log(JSON.stringify(Sim._text()))")
        for k in ("DEMO", "Demo mode: simulated sensor values, not measurements", "temperature", "وضع تجريبي", "Raw temperature reading: 160.0"):
            self.assertIn(k, o)

    def test_reference_untouched_and_state_untouched(self):
        o = run(SETUP + "const g=mk({temp:500});g.reference_data={a:1};const P=Plaus.apply(g);const d=Sim.autoApply(P.d,g,P.cl,P.fl,1);console.log(JSON.stringify([d.temperature.temp_c,d.__sim||false]))")
        self.assertEqual(o, [500.0, False])

    def test_template_wiring_and_no_claims(self):
        s = open(P, encoding="utf-8").read()
        for k in ('id="btn-sim"', "Sim.autoApply(P.d,raw,P.cl,P.fl,Date.now())", "Sim.guard()", "setInterval(function(){try{Sim.guard"):
            self.assertIn(k, s)
        for bad in ("certified", "healthy motor", "is validated"):
            self.assertNotIn(bad, s.lower())


if __name__ == "__main__":
    unittest.main()
