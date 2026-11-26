"""Static checks for the redesigned dashboard template (staged, not applied). No browser needed."""
import os, re, subprocess, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "..", "pi_deployed", "staged_not_applied", "templates_index.html.g29")


class TestTemplate(unittest.TestCase):
    def setUp(self):
        self.s = open(P, encoding="utf-8").read()

    def test_scripts_parse(self):
        for i, js in enumerate(re.findall(r"<script>(.*?)</script>", self.s, re.S)):
            f = "/tmp/_g29_%d.js" % i
            open(f, "w").write(js)
            r = subprocess.run(["node", "--check", f], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_api_and_controls_unchanged(self):
        for needle in ["/api/stream", "/api/latest", "/api/history", "/api/commissioning", "btn-commission", "btn-comm-reset", "confirm: true".replace(": ", ":")]:
            self.assertIn(needle, self.s.replace(" ", ""), needle)

    def test_honesty_labels_present(self):
        for needle in ["ref-banner", "label_en", "label_ar", "not a check of motor health", "not a validated", "Default (fixed)", "motor state not verified", "no probability", "Not measured on our motor"]:
            self.assertIn(needle, self.s, needle)

    def test_forbidden_words_absent(self):
        up = self.s.upper()
        self.assertNotIn("DEMO", up)
        self.assertNotIn("UNCALIBRATED", up)

    def test_no_spectrum_claims(self):
        self.assertNotIn("FFT", self.s.upper())

    def test_nine_graph_cards(self):
        for i in ["ch-rms", "ch-z", "ch-kurt", "ch-crest", "ch-axis", "ch-temp", "ch-snd", "ch-bn", 'id="tl"']:
            self.assertIn(i, self.s)


if __name__ == "__main__":
    unittest.main()
