"""Checks the labelled public FMCG induction-motor RUL benchmark.

Synthetic CSVs here only prove the data contract and causality. The vendored
Zenodo CSV is never presented as a measurement from, or a field validation of,
the capstone motor.
"""

import csv
import datetime as dt
import hashlib
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

import rul_fmcg as fmcg  # noqa: E402

SCRIPT = os.path.join(ROOT, "ml", "rul_fmcg.py")
VENDORED = Path(ROOT) / "data" / "fmcg_induction_rul"
REPORT_PATH = Path(ROOT) / "ml" / "rul_fmcg_report.json"
LABEL = "OFFLINE RESULT / NAMED PUBLIC DATASET"
SOURCE_COLUMNS = (
    "Date",
    "Time",
    "RMSVelX (mm/s)",
    "RMSVelY (mm/s)",
    "RMSVelZ (mm/s)",
    "Temperature (°C)",
    "ElectricalStatorFrequency (Hz)",
    "Rotation Speed (rpm)",
    "Slip Frequency (Hz)",
    "Torque (Nm)",
    "AccelerationGeometricMean (mm/s²)",
    "BearingState",
    "MisalignmentState",
    "UnbalanceState",
    "VelocityGeometricMean (mm/s)",
    "RUL (jam)",
    "Downtime",
)
EXPECTED_METRICS = {
    "n_runs": 4,
    "n_rows": 1639,
    "tail_n_rows": 334,
    "mae_h": 141.716,
    "rmse_h": 204.069,
    "warning_accuracy": 0.677,
    "warning_recall": 0.029,
    "zero_mae_h": 69.185,
    "zero_rmse_h": 106.164,
    "median_mae_h": 254.993,
    "median_rmse_h": 263.054,
    "no_warning_accuracy": 0.686,
}


def _write_csv(
    directory: str,
    *,
    filename: str = "raw.csv",
    rows_per_run: int = 120,
    start_rul: float = 100.0,
    mutate=None,
) -> str:
    """Write deterministic source-shaped runs; mutate gets each run's rows."""

    path = os.path.join(directory, filename)
    all_rows = []
    for run_index in range(4):
        base = dt.datetime(2024, 1, 1) + dt.timedelta(days=10 * run_index)
        run_rows = []
        for row_index in range(rows_per_run):
            stamp = base + dt.timedelta(hours=1 + row_index)
            rul = max(0.0, start_rul - row_index)
            run_rows.append(
                {
                    "Date": stamp.date().isoformat(),
                    "Time": f"1970-01-01 {stamp.hour:02d}:{stamp.minute:02d}:{stamp.second:02d}",
                    "RMSVelX (mm/s)": 0.1 + 0.001 * row_index,
                    "RMSVelY (mm/s)": 0.2 + 0.002 * row_index,
                    "RMSVelZ (mm/s)": 0.3 + 0.003 * row_index,
                    "Temperature (°C)": 30.0 + 0.05 * row_index,
                    "ElectricalStatorFrequency (Hz)": 50.0,
                    "Rotation Speed (rpm)": 2980.0,
                    "Slip Frequency (Hz)": 0.2,
                    "Torque (Nm)": 400.0,
                    "AccelerationGeometricMean (mm/s²)": 0.5,
                    "BearingState": 1.0,
                    "MisalignmentState": 2.0,
                    "UnbalanceState": 3.0,
                    "VelocityGeometricMean (mm/s)": 0.4,
                    "RUL (jam)": rul,
                    "Downtime": "YES" if rul == 0.0 else "NO",
                }
            )
        if mutate is not None:
            mutate(run_rows, run_index)
        all_rows.extend(run_rows)
    with open(path, "w", newline="", encoding="cp1252") as handle:
        writer = csv.DictWriter(handle, fieldnames=SOURCE_COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(all_rows)
    return path


class FmcgDataContractTest(unittest.TestCase):
    def test_load_runs_keeps_only_complete_run_to_zero_trajectories(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = fmcg.load_runs(_write_csv(tmp))

        self.assertEqual(list(runs), ["run_01", "run_02", "run_03", "run_04"])
        seen_rows = []
        for run_id, run in runs.items():
            self.assertEqual(run.run_id, run_id)
            self.assertEqual(run.rul_h.size, 120)
            self.assertEqual(float(run.rul_h[-1]), 0.0)
            self.assertEqual(float(run.rul_h[0]), 100.0)
            self.assertEqual(run.features.shape, (120, 1 + 13 * 2))
            self.assertTrue(np.isfinite(run.features).all())
            self.assertTrue(
                all(
                    later > earlier
                    for earlier, later in zip(run.timestamps, run.timestamps[1:])
                )
            )
            seen_rows.extend(run.source_rows)
        self.assertEqual(len(seen_rows), len(set(seen_rows)))

    def test_bad_labels_and_missing_columns_are_rejected(self):
        def negative_rul(rows, _):
            rows[-1]["RUL (jam)"] = -1.0

        def nan_rul(rows, _):
            rows[5]["RUL (jam)"] = "nan"

        def bad_downtime(rows, _):
            rows[5]["Downtime"] = "MAYBE"

        def flat_rul(rows, _):
            for row in rows:
                row["RUL (jam)"] = 100.0

        def repeated_time(rows, _):
            rows[1]["Time"] = rows[0]["Time"]

        with tempfile.TemporaryDirectory() as tmp:
            cases = {
                "negative": negative_rul,
                "nan": nan_rul,
                "downtime": bad_downtime,
                "flat": flat_rul,
                "unordered": repeated_time,
            }
            for name, mutate in cases.items():
                path = _write_csv(tmp, filename=f"{name}.csv", mutate=mutate)
                with self.subTest(case=name):
                    with self.assertRaises(ValueError):
                        fmcg.load_runs(path)
            missing = os.path.join(tmp, "missing.csv")
            with open(
                _write_csv(tmp, filename="source.csv"), encoding="cp1252"
            ) as handle:
                rows = list(csv.DictReader(handle, delimiter=";"))
            with open(missing, "w", newline="", encoding="cp1252") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[name for name in SOURCE_COLUMNS if name != "RUL (jam)"],
                    delimiter=";",
                )
                writer.writeheader()
                writer.writerows(
                    {key: value for key, value in row.items() if key != "RUL (jam)"}
                    for row in rows
                )
            with self.assertRaises(ValueError):
                fmcg.load_runs(missing)

    def test_features_never_read_a_future_row(self):
        values = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0], [7.0, 8.0]])
        stamps = tuple(
            dt.datetime(2024, 1, 1) + dt.timedelta(hours=index)
            for index in range(values.shape[0])
        )
        before = fmcg._build_features(values[:3], stamps[:3])
        extended_values = np.vstack((values, np.full((2, 2), 999.0)))
        extended_stamps = stamps + tuple(
            dt.datetime(2024, 1, 2) + dt.timedelta(hours=index) for index in range(2)
        )
        after = fmcg._build_features(extended_values, extended_stamps)
        np.testing.assert_allclose(before, after[:3])
        self.assertLess(after[3, 1], 999.0)


