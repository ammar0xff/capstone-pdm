"""Checks the labelled NASA IMS public-bearing RUL benchmark.

The synthetic CSVs here only prove the data contract and causality. The vendored
feature record comes from the public NASA IMS archive and is never presented as
a measurement from, or a field validation of, the capstone motor.
"""

import csv
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

import rul_nasa_ims as nasa  # noqa: E402

SCRIPT = os.path.join(ROOT, "ml", "rul_nasa_ims.py")
VENDORED = Path(ROOT) / "data" / "nasa_ims"
LABEL = "BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED"
EXPECTED_SNAPSHOTS = {
    "s1_b3": 2156,
    "s1_b4": 2156,
    "s2_b1": 984,
    "s3_b3": 6324,
}


def _write_csv(directory: str, rows: int = 30) -> str:
    path = os.path.join(directory, "failed_bearings.csv")
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(nasa.CSV_COLUMNS)
        for bearing_id, set_name, failure, channels in nasa.BEARING_CONFIG:
            for index in range(rows):
                rms1 = 0.1 + 0.01 * index
                rms2 = 0.2 + 0.02 * index if len(channels) == 2 else ""
                kurt1 = 3.0
                kurt2 = 3.0 if len(channels) == 2 else ""
                writer.writerow(
                    [
                        set_name,
                        bearing_id,
                        failure,
                        index,
                        index * 10.0,
                        f"2020-01-01T00:{index % 60:02d}:00",
                        rms1,
                        kurt1,
                        rms2,
                        kurt2,
                    ]
                )
    return path


