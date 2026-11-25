"""Checks the target-rig run-to-failure RUL readiness path.

The rig has not produced a failure-labelled run-to-failure series yet, so these
tests use a small generated CSV only to prove the data contract, causal feature
construction, run-disjoint evaluation and honest reporting. They do not present
the generated values as measurements from our motor.
"""

import csv
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ml"))

import rul_from_rig as rig  # noqa: E402

SCRIPT = os.path.join(ROOT, "ml", "rul_from_rig.py")


def _row_values(run_index: int, row_index: int) -> dict[str, float]:
    db = 50.0 + 0.5 * row_index + 2.0 * run_index
    return {
        "rms_dyn": 0.05 + 0.002 * row_index + 0.005 * run_index,
        "peak_dyn": 0.20 + 0.004 * row_index + 0.01 * run_index,
        "crest_factor": 2.5 + 0.01 * row_index,
        "kurtosis": 3.0 + 0.02 * row_index + 0.05 * run_index,
        "temp_c": 30.0 + 0.1 * row_index + run_index,
        "temp_slope": 0.2 + 0.01 * row_index,
        "sound_rms": 10.0 ** ((db - 120.0) / 20.0),
        "sound_db": db,
        "sound_zcr": 0.05 + 0.001 * row_index,
    }


def _write_runs(
    path: str,
    rows_per_run: int | list[int] = 12,
    n_runs: int = 3,
    include_sound_rms: bool = True,
    include_failure: bool = True,
) -> None:
    counts = (
        [rows_per_run] * n_runs if isinstance(rows_per_run, int) else list(rows_per_run)
    )
    fields = ["run_id", "timestamp"]
    if include_failure:
        fields.append("failure_timestamp")
    fields.extend(name for name in rig.FEATURE_NAMES if name != "sound_rms")
    if include_sound_rms:
        fields.append("sound_rms")

    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for run_index, count in enumerate(counts):
            base = run_index * 1000.0
            last_time = base + (count - 1) * 10.0
            for row_index in range(count):
                values = _row_values(run_index, row_index)
                row = {
                    "run_id": f"run-{run_index + 1}",
                    "timestamp": base + row_index * 10.0,
                }
                if include_failure:
                    row["failure_timestamp"] = last_time
                for name in fields:
                    if name in row:
                        continue
                    row[name] = values[name]
                writer.writerow(row)


def _rewrite_without_column(src: str, dst: str, column: str) -> None:
    with open(src, newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    fields = [name for name in rows[0] if name != column]
    with open(dst, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in fields})


def _mutate_cell(
    src: str, dst: str, run_id: str, row_position: int, column: str, value: str
) -> None:
    with open(src, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    matching = [row for row in rows if row["run_id"] == run_id]
    target = matching[row_position]
    target[column] = value
    with open(dst, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class RigDataContractTest(unittest.TestCase):
    def test_load_runs_builds_causal_labels_and_feature_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "runs.csv")
            _write_runs(path, rows_per_run=12, n_runs=3)
            dataset = rig.load_runs(path, window=4)

        self.assertEqual(dataset.total_rows, 36)
        self.assertEqual(dataset.sound_rms_source, "explicit sound_rms column")
        self.assertEqual(set(dataset.runs), {"run-1", "run-2", "run-3"})
        for run in dataset.runs.values():
            with self.subTest(run=run.run_id):
                self.assertEqual(run.n_rows, 12)
                self.assertEqual(run.features.shape, (9, 27))
                self.assertEqual(run.rul_s[-1], 0.0)
                self.assertTrue(all(a > b for a, b in zip(run.rul_s, run.rul_s[1:])))
                self.assertEqual(run.failure_time_s, run.last_time_s)

    def test_future_rows_do_not_change_past_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = os.path.join(tmp, "base.csv")
            extended = os.path.join(tmp, "extended.csv")
            _write_runs(base, rows_per_run=[10, 10, 10])
            _write_runs(extended, rows_per_run=[11, 10, 10])
            before = rig.load_runs(base, window=4).runs["run-1"]
            after = rig.load_runs(extended, window=4).runs["run-1"]

        self.assertEqual(after.features.shape[0], before.features.shape[0] + 1)
        for index in range(before.features.shape[0]):
            with self.subTest(window=index):
                np.testing.assert_allclose(
                    before.features[index], after.features[index]
                )

    def test_sound_rms_is_derived_when_column_is_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "runs.csv")
            _write_runs(path, include_sound_rms=False)
            dataset = rig.load_runs(path, window=4)

        self.assertIn("derived from sound_db", dataset.sound_rms_source)
        self.assertTrue(
            all(np.isfinite(run.features).all() for run in dataset.runs.values())
        )

    def test_missing_required_column_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "source.csv")
            broken = os.path.join(tmp, "broken.csv")
            _write_runs(source)
            _rewrite_without_column(source, broken, "kurtosis")
            with self.assertRaises(ValueError) as raised:
                rig.load_runs(broken, window=4)

        self.assertIn("kurtosis", str(raised.exception))

    def test_non_finite_feature_and_bad_timestamps_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "source.csv")
            _write_runs(source)
            for label, column, value in (
                ("nan", "rms_dyn", "nan"),
                ("duplicate-time", "timestamp", "1000"),
                ("backwards-time", "timestamp", "900"),
            ):
                with self.subTest(case=label):
                    broken = os.path.join(tmp, f"{label}.csv")
                    _mutate_cell(source, broken, "run-2", 3, column, value)
                    with self.assertRaises(ValueError):
                        rig.load_runs(broken, window=4)

    def test_inconsistent_or_early_failure_endpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "source.csv")
            _write_runs(source)
            for label, value in (("inconsistent", "9999"), ("early", "1000")):
                with self.subTest(case=label):
                    broken = os.path.join(tmp, f"{label}.csv")
                    _mutate_cell(source, broken, "run-1", 2, "failure_timestamp", value)
                    with self.assertRaises(ValueError):
                        rig.load_runs(broken, window=4)

    def test_single_run_is_not_enough_for_disjoint_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "one-run.csv")
            _write_runs(path, n_runs=1)
            with self.assertRaises(ValueError) as raised:
                rig.evaluate(path, window=4)

        self.assertIn("at least two", str(raised.exception))


