"""Checks the labelled XJTU-SY public-bearing RUL benchmark.

The small CSVs here are generated only to prove the data contract, causal
prediction and honest reporting. They are not presented as measurements from
our motor or from the XJTU-SY experiment.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ml"))

import rul_xjtu_sy as xjtu  # noqa: E402

SCRIPT = os.path.join(ROOT, "ml", "rul_xjtu_sy.py")
VENDORED = Path(ROOT) / "data" / "xjtu_sy_mendeley"


def _write_csv(path: str, rows: int, offset: float = 0.0) -> None:
    rng = np.random.default_rng(rows + int(offset))
    snapshots = np.arange(rows, dtype=float) + offset
    features = np.column_stack(
        [
            rng.uniform(0.1, 1.0, rows),
            rng.uniform(0.05, 0.5, rows),
            rng.uniform(0.5, 5.0, rows),
            rng.uniform(-1.0, 1.0, (rows, xjtu.N_FEATURES - 3)),
        ]
    )
    data = np.column_stack((snapshots, features))
    header = ",".join(
        ["snapshot"] + [f"feature_{i:02d}" for i in range(1, xjtu.N_FEATURES + 1)]
    )
    np.savetxt(path, data, delimiter=",", header=header, comments="")


class XjtuDataContractTest(unittest.TestCase):
    def test_load_bearing_builds_finite_health_from_54_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bearing1.csv")
            _write_csv(path, 20)
            bearing = xjtu.load_bearing(Path(path))

        self.assertEqual(bearing.run_id, "bearing1")
        self.assertEqual(bearing.snapshots.shape, (20,))
        self.assertEqual(bearing.health.shape, (20,))
        self.assertTrue(np.isfinite(bearing.health).all())
        self.assertEqual(bearing.duration_min, 19.0)

    def test_bad_shapes_non_finite_and_time_order_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            valid = os.path.join(tmp, "bearing1.csv")
            _write_csv(valid, 20)
            data = np.loadtxt(valid, delimiter=",", skiprows=1)
            cases = {
                "short": data[:5, :],
                "wrong-width": data[:, :-1],
            }
            for name, array in cases.items():
                path = os.path.join(tmp, f"{name}.csv")
                np.savetxt(path, array, delimiter=",", header="x", comments="")
                with self.subTest(case=name):
                    with self.assertRaises(ValueError):
                        xjtu.load_bearing(Path(path))
            broken = np.array(data, copy=True)
            broken[3, 2] = np.nan
            nan_path = os.path.join(tmp, "nan.csv")
            np.savetxt(nan_path, broken, delimiter=",", header="x", comments="")
            with self.subTest(case="nan"):
                with self.assertRaises(ValueError):
                    xjtu.load_bearing(Path(nan_path))
            broken = np.array(data, copy=True)
            broken[4, 0] = broken[3, 0]
            time_path = os.path.join(tmp, "time.csv")
            np.savetxt(time_path, broken, delimiter=",", header="x", comments="")
            with self.subTest(case="repeated-time"):
                with self.assertRaises(ValueError):
                    xjtu.load_bearing(Path(time_path))

    def test_prediction_never_reads_the_held_bearings_future(self):
        health = np.linspace(0.0, 2.0, 40)
        before = xjtu.predict_rul(health, 20, threshold=1.8, naive=30.0)
        extended = np.concatenate((health, np.full(20, 100.0)))
        after = xjtu.predict_rul(extended, 20, threshold=1.8, naive=30.0)
        self.assertEqual(before, after)
        self.assertGreaterEqual(before, 0.0)
        self.assertLessEqual(before, 60.0)

    def test_non_positive_trend_falls_back_to_naive_not_a_guess(self):
        flat = np.full(40, 0.5)
        self.assertEqual(xjtu.predict_rul(flat, 30, threshold=2.0, naive=12.5), 12.5)


class XjtuEvaluationTest(unittest.TestCase):
    def test_evaluate_requires_two_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_csv(os.path.join(tmp, "bearing1.csv"), 20)
            with self.assertRaises(ValueError) as raised:
                xjtu.evaluate(tmp)

        self.assertIn("at least two", str(raised.exception))

    def test_evaluate_is_bearing_disjoint_and_honestly_labelled(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_csv(os.path.join(tmp, "bearing1.csv"), 30)
            _write_csv(os.path.join(tmp, "bearing2.csv"), 40, offset=0.0)
            report = xjtu.evaluate(tmp)

        self.assertEqual(report["status"], "benchmark_complete")
        self.assertEqual(
            report["label"], "BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED"
        )
        self.assertIs(report["source"]["our_motor"], False)
        self.assertIs(report["source"]["operator_confirmed_failure"], False)
        self.assertIs(report["source"]["field_validation"], False)
        self.assertIsNone(report["readiness"]["hours_to_failure_for_our_rig"])
        self.assertEqual(
            report["method"]["validation"],
            "leave-one-bearing-out; last 20% of the held bearing's snapshots",
        )
        self.assertEqual(set(report["per_bearing"]), {"bearing1", "bearing2"})
        self.assertGreater(report["tail_windows"]["n_windows"], 0)
        self.assertTrue(report["source"]["derived_data_license"] == "CC BY 4.0")

    def test_tail_fraction_is_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write_csv(os.path.join(tmp, "bearing1.csv"), 20)
            _write_csv(os.path.join(tmp, "bearing2.csv"), 20)
            for bad in (0.0, -0.1, 1.1):
                with self.subTest(fraction=bad):
                    with self.assertRaises(ValueError):
                        xjtu.evaluate(tmp, tail_fraction=bad)


class XjtuEvidenceTest(unittest.TestCase):
    def test_vendored_files_match_recorded_hashes(self):
        import hashlib

        manifest = json.loads((VENDORED / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest), 15)
        for name, meta in sorted(manifest.items()):
            with self.subTest(file=name):
                mat = VENDORED / "features" / name
                csv = VENDORED / "csv" / meta["csv"]
                self.assertTrue(csv.exists(), f"missing derived CSV: {csv}")
                self.assertEqual(
                    hashlib.sha256(csv.read_bytes()).hexdigest(), meta["csv_sha256"]
                )
                if mat.exists():
                    self.assertEqual(
                        hashlib.sha256(mat.read_bytes()).hexdigest(), meta["sha256"]
                    )

    def test_report_and_provenance_doc_keep_the_label_and_gaps(self):
        report = json.loads(
            (Path(ROOT) / "ml" / "rul_xjtu_sy_report.json").read_text(encoding="utf-8")
        )
        doc = (VENDORED / "README.md").read_text(encoding="utf-8")
        evidence = (Path(ROOT) / "docs" / "DATA_PROVENANCE_LICENSES.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            report["label"], "BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED"
        )
        for token in ("10.17632/mpn45f4gxc.1", "CC BY 4.0", "not available", "[NEED:"):
            with self.subTest(doc_token=token):
                self.assertIn(token, doc)
        for token in (
            "10.1109/TR.2018.2882682",
            "2 hp Reliance Electric motor",
            "explicit FEMTO-ST dataset licence",
            "explicit CWRU dataset reuse licence",
            "exact Reliance Electric catalogue number",
        ):
            with self.subTest(evidence_token=token):
                self.assertIn(token, evidence)

    def test_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "report.json")
            proc = subprocess.run(
                [sys.executable, SCRIPT, "--report", out],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            written = json.loads(Path(out).read_text(encoding="utf-8"))
            printed = json.loads(proc.stdout)
            self.assertEqual(written, printed)
            self.assertEqual(written["data"]["n_bearings"], 15)


if __name__ == "__main__":
    unittest.main()
