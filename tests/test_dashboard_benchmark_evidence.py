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
FMCG_REPORT = os.path.join(ROOT, "ml", "rul_fmcg_report.json")
CWRU_REPORT = os.path.join(ROOT, "ml", "diagnosis_cwru_report.json")
CMAPSS_REPORT = os.path.join(ROOT, "ml", "rul_cmapss_warning_report.json")


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


class FmcgBenchmarkDisplayTest(unittest.TestCase):
    """The headline real-motor panel quotes the committed measured report."""

    @classmethod
    def setUpClass(cls):
        with open(DASHBOARD, encoding="utf-8") as handle:
            cls.html = handle.read()
        with open(PAGES["guide"], encoding="utf-8") as handle:
            cls.guide = handle.read()
        with open(FMCG_REPORT, encoding="utf-8") as handle:
            cls.report = json.load(handle)

    def test_headline_numbers_match_the_committed_report(self):
        tail = self.report["tail_windows"]
        zero = self.report["constant_zero_baseline_tail_windows"]
        no_warning = self.report["constant_no_warning_baseline_tail_windows"]
        self.assertEqual(tail["mae_h"], 141.716)
        self.assertEqual(tail["rmse_h"], 204.069)
        self.assertEqual(tail["accuracy"], 0.677)
        self.assertEqual(tail["recall"], 0.029)
        for expected in (
            f"<strong>{tail['mae_h']} h</strong>",
            f"<strong>{tail['rmse_h']} h</strong>",
            "<strong>67.7%</strong>",
            f"<strong>{tail['recall']}</strong>",
            f"<strong>{zero['mae_h']} h</strong>",
            f"<strong>{no_warning['accuracy']}</strong>",
            f"<small>24 h warning accuracy · {tail['accuracy']}</small>",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.html)

    def test_headline_panel_keeps_provenance_licence_gaps_and_device_only_rule(self):
        for token in (
            "FMCG induction motor",
            "10.5281/zenodo.15637023",
            "CC BY 4.0",
            "10.35784/acs_7299",
            "52df07317901bdb7647c86df479d06c6",
            "BENCHMARK",
            "NOT OUR MOTOR",
            "NOT FIELD-VALIDATED",
            "[NEED: explicit FEMTO-ST licence]",
            "[NEED: explicit XJTU-SY reuse licence]",
            "[NEED: explicit CWRU licence; exact catalogue number]",
            "REMOVE SIMULATOR, ALL FROM DEVICE",
            "NO DATA",
            "AWAITING DATA",
            "NOT REPORTED",
            "below 80%",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.html)

    def test_guide_deck_states_the_same_measured_result(self):
        for token in (
            "141.716 h",
            "204.069 h",
            "67.7%",
            "0.029",
            "69.185/106.164 h",
            "0.686",
            "10.5281/zenodo.15637023",
            "CC BY 4.0",
            "below 80%",
            "BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.guide)

    def test_no_field_validation_claim_is_introduced(self):
        for page, text in (("index", self.html), ("guide", self.guide)):
            for forbidden in (
                "100% on real motor",
                "field-validated RUL complete",
                "hours-to-failure for our motor",
                "operator-approved alarm threshold of 24 h",
            ):
                with self.subTest(page=page, forbidden=forbidden):
                    self.assertNotIn(forbidden, text)


class CwruDiagnosisDisplayTest(unittest.TestCase):
    """The headline real-motor diagnosis panel quotes its committed report."""

    @classmethod
    def setUpClass(cls):
        with open(DASHBOARD, encoding="utf-8") as handle:
            cls.html = handle.read()
        with open(PAGES["guide"], encoding="utf-8") as handle:
            cls.guide = handle.read()
        with open(CWRU_REPORT, encoding="utf-8") as handle:
            cls.report = json.load(handle)

    def test_headline_numbers_match_the_committed_report(self):
        metrics = self.report["metrics"]
        baseline = self.report["majority_class_baseline"]
        data = self.report["data"]
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertEqual(baseline["accuracy"], 0.4004)
        self.assertGreater(metrics["accuracy"], 0.80)
        for expected in (
            f"<strong>{metrics['accuracy']:.3f}</strong>",
            f"<strong>{baseline['accuracy']}</strong>",
            "<strong>1,039</strong>",
            f"<strong>{data['n_folds']}</strong>",
            "<small>four-class accuracy · 100.0%</small>",
            "<small>majority baseline · 40.04%</small>",
            "<small>windows · 150 contiguous blocks</small>",
            "<small>sample-disjoint folds</small>",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.html)

    def test_panel_keeps_scope_licence_gap_and_device_only_rule(self):
        for token in (
            "CWRU induction motor",
            "2 hp Reliance Electric",
            "four bearing-condition classes",
            "not</b> the deployed runtime classes",
            "not</b> RUL",
            "NOT FIELD-VALIDATED",
            "[NEED: explicit CWRU licence; exact catalogue number]",
            "ml/diagnosis_cwru_report.json",
            "REMOVE SIMULATOR, ALL FROM DEVICE",
            "NO DATA",
            "AWAITING DATA",
            "NOT REPORTED",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.html)

    def test_guide_deck_states_the_same_measured_result(self):
        for token in (
            "1.000",
            "100.0%",
            "0.4004",
            "40.04%",
            "1,039",
            "sample-disjoint",
            "CWRU induction-motor diagnosis",
            "BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.guide)

    def test_no_real_motor_or_field_validation_claim_is_introduced(self):
        for page, text in (("index", self.html), ("guide", self.guide)):
            for forbidden in (
                "100% on our motor",
                "field-validated RUL complete",
                "hours-to-failure for our motor",
            ):
                with self.subTest(page=page, forbidden=forbidden):
                    self.assertNotIn(forbidden, text)


class CmapssRulWarningDisplayTest(unittest.TestCase):
    """The >80% RUL panel is labelled as a simulated short-horizon benchmark."""

    @classmethod
    def setUpClass(cls):
        with open(DASHBOARD, encoding="utf-8") as handle:
            cls.html = handle.read()
        with open(PAGES["guide"], encoding="utf-8") as handle:
            cls.guide = handle.read()
        with open(CMAPSS_REPORT, encoding="utf-8") as handle:
            cls.report = json.load(handle)

    def test_dashboard_numbers_match_the_committed_report(self):
        last = self.report["official_test_last_cycle"]
        cv = self.report["grouped_unit_cv"]
        self.assertGreater(last["accuracy"], 0.80)
        self.assertGreater(cv["mean_accuracy"], 0.80)
        for expected in (
            "<strong>94.0%</strong>",
            "<strong>75.0%</strong>",
            f"<small>last-cycle warning accuracy · {last['accuracy']:.3f}</small>",
            f"<small>majority baseline · {last['majority_baseline']:.3f}</small>",
            f"<strong>{last['precision']}</strong>",
            f"<small>warning recall · {last['positive_count']} positive units</small>",
            "<strong>97.05%</strong>",
            f"<small>mean unit-disjoint CV accuracy · {cv['mean_accuracy']}</small>",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.html)

    def test_scope_and_provenance_are_visible_on_both_pages(self):
        for token in (
            "NASA C-MAPSS FD001",
            "SIMULATED TURBOFAN",
            "NOT OUR MOTOR",
            "NOT FIELD-VALIDATED",
            "30-cycle RUL warning",
            "not</b> an induction-motor result",
            "10.5281/zenodo.15346912",
            "ml/rul_cmapss_warning_report.json",
            "below 80%",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.html)
        for token in (
            "C-MAPSS FD001",
            "0.940",
            "0.750",
            "SIMULATED TURBOFAN",
            "NOT OUR MOTOR",
            "NOT FIELD-VALIDATED",
        ):
            with self.subTest(page="guide", token=token):
                self.assertIn(token, self.guide)

    def test_no_field_or_runtime_claim_is_introduced(self):
        for page, text in (("index", self.html), ("guide", self.guide)):
            for forbidden in (
                "field-validated RUL complete",
                "hours-to-failure for our motor",
                "operator-approved alarm threshold of 30 cycles",
            ):
                with self.subTest(page=page, forbidden=forbidden):
                    self.assertNotIn(forbidden, text)


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