class FmcgEvaluationTest(unittest.TestCase):
    def test_evaluate_is_run_disjoint_and_honestly_labelled(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = fmcg.evaluate(_write_csv(tmp))

        self.assertEqual(report["status"], "benchmark_complete")
        self.assertEqual(report["label"], LABEL)
        self.assertIs(report["source"]["our_motor"], False)
        self.assertIs(report["source"]["operator_confirmed_failure"], False)
        self.assertIs(report["source"]["field_validation"], False)
        self.assertIsNone(report["readiness"]["hours_to_failure_for_our_rig"])
        self.assertEqual(
            report["method"]["validation"],
            "leave-one-run-out; last 20% of the held run's rows",
        )
        self.assertTrue(report["method"]["causal"])
        self.assertEqual(
            set(report["per_run"]), {"run_01", "run_02", "run_03", "run_04"}
        )
        for held_id, detail in report["per_run"].items():
            with self.subTest(held=held_id):
                self.assertNotIn(held_id, detail["train_runs"])
                self.assertEqual(len(detail["train_runs"]), 3)
                self.assertEqual(detail["tail_rows"], 25)
                self.assertEqual(detail["actual_last_rul_h"], 0.0)
        tail = report["tail_windows"]
        self.assertEqual(tail["n_rows"], 100)
        self.assertEqual(
            tail["true_positive"]
            + tail["false_positive"]
            + tail["false_negative"]
            + tail["true_negative"],
            tail["n_rows"],
        )

    def test_tail_fraction_and_warning_threshold_are_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_csv(tmp)
            for bad in (0.0, -0.1, 1.1):
                with self.subTest(fraction=bad):
                    with self.assertRaises(ValueError):
                        fmcg.evaluate(path, tail_fraction=bad)
            for bad in (0.0, -24.0):
                with self.subTest(threshold=bad):
                    with self.assertRaises(ValueError):
                        fmcg.evaluate(path, warning_threshold_h=bad)


class FmcgEvidenceTest(unittest.TestCase):
    def test_vendored_csv_matches_manifest_and_source_hash(self):
        manifest = json.loads((VENDORED / "manifest.json").read_text(encoding="utf-8"))
        raw_path = VENDORED / "raw.csv"
        payload = raw_path.read_bytes()
        self.assertEqual(hashlib.md5(payload).hexdigest(), manifest["file"]["md5"])
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(), manifest["file"]["sha256"]
        )
        self.assertEqual(manifest["file"]["md5"], fmcg.SOURCE_MD5)
        self.assertEqual(manifest["dataset"]["license"], fmcg.LICENSE)
        self.assertEqual(tuple(manifest["source_columns"]), SOURCE_COLUMNS)
        self.assertEqual(
            [run["rows"] for run in manifest["run_selection"]["selected_runs"]],
            [582, 312, 552, 193],
        )

    def test_committed_report_matches_reproduction_and_measured_numbers(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(report, fmcg.evaluate(fmcg.DEFAULT_CSV))
        tail = report["tail_windows"]
        self.assertEqual(tail["n_rows"], EXPECTED_METRICS["tail_n_rows"])
        self.assertEqual(tail["mae_h"], EXPECTED_METRICS["mae_h"])
        self.assertEqual(tail["rmse_h"], EXPECTED_METRICS["rmse_h"])
        self.assertEqual(tail["accuracy"], EXPECTED_METRICS["warning_accuracy"])
        self.assertEqual(tail["recall"], EXPECTED_METRICS["warning_recall"])
        self.assertEqual(
            report["constant_zero_baseline_tail_windows"]["mae_h"],
            EXPECTED_METRICS["zero_mae_h"],
        )
        self.assertEqual(
            report["constant_zero_baseline_tail_windows"]["rmse_h"],
            EXPECTED_METRICS["zero_rmse_h"],
        )
        self.assertEqual(
            report["constant_median_baseline_tail_windows"]["mae_h"],
            EXPECTED_METRICS["median_mae_h"],
        )
        self.assertEqual(
            report["constant_median_baseline_tail_windows"]["rmse_h"],
            EXPECTED_METRICS["median_rmse_h"],
        )
        self.assertEqual(
            report["constant_no_warning_baseline_tail_windows"]["accuracy"],
            EXPECTED_METRICS["no_warning_accuracy"],
        )
        self.assertEqual(report["data"]["n_runs"], EXPECTED_METRICS["n_runs"])
        self.assertEqual(report["data"]["n_rows"], EXPECTED_METRICS["n_rows"])
        self.assertLess(tail["accuracy"], 0.80)
        self.assertLess(
            tail["accuracy"],
            report["constant_no_warning_baseline_tail_windows"]["accuracy"],
        )

    def test_docs_keep_the_real_result_and_do_not_promote_it(self):
        readme = (Path(ROOT) / "README.md").read_text(encoding="utf-8")
        ai_report = (Path(ROOT) / "ml" / "ai_report.md").read_text(encoding="utf-8")
        data_readme = (VENDORED / "README.md").read_text(encoding="utf-8")
        for text, name in (
            (readme, "README.md"),
            (ai_report, "ml/ai_report.md"),
            (data_readme, "data/fmcg_induction_rul/README.md"),
        ):
            with self.subTest(doc=name):
                self.assertIn("10.5281/zenodo.15637023", text)
                self.assertIn("141.716", text)
                self.assertIn("204.069", text)
                self.assertIn("67.7%", text)
                self.assertIn("OFFLINE RESULT / NAMED PUBLIC DATASET", text)
                self.assertNotIn("100% on real motor", text)
                self.assertNotIn("field-validated RUL complete", text)
        for token in (
            "[NEED: explicit FEMTO-ST licence]",
            "[NEED: explicit XJTU-SY reuse licence]",
            "[NEED: explicit CWRU licence; exact catalogue number]",
        ):
            self.assertIn(token, data_readme)

    def test_cli_writes_the_same_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "report.json")
            proc = subprocess.run(
                [sys.executable, SCRIPT, "--report", out],
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            written = json.loads(Path(out).read_text(encoding="utf-8"))
            self.assertEqual(written, json.loads(proc.stdout))
            self.assertEqual(
                written, json.loads(REPORT_PATH.read_text(encoding="utf-8"))
            )


if __name__ == "__main__":
    unittest.main()
