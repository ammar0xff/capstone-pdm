"""Checks the labelled CWRU real-induction-motor diagnosis benchmark.

Synthetic recordings here only prove the data contract, fold separation and
CLI. The vendored CWRU files are real measurements from a different motor with
seeded faults; no result is a field validation of the capstone rig.
"""

import hashlib
import itertools
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import scipy.io

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, os.path.join(ROOT, "ml"))

import diagnosis_cwru as cwru  # noqa: E402

SCRIPT = os.path.join(ROOT, "ml", "diagnosis_cwru.py")
DATA_DIR = Path(ROOT) / "data" / "cwru"
REPORT_PATH = Path(ROOT) / "ml" / "diagnosis_cwru_report.json"
LABEL = "OFFLINE RESULT / NAMED PUBLIC DATASET"
EXPECTED_SOURCES = {
    "Normal_0.mat": ("X097_DE_time", "healthy", 0, "ee410e7243aefcd8b7120876556464e7"),
    "IR007_0.mat": (
        "X105_DE_time",
        "inner_race",
        1,
        "f14821b40412f33018279198da7f9cdc",
    ),
    "B007_0.mat": ("X118_DE_time", "ball", 2, "ff0f20588edc64140ae33888fcf1114a"),
    "OR007@6_0.mat": (
        "X130_DE_time",
        "outer_race",
        3,
        "e45f73f65cc3de4482d28d758503f2c1",
    ),
}
EXPECTED_METRICS = {
    "n_recordings": 4,
    "n_groups": 150,
    "n_windows": 1039,
    "n_folds": 5,
    "accuracy": 1.0,
    "majority_baseline_accuracy": 0.4004,
}


def _write_synthetic_recording(directory: str, name: str, class_id: int) -> str:
    """Write six contiguous blocks of a simple deterministic class signal."""

    total = cwru.DEFAULT_BLOCK_SAMPLES * 6
    time = np.arange(total, dtype=float)
    rng = np.random.default_rng(1000 + class_id)
    frequency = 60.0 + 35.0 * class_id
    samples = np.sin(2 * np.pi * frequency * time / cwru.DEFAULT_SAMPLE_RATE_HZ)
    samples = samples + 0.01 * rng.standard_normal(total)
    path = os.path.join(directory, name)
    scipy.io.savemat(path, {"DE_time": samples.reshape(-1, 1)})
    return path


def _synthetic_manifest() -> dict:
    return {
        "sample_rate_hz": cwru.DEFAULT_SAMPLE_RATE_HZ,
        "sources": [
            {
                "file": f"class_{class_id}.mat",
                "channel": "DE_time",
                "class_name": name,
                "class_id": class_id,
            }
            for class_id, name in enumerate(cwru.DEFAULT_CLASS_NAMES)
        ],
    }


class CwruDataContractTest(unittest.TestCase):
    def test_default_mapping_matches_hashes_and_channel_names(self):
        self.assertEqual(
            set(EXPECTED_SOURCES), {item["file"] for item in cwru.DEFAULT_SOURCES}
        )
        for source in cwru.DEFAULT_SOURCES:
            channel, class_name, class_id, md5 = EXPECTED_SOURCES[source["file"]]
            with self.subTest(file=source["file"]):
                self.assertEqual(source["channel"], channel)
                self.assertEqual(source["class_name"], class_name)
                self.assertEqual(source["class_id"], class_id)
                self.assertEqual(source["md5"], md5)
                payload = (DATA_DIR / source["file"]).read_bytes()
                self.assertEqual(hashlib.md5(payload).hexdigest(), md5)

    def test_config_and_source_errors_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for bad in (
                {
                    "window_samples": 0,
                    "hop_samples": 512,
                    "block_samples": 4096,
                    "n_folds": 5,
                },
                {
                    "window_samples": 1024,
                    "hop_samples": 2048,
                    "block_samples": 4096,
                    "n_folds": 5,
                },
                {
                    "window_samples": 8192,
                    "hop_samples": 512,
                    "block_samples": 4096,
                    "n_folds": 5,
                },
                {
                    "window_samples": 1024,
                    "hop_samples": 512,
                    "block_samples": 4096,
                    "n_folds": 1,
                },
            ):
                with self.subTest(config=bad):
                    with self.assertRaises(ValueError):
                        cwru.evaluate(tmp, **bad)

            for class_id, name in enumerate(cwru.DEFAULT_CLASS_NAMES):
                _write_synthetic_recording(tmp, f"class_{class_id}.mat", class_id)
            manifest = _synthetic_manifest()

            wrong_channel = json.loads(json.dumps(manifest))
            wrong_channel["sources"][0]["channel"] = "MISSING"
            with self.assertRaises(ValueError):
                cwru.evaluate(tmp, manifest=wrong_channel, verify_hashes=False)

            duplicate_id = json.loads(json.dumps(manifest))
            duplicate_id["sources"][1]["class_id"] = 0
            with self.assertRaises(ValueError):
                cwru.evaluate(tmp, manifest=duplicate_id, verify_hashes=False)

            hashed = json.loads(json.dumps(manifest))
            hashed["sources"][0]["md5"] = "0" * 32
            with self.assertRaises(ValueError):
                cwru.evaluate(tmp, manifest=hashed)

    def test_features_use_only_the_window_and_groups_never_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            for class_id, name in enumerate(cwru.DEFAULT_CLASS_NAMES):
                _write_synthetic_recording(tmp, f"class_{class_id}.mat", class_id)
            _, _, folds, spans, group_to_fold = cwru._build_matrix(
                cwru._read_sources(
                    Path(tmp),
                    _synthetic_manifest()["sources"],
                    block_samples=cwru.DEFAULT_BLOCK_SAMPLES,
                    window_samples=cwru.DEFAULT_WINDOW_SAMPLES,
                    verify_hashes=False,
                )[0],
                sample_rate_hz=cwru.DEFAULT_SAMPLE_RATE_HZ,
                window_samples=cwru.DEFAULT_WINDOW_SAMPLES,
                hop_samples=cwru.DEFAULT_HOP_SAMPLES,
                block_samples=cwru.DEFAULT_BLOCK_SAMPLES,
                n_folds=cwru.DEFAULT_N_FOLDS,
            )

        self.assertEqual(len(group_to_fold), 24)
        self.assertEqual(set(group_to_fold.values()), set(range(cwru.DEFAULT_N_FOLDS)))
        for first, second in itertools.combinations(spans, 2):
            if first.file_name != second.file_name or first.group == second.group:
                continue
            self.assertTrue(
                first.end <= second.start or second.end <= first.start,
                (first, second),
            )
        for span, fold in zip(spans, folds):
            self.assertEqual(group_to_fold[span.group], int(fold))

    def test_user_supplied_manifest_can_score_another_labelled_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            for class_id, name in enumerate(cwru.DEFAULT_CLASS_NAMES):
                _write_synthetic_recording(tmp, f"class_{class_id}.mat", class_id)
            report = cwru.evaluate(
                tmp, manifest=_synthetic_manifest(), verify_hashes=False
            )

        self.assertEqual(report["status"], "diagnosis_benchmark_complete")
        self.assertEqual(report["label"], cwru.OPERATOR_LABEL)
        self.assertEqual(report["data"]["n_recordings"], 4)
        self.assertEqual(report["data"]["operating_point"], "operator-supplied")
        self.assertIs(report["source"]["operator_supplied"], True)
        self.assertEqual(
            report["source"]["dataset"], "operator-supplied labelled recordings"
        )
        self.assertEqual(report["source"]["source_urls"], [])
        self.assertIsNone(report["readiness"]["not_our_motor"])
        self.assertNotIn("CWRU", json.dumps(report["source"]))
        self.assertGreater(report["metrics"]["accuracy"], 0.80)


