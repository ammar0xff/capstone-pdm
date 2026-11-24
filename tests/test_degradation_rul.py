"""Checks the offline, threshold-based degradation estimator.

This is a documented degradation model, not a field-validated RUL predictor.
Every result must say so, and the threshold must come from the operator.
"""

import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ml"))

from degradation_rul import estimate_rul  # noqa: E402


class DegradationRulTest(unittest.TestCase):
    def test_linear_estimate_from_known_trend(self):
        result = estimate_rul([(0, 1.0), (1, 2.0), (2, 3.0), (3, 4.0)], threshold=6.0)
        self.assertEqual(result["status"], "estimated")
        self.assertAlmostEqual(result["slope"], 1.0)
        self.assertAlmostEqual(result["intercept"], 1.0)
        self.assertAlmostEqual(result["estimated_cross_time"], 5.0)
        self.assertAlmostEqual(result["rul_seconds"], 2.0)

    def test_exponential_estimate_from_known_trend(self):
        history = [(t, math.exp(t)) for t in range(4)]
        result = estimate_rul(history, threshold=100.0, model="exponential")
        self.assertEqual(result["status"], "estimated")
        self.assertAlmostEqual(result["slope"], 1.0)
        self.assertAlmostEqual(result["intercept"], 0.0)
        expected_cross = math.log(100.0)
        self.assertAlmostEqual(result["estimated_cross_time"], expected_cross)
        self.assertAlmostEqual(result["rul_seconds"], expected_cross - 3.0)

    def test_threshold_already_reached_gives_zero(self):
        result = estimate_rul([(0, 1.0), (1, 2.0), (2, 3.0)], threshold=2.0)
        self.assertEqual(result["status"], "threshold_reached")
        self.assertEqual(result["rul_seconds"], 0.0)

    def test_flat_or_decreasing_trend_gives_no_estimate(self):
        for history in ([(0, 2.0), (1, 2.0), (2, 2.0)], [(0, 3.0), (1, 2.0), (2, 1.0)]):
            with self.subTest(history=history):
                result = estimate_rul(history, threshold=10.0)
                self.assertEqual(result["status"], "no_increasing_trend")
                self.assertIsNone(result["rul_seconds"])
                self.assertIsNone(result["estimated_cross_time"])

    def test_every_result_is_labelled_as_not_field_validated(self):
        for result in (
            estimate_rul([(0, 1.0), (1, 2.0), (2, 3.0)], threshold=6.0),
            estimate_rul([(0, 1.0), (1, 2.0), (2, 3.0)], threshold=2.0),
            estimate_rul([(0, 2.0), (1, 2.0), (2, 2.0)], threshold=6.0),
        ):
            with self.subTest(status=result["status"]):
                self.assertIn("not field-validated", result["label"])
                self.assertEqual(result["threshold_source"], "operator-supplied")

    def test_rejects_empty_or_short_history(self):
        for history in ([], [(0, 1.0), (1, 2.0)]):
            with self.subTest(history=history):
                with self.assertRaises(ValueError):
                    estimate_rul(history, threshold=6.0)

    def test_rejects_non_finite_values(self):
        with self.assertRaises(ValueError):
            estimate_rul([(0, 1.0), (1, math.nan), (2, 3.0)], threshold=6.0)
        with self.assertRaises(ValueError):
            estimate_rul([(0, 1.0), (1, 2.0), (math.inf, 3.0)], threshold=6.0)

    def test_rejects_duplicate_or_backwards_timestamps(self):
        for history in (
            [(0, 1.0), (1, 2.0), (1, 3.0)],
            [(0, 1.0), (2, 2.0), (1, 3.0)],
        ):
            with self.subTest(history=history):
                with self.assertRaises(ValueError):
                    estimate_rul(history, threshold=6.0)

    def test_rejects_non_finite_threshold(self):
        with self.assertRaises(ValueError):
            estimate_rul([(0, 1.0), (1, 2.0), (2, 3.0)], threshold=math.nan)

    def test_exponential_rejects_nonpositive_values_and_threshold(self):
        with self.assertRaises(ValueError):
            estimate_rul(
                [(0, 1.0), (1, 0.0), (2, 3.0)], threshold=10.0, model="exponential"
            )
        with self.assertRaises(ValueError):
            estimate_rul(
                [(0, 1.0), (1, 2.0), (2, 3.0)], threshold=0.0, model="exponential"
            )

    def test_unknown_model_rejected(self):
        with self.assertRaises(ValueError):
            estimate_rul(
                [(0, 1.0), (1, 2.0), (2, 3.0)], threshold=6.0, model="quadratic"
            )

    def test_cli_reads_named_csv_columns_and_emits_json(self):
        script = os.path.join(ROOT, "ml", "degradation_rul.py")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "history.csv")
            with open(path, "w") as f:
                f.write("unix_time,sound_rms\n")
                f.write("0,1\n1,2\n2,3\n3,4\n")
            proc = subprocess.run(
                [
                    sys.executable,
                    script,
                    "--history",
                    path,
                    "--time-column",
                    "unix_time",
                    "--value-column",
                    "sound_rms",
                    "--threshold",
                    "6",
                ],
                capture_output=True,
                text=True,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertAlmostEqual(result["rul_seconds"], 2.0)
        self.assertIn("not field-validated", result["label"])

    def test_cli_rejects_missing_column(self):
        script = os.path.join(ROOT, "ml", "degradation_rul.py")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "history.csv")
            with open(path, "w") as f:
                f.write("timestamp,value\n0,1\n1,2\n2,3\n")
            proc = subprocess.run(
                [sys.executable, script, "--history", path, "--threshold", "6"],
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("ERROR", proc.stderr)


if __name__ == "__main__":
    unittest.main()
