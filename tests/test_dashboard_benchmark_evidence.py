"""Guards the hosted site's labelled benchmark and evidence display."""

import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = {
    "index": os.path.join(ROOT, "public", "index.html"),
    "guide": os.path.join(ROOT, "public", "guide.html"),
    "calibration": os.path.join(ROOT, "public", "calibration.html"),
}
DASHBOARD = PAGES["index"]
REPORT = os.path.join(ROOT, "ml", "rul_xjtu_sy_report.json")


class BenchmarkDisplayTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DASHBOARD, encoding="utf-8") as handle:
            cls.html = handle.read()
        with open(REPORT, encoding="utf-8") as handle:
            cls.report = json.load(handle)

    def test_benchmark_label_is_visible_and_unambiguous(self):
        self.assertIn("BENCHMARK", self.html)
        self.assertIn("NOT OUR MOTOR", self.html)
        self.assertIn("NOT FIELD-VALIDATED", self.html)
        self.assertIn("not</b> hours-to-failure for the capstone motor", self.html)

    def test_displayed_numbers_match_the_reproducible_report(self):
        expected = {
            "mae": self.report["tail_windows"]["mae_min"],
            "rmse": self.report["tail_windows"]["rmse_min"],
            "baseline": self.report["constant_baseline_tail_windows"]["rmse_min"],
        }
        for name, value in expected.items():
            with self.subTest(metric=name):
                self.assertIn(f"<strong>{value}</strong>", self.html)

    def test_evidence_panel_keeps_unknown_licences_as_needs(self):
        for token in (
            "DATA_PROVENANCE_LICENSES.md",
            "REAL_MOTOR_READINESS.md",
            "10.17632/mpn45f4gxc.1",
            "2 hp Reliance Electric motor",
            "[NEED: explicit reuse licence]",
            "[NEED: explicit FEMTO-ST licence]",
            "[NEED: CWRU licence; exact catalogue number]",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.html)

    def test_benchmark_is_not_written_into_live_telemetry_state(self):
        self.assertNotRegex(self.html, r"benchmark[^\n]*RTDB")
        self.assertNotRegex(self.html, r"FIREBASE_RTDB_URL[^\n]*benchmark")
        self.assertIn(
            "Labelled public benchmark: never live telemetry, never our motor",
            self.html,
        )


class LightModeTest(unittest.TestCase):
    def test_all_hosted_pages_use_light_surface_tokens(self):
        for name, path in PAGES.items():
            with self.subTest(page=name):
                with open(path, encoding="utf-8") as handle:
                    text = handle.read()
                self.assertRegex(text, r"--bg-(?:base|dark):\s*#f4f7fb")
                self.assertNotIn("#090d16", text)
                self.assertNotIn("#040711", text)
                self.assertNotRegex(text, r"--bg-(?:base|dark):\s*#0")


class CalibrationHonestyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(PAGES["calibration"], encoding="utf-8") as handle:
            cls.html = handle.read()

    def test_no_certified_verdict_or_signed_evidence(self):
        for token in (
            r"\bPASS\b",
            r"\bCERTIFIED\b",
            "ISO 17025",
            "DIGITALLY SIGNED",
            "CAL-2026-STEM-0042",
            "10 / 10 Pts Verified",
            "guarantee false-alarm-free",
        ):
            with self.subTest(token=token):
                self.assertNotRegex(self.html, token)

        for token in (
            "Status: REVIEW / UNVERIFIED",
            "REVIEW / UNVERIFIED",
            "NOT ISSUED",
            "NOT VERIFIED",
            "SIGNATURE NOT CAPTURED",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.html)

    def test_no_fake_measurements_or_simulation_defaults(self):
        for token in (
            "+8, +3, +271",
            "+264 LSB",
            "-248 LSB",
            "0.0084g",
            "38.2 dB SPL",
            "> 65.4 dB",
            "0.51%",
            "a = 1.000",
            "b = 0.00",
            "OFFSET_X",
            "SCALE_FACTOR",
            'value="8"',
            'value="3"',
            'value="271"',
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, self.html)

        self.assertNotRegex(self.html, r'<input[^>]+id="input-raw-[xyz]"[^>]+value=')
        self.assertIn('placeholder="NO DATA"', self.html)
        self.assertIn("NO DATA", self.html)
        self.assertIn("AWAITING DATA", self.html)
        self.assertIn("No measurements are supplied by this page", self.html)

    def test_reference_inputs_have_visible_labels(self):
        for axis in ("x", "y", "z"):
            with self.subTest(axis=axis):
                self.assertIn(f'<label for="input-raw-{axis}">', self.html)

        for token in (
            "[NEED: measured site value or pressure]",
            "[NEED: local boiling point]",
            "[NEED: signed noise-floor log and reviewed zone calculation]",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.html)


if __name__ == "__main__":
    unittest.main()