class RigEvaluationTest(unittest.TestCase):
    def test_evaluate_is_run_disjoint_and_honestly_labelled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "runs.csv")
            _write_runs(path, rows_per_run=12, n_runs=3)
            report = rig.evaluate(path, window=4)

        self.assertEqual(report["status"], "target_rig_evaluation_complete")
        self.assertIn("not field-validated", report["label"])
        self.assertIs(report["source"]["field_validation"], False)
        self.assertEqual(
            report["method"]["validation"],
            "leave-one-run-out; all windows of the held run",
        )
        self.assertEqual(report["data"]["n_runs"], 3)
        self.assertEqual(report["data"]["n_windows"], 27)
        self.assertEqual(set(report["per_run"]), {"run-1", "run-2", "run-3"})
        self.assertFalse(report["readiness"]["runtime_or_dashboard_changed"])

    def test_cli_evaluate_writes_report_and_optional_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "runs.csv")
            report_path = os.path.join(tmp, "report.json")
            model_path = os.path.join(tmp, "model.joblib")
            _write_runs(path)
            proc = subprocess.run(
                [
                    sys.executable,
                    SCRIPT,
                    "--history",
                    path,
                    "--report",
                    report_path,
                    "--window",
                    "4",
                    "--model-out",
                    model_path,
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(report_path, encoding="utf-8") as handle:
                written = json.load(handle)
            printed = json.loads(proc.stdout)
            self.assertTrue(os.path.exists(model_path))

        self.assertEqual(written, printed)
        self.assertIn("not field-validated", written["label"])

    def test_cli_predicts_rul_from_saved_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs_path = os.path.join(tmp, "runs.csv")
            model_path = os.path.join(tmp, "model.joblib")
            current_path = os.path.join(tmp, "current.csv")
            _write_runs(runs_path)
            fit = subprocess.run(
                [
                    sys.executable,
                    SCRIPT,
                    "--history",
                    runs_path,
                    "--report",
                    os.path.join(tmp, "unused.json"),
                    "--window",
                    "4",
                    "--model-out",
                    model_path,
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(fit.returncode, 0, fit.stderr)
            _write_runs(current_path, n_runs=1, include_failure=False)
            proc = subprocess.run(
                [
                    sys.executable,
                    SCRIPT,
                    "--mode",
                    "predict",
                    "--model",
                    model_path,
                    "--history",
                    current_path,
                    "--window",
                    "4",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            result = json.loads(proc.stdout)

        self.assertEqual(result["status"], "prediction_complete")
        self.assertTrue(math.isfinite(result["rul_seconds"]))
        self.assertGreaterEqual(result["rul_seconds"], 0.0)
        self.assertIn("not field-validated", result["label"])
        self.assertTrue(result["operator_action_required"])


class RealMotorReadinessDocumentationTest(unittest.TestCase):
    def test_readiness_doc_contract_and_script_are_discoverable(self):
        doc = Path(ROOT) / "docs" / "REAL_MOTOR_READINESS.md"
        self.assertTrue(doc.exists(), "missing target-rig readiness evidence")
        text = doc.read_text(encoding="utf-8")
        for token in (
            "ml/rul_from_rig.py",
            "failure_timestamp",
            "rms_dyn",
            "leave-one-run-out",
            "not field-validated",
            "[NEED:",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_entry_points_link_to_readiness_evidence(self):
        entry_points = (
            "README.md",
            "public/guide.html",
            "docs/EXHIBITION_REVIEW_PACK.md",
            "docs/FILE_MAP.md",
            "docs/G12_REQUEST_RESPONSE_REGISTER.md",
            "docs/PI_DEPLOYMENT_EVIDENCE.md",
            "ml/ai_report.md",
            "PLAN.md",
        )
        for relative_path in entry_points:
            with self.subTest(file=relative_path):
                text = (Path(ROOT) / relative_path).read_text(encoding="utf-8")
                self.assertIn("rul_from_rig.py", text)

    def test_readiness_doc_is_linked_from_indexes(self):
        for relative_path in (
            "README.md",
            "docs/FILE_MAP.md",
            "docs/G12_REQUEST_RESPONSE_REGISTER.md",
            "docs/EXHIBITION_REVIEW_PACK.md",
            "docs/PI_DEPLOYMENT_EVIDENCE.md",
            "ml/ai_report.md",
            "PLAN.md",
        ):
            with self.subTest(file=relative_path):
                text = (Path(ROOT) / relative_path).read_text(encoding="utf-8")
                self.assertIn("REAL_MOTOR_READINESS.md", text)


if __name__ == "__main__":
    unittest.main()
