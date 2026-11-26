"""Checks the honest >80% C-MAPSS RUL warning benchmark.

FD001 is a public simulated turbofan benchmark with explicit RUL labels. It is
not field validation and not the deployed runtime
classifier. The tests guard provenance, leakage, grouped folds, the measured
>80% result and its majority baseline without relabelling the FMCG result.
"""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ml"))

import rul_cmapss_warning as warning  # noqa: E402

RAW_DIR = os.path.join(ROOT, "data", "cmapss")
REPORT_PATH = os.path.join(ROOT, "ml", "rul_cmapss_warning_report.json")
FILE_HASHES = {
    "train_FD001.txt": "259f340bac32ce6fa8894815600fa757",
    "test_FD001.txt": "62316d1dd70f88a9a43a1e2690765437",
    "RUL_FD001.txt": "8f4a8b3d2692b2f7d8e72b344927bf4b",
}


class CmapssWarningProvenanceTest(unittest.TestCase):
    def test_raw_files_match_documented_hashes(self):
        for name, expected in FILE_HASHES.items():
            with self.subTest(file=name):
                with open(os.path.join(RAW_DIR, name), "rb") as handle:
                    self.assertEqual(hashlib.md5(handle.read()).hexdigest(), expected)

    def test_source_and_scope_are_labelled(self):
        self.assertEqual(warning.WARNING_HORIZON_CYCLES, 30)
        self.assertEqual(warning.SOURCE_DOI, "10.5281/zenodo.15346912")
        self.assertEqual(warning.SOURCE_LICENSE, "CC BY 4.0")
        self.assertIn("OFFLINE", warning.LABEL)
        self.assertIn("OFFLINE", warning.LABEL)
        self.assertIn("SIMULATED", warning.LABEL)

    def test_test_rul_reconstruction_uses_the_official_last_cycle_labels(self):
        # Two test units: both are observed at cycles 10 and 11. Their published
        # final-cycle RULs are 20 and 7, so earlier rows add the visible cycles.
        test = np.array(
            [
                [1, 10, 0, 0, 0],
                [1, 11, 0, 0, 0],
                [2, 10, 0, 0, 0],
                [2, 11, 0, 0, 0],
            ],
            dtype=float,
        )
        true_rul = np.array([[20.0], [7.0]])
        values = warning.test_rul_by_row(test, true_rul)
        np.testing.assert_allclose(values, [21.0, 20.0, 8.0, 7.0])


class CmapssWarningBenchmarkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = warning.evaluate(RAW_DIR)

    def test_committed_report_is_reproduced_exactly(self):
        with open(REPORT_PATH, encoding="utf-8") as handle:
            committed = json.load(handle)
        self.assertEqual(committed, self.report)

    def test_official_last_cycle_result_is_above_80_with_baseline(self):
        result = self.report["official_test_last_cycle"]
        self.assertEqual(result["n"], 100)
        self.assertEqual(result["positive_count"], 25)
        self.assertGreater(result["accuracy"], 0.80)
        self.assertGreater(result["accuracy"], result["majority_baseline"])
        self.assertGreater(result["precision"], 0.80)
        self.assertGreater(result["recall"], 0.70)
        self.assertLessEqual(result["accuracy"], 1.0)

    def test_grouped_cv_is_unit_disjoint_and_reported(self):
        cv = self.report["grouped_unit_cv"]
        self.assertEqual(cv["n_folds"], 5)
        seen = []
        for fold in cv["per_fold"]:
            seen.extend(fold["units"])
        self.assertEqual(sorted(seen), list(range(1, 101)))
        self.assertGreater(cv["mean_accuracy"], 0.80)
        for fold in cv["per_fold"]:
            with self.subTest(fold=fold["fold"]):
                self.assertGreater(fold["accuracy"], 0.80)

    def test_report_keeps_fmcg_below_80_result_visible(self):
        with open(
            os.path.join(ROOT, "ml", "rul_fmcg_report.json"), encoding="utf-8"
        ) as handle:
            fmcg = json.load(handle)
        self.assertEqual(fmcg["tail_windows"]["accuracy"], 0.677)
        self.assertLess(fmcg["tail_windows"]["accuracy"], 0.80)
        self.assertIs(self.report["readiness"]["fmcg_result_unchanged"], True)

    def test_report_is_not_a_field_or_runtime_claim(self):
        readiness = self.report["readiness"]
        self.assertIs(readiness["not_our_motor"], True)
        self.assertIs(readiness["not_field_validated"], True)
        self.assertIs(readiness["field_validated_rul"], False)
        self.assertIs(readiness["runtime_or_dashboard_claim_changed"], False)
        self.assertEqual(self.report["status"], "rul_warning_benchmark_complete")


class CmapssWarningCliTest(unittest.TestCase):
    def test_cli_writes_json_report(self):
        script = os.path.join(ROOT, "ml", "rul_cmapss_warning.py")
        with tempfile.TemporaryDirectory() as tmp:
            report_path = os.path.join(tmp, "report.json")
            proc = subprocess.run(
                [
                    sys.executable,
                    script,
                    "--raw-dir",
                    RAW_DIR,
                    "--report",
                    report_path,
                ],
                capture_output=True,
                text=True,
                timeout=180,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(report_path, encoding="utf-8") as handle:
                written = json.load(handle)
        printed = json.loads(proc.stdout)
        self.assertEqual(written, printed)
        self.assertEqual(written["status"], "rul_warning_benchmark_complete")
        self.assertGreater(written["official_test_last_cycle"]["accuracy"], 0.80)

    def test_cli_rejects_missing_raw_files(self):
        script = os.path.join(ROOT, "ml", "rul_cmapss_warning.py")
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [sys.executable, script, "--raw-dir", tmp],
                capture_output=True,
                text=True,
                timeout=30,
            )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("ERROR", proc.stderr)


if __name__ == "__main__":
    unittest.main()