class NasaDataContractTest(unittest.TestCase):
    def test_load_csv_builds_finite_normalised_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            bearings = nasa.load_csv(_write_csv(tmp))

        self.assertEqual(set(bearings), {config[0] for config in nasa.BEARING_CONFIG})
        for bearing in bearings.values():
            self.assertEqual(bearing.snapshots.size, 30)
            self.assertEqual(bearing.health.size, 30)
            self.assertTrue(np.isfinite(bearing.health).all())
            self.assertAlmostEqual(bearing.duration_min, 290.0)
            self.assertAlmostEqual(float(np.median(bearing.health[:3])), 0.0, places=6)

    def test_bad_labels_missing_values_and_time_order_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            valid = _write_csv(tmp)
            with open(valid, newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            cases = {
                "wrong-set": [dict(row, set="9th_test") for row in rows],
                "wrong-failure": [dict(row, failure="not documented") for row in rows],
                "empty-rms": [dict(row, rms1="") for row in rows],
                "zero-rms": [dict(row, rms1="0") for row in rows],
                "repeated-snapshot": [
                    dict(row, snapshot="5")
                    if row["bearing"] == "s2_b1" and row["snapshot"] == "6"
                    else row
                    for row in rows
                ],
            }
            for name, mutated in cases.items():
                path = os.path.join(tmp, f"{name}.csv")
                with open(path, "w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=nasa.CSV_COLUMNS)
                    writer.writeheader()
                    writer.writerows(mutated)
                with self.subTest(case=name):
                    with self.assertRaises(ValueError):
                        nasa.load_csv(path)

    def test_prediction_never_reads_the_held_bearings_future(self):
        health = np.linspace(0.0, 2.0, 60)
        before = nasa.predict_rul(health, 30, threshold=1.8, naive=300.0)
        extended = np.concatenate((health, np.full(30, 100.0)))
        after = nasa.predict_rul(extended, 30, threshold=1.8, naive=300.0)
        self.assertEqual(before, after)
        self.assertGreaterEqual(before, 0.0)
        self.assertLessEqual(before, 600.0)

    def test_flat_or_falling_trend_uses_naive_baseline(self):
        flat = np.full(60, 0.5)
        self.assertEqual(nasa.predict_rul(flat, 45, threshold=2.0, naive=123.5), 123.5)
        falling = np.linspace(2.0, 0.0, 60)
        self.assertEqual(
            nasa.predict_rul(falling, 45, threshold=2.0, naive=123.5), 123.5
        )


class NasaEvaluationTest(unittest.TestCase):
    def test_evaluate_is_bearing_disjoint_and_honestly_labelled(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = nasa.evaluate(_write_csv(tmp))
        self.assertEqual(report["status"], "benchmark_complete")
        self.assertEqual(report["label"], LABEL)
        self.assertIs(report["source"]["our_motor"], False)
        self.assertIs(report["source"]["operator_confirmed_failure"], False)
        self.assertIs(report["source"]["field_validation"], False)
        self.assertIsNone(report["readiness"]["hours_to_failure_for_our_rig"])
        self.assertEqual(
            report["method"]["validation"],
            "leave-one-bearing-out; last 20% of the held bearing's snapshots",
        )
        self.assertEqual(
            set(report["per_bearing"]), {config[0] for config in nasa.BEARING_CONFIG}
        )
        self.assertGreater(report["tail_windows"]["n_windows"], 0)
        self.assertIn(
            "not wall-clock operating hours", report["data"]["snapshot_period_min"]
        )

    def test_tail_fraction_is_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_csv(tmp)
            for bad in (0.0, -0.1, 1.1):
                with self.subTest(fraction=bad):
                    with self.assertRaises(ValueError):
                        nasa.evaluate(path, tail_fraction=bad)


class NasaEvidenceTest(unittest.TestCase):
    def test_vendored_features_match_manifest(self):
        manifest = json.loads((VENDORED / "manifest.json").read_text(encoding="utf-8"))
        csv_path = VENDORED / "failed_bearings.csv"
        self.assertEqual(
            hashlib.sha256(csv_path.read_bytes()).hexdigest(),
            manifest["features"]["failed_bearings.csv"]["sha256"],
        )
        self.assertEqual(manifest["source"]["archive_sha256"], nasa.ARCHIVE_SHA256)
        self.assertEqual(
            {item["id"] for item in manifest["bearings"]},
            {config[0] for config in nasa.BEARING_CONFIG},
        )
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(tuple(reader.fieldnames), nasa.CSV_COLUMNS)
            counts: dict[str, int] = {}
            failures: dict[str, str] = {}
            for row in reader:
                counts[row["bearing"]] = counts.get(row["bearing"], 0) + 1
                failures[row["bearing"]] = row["failure"]
        self.assertEqual(counts, EXPECTED_SNAPSHOTS)
        for item in manifest["bearings"]:
            with self.subTest(bearing=item["id"]):
                self.assertEqual(counts[item["id"]], item["snapshots"])
                self.assertEqual(failures[item["id"]], item["failure"])

    def test_report_and_docs_keep_label_and_provenance(self):
        report = json.loads(
            (Path(ROOT) / "ml" / "rul_nasa_ims_report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report, nasa.evaluate(VENDORED / "failed_bearings.csv"))
        readme = (VENDORED / "README.md").read_text(encoding="utf-8")
        provenance = (Path(ROOT) / "docs" / "DATA_PROVENANCE_LICENSES.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual(report["label"], LABEL)
        self.assertEqual(report["source"]["archive_sha256"], nasa.ARCHIVE_SHA256)
        self.assertEqual(report["source"]["license_evidence"], nasa.LICENSE_EVIDENCE)
        self.assertIs(report["source"]["field_validation"], False)
        for token in (
            "https://data.nasa.gov/dataset/ims-bearings",
            "https://www.usa.gov/government-works",
            "NOT OUR MOTOR",
            "NOT FIELD-VALIDATED",
            "6cb42c263b0281c725abf99f4b9fcf49915c949f31dbd2333877dc2e06ce9ec2",
        ):
            with self.subTest(doc_token=token):
                self.assertIn(token, readme)
        self.assertIn("NASA IMS Bearings", provenance)
        self.assertIn("not operator sign-off", provenance)
        for relative in (
            "README.md",
            "ml/ai_report.md",
            "docs/G12_REQUEST_RESPONSE_REGISTER.md",
            "docs/EXHIBITION_REVIEW_PACK.md",
        ):
            with self.subTest(no_placeholders_in=relative):
                self.assertNotIn(
                    "[[NASA_", (Path(ROOT) / relative).read_text(encoding="utf-8")
                )

    def test_cli_writes_the_same_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "report.json")
            proc = subprocess.run(
                [sys.executable, SCRIPT, "--report", out],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            written = json.loads(Path(out).read_text(encoding="utf-8"))
            self.assertEqual(written, json.loads(proc.stdout))
            self.assertEqual(written["data"]["n_bearings"], 4)
            self.assertEqual(written["label"], LABEL)


if __name__ == "__main__":
    unittest.main()
