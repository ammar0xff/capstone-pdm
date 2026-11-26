"""StateHold: display hysteresis in the dashboard template (g29). Runs the real JS block with node."""
import os, re, subprocess, json, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "..", "pi_deployed", "staged_not_applied", "templates_index.html.g29")


def run(seq):
    s = open(P, encoding="utf-8").read()
    blk = next(b for b in re.findall(r"<script>(.*?)</script>", s, re.S) if "const StateHold" in b)
    prog = blk + "\nconst out=[];const seq=%s;for(const [t,r] of seq) out.push(StateHold.update(r,t));console.log(JSON.stringify(out));" % json.dumps(seq)
    open("/tmp/_sh.js", "w").write(prog)
    return json.loads(subprocess.run(["node", "/tmp/_sh.js"], capture_output=True, text=True, check=True).stdout)


class TestHold(unittest.TestCase):
    def test_first_value_shown_at_once(self):
        self.assertEqual(run([[0, 2]]), [2])

    def test_chatter_near_limit_stays_calm(self):
        seq = [[0, 0]] + [[500 * i, 1 if i % 2 else 0] for i in range(1, 30)]
        self.assertEqual(set(run(seq)), {0})  # never sustained 2 s above 0

    def test_sustained_warning_is_shown_after_hold(self):
        seq = [[0, 0]] + [[500 * i, 1] for i in range(1, 10)]
        out = run(seq)
        self.assertEqual(out[1], 0); self.assertEqual(out[-1], 1)

    def test_escalation_goes_to_lowest_sustained_level(self):
        seq = [[0, 0]] + [[500 * i, 2 if i % 2 else 1] for i in range(1, 10)]
        self.assertEqual(run(seq)[-1], 1)  # warning sustained, fault was not

    def test_fault_held_through_dips(self):
        seq = [[0, 2]] + [[500 * i, 1 if i % 3 == 0 else 2] for i in range(1, 30)]
        self.assertEqual(set(run(seq)), {2})

    def test_fault_clears_after_long_quiet(self):
        seq = [[0, 2]] + [[1000 * i, 0] for i in range(1, 10)]
        out = run(seq); self.assertEqual(out[3], 2); self.assertEqual(out[-1], 0)

    def test_invalid_reading_passes_through_and_resets(self):
        out = run([[0, 2], [100, -1], [200, 0]])
        self.assertEqual(out, [2, -1, 0])

    def test_template_uses_held_state(self):
        s = open(P, encoding="utf-8").read()
        self.assertIn("d.__held", s); self.assertIn("The gate itself is unchanged", s)


if __name__ == "__main__":
    unittest.main()