class CwruEvidenceTest(unittest.TestCase):
    def test_committed_report_matches_reproduction_and_measured_numbers(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(report, cwru.evaluate(cwru.DEFAULT_DATA_DIR))
        self.assertEqual(report["status"], "diagnosis_benchmark_complete")
        self.assertEqual(report["label"], LABEL)
        self.assertIs(report["source"]["our_motor"], False)
        self.assertIs(report["source"]["operator_supplied"], False)
        self.assertIs(report["source"]["field_validation"], False)
        self.assertIs(report["readiness"]["not_our_motor"], True)
        self.assertIs(report["readiness"]["runtime_classifier_changed"], False)
        self.assertIsNone(report["readiness"]["rul_claim"])
        self.assertEqual(
            report["data"]["n_recordings"], EXPECTED_METRICS["n_recordings"]
        )
        self.assertEqual(report["data"]["n_groups"], EXPECTED_METRICS["n_groups"])
        self.assertEqual(report["data"]["n_windows"], EXPECTED_METRICS["n_windows"])
        self.assertEqual(report["data"]["n_folds"], EXPECTED_METRICS["n_folds"])
        self.assertEqual(report["metrics"]["accuracy"], EXPECTED_METRICS["accuracy"])
        self.assertGreater(report["metrics"]["accuracy"], 0.80)
        self.assertEqual(
            report["majority_class_baseline"]["accuracy"],
            EXPECTED_METRICS["majority_baseline_accuracy"],
        )
        self.assertGreater(
            report["metrics"]["accuracy"], report["majority_class_baseline"]["accuracy"]
        )
        for name, detail in report["metrics"]["per_class"].items():
            with self.subTest(class_name=name):
                self.assertEqual(detail["recall"], 1.0)
        self.assertEqual(len(report["per_fold"]), cwru.DEFAULT_N_FOLDS)
        for detail in report["per_fold"].values():
            self.assertEqual(detail["accuracy"], 1.0)

    def test_docs_state_the_real_result_without_promoting_it(self):
        documents = {
            "README.md": (Path(ROOT) / "README.md").read_text(encoding="utf-8"),
            "ml/ai_report.md": (ROOT / "ml" / "ai_report.md").read_text(
                encoding="utf-8"
            ),
            "data/cwru/README.md": (DATA_DIR / "README.md").read_text(encoding="utf-8"),
            "docs/G12_REQUEST_RESPONSE_REGISTER.md": (
                ROOT / "docs" / "G12_REQUEST_RESPONSE_REGISTER.md"
            ).read_text(encoding="utf-8"),
            "docs/EXHIBITION_REVIEW_PACK.md": (
                ROOT / "docs" / "EXHIBITION_REVIEW_PACK.md"
            ).read_text(encoding="utf-8"),
        }
        for name, text in documents.items():
            with self.subTest(document=name):
                self.assertIn("1.000", text)
                self.assertIn("100.0%", text)
                self.assertIn("40.04%", text)
                self.assertIn("NOT FIELD-VALIDATED", text)
                self.assertNotIn("100% on our motor", text)
                self.assertNotIn("CWRU RUL", text)
                self.assertNotIn("field-validated RUL complete", text)

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
