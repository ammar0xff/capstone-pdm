"""Checks the NASA C-MAPSS FD001 RUL benchmark.

These are public simulated turbofan data, not our motor. The tests guard the
provenance, the absence of label leakage and the published benchmark metrics;
they do not claim field validation.
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

import train_rul_cmapss as rul  # noqa: E402

RAW_DIR = os.path.join(ROOT, "data", "cmapss")
FILE_HASHES = {
    "train_FD001.txt": "259f340bac32ce6fa8894815600fa757",
    "test_FD001.txt": "62316d1dd70f88a9a43a1e2690765437",
    "RUL_FD001.txt": "8f4a8b3d2692b2f7d8e72b344927bf4b",
}


class CmapssProvenanceTest(unittest.TestCase):
    def test_local_raw_files_match_documented_hashes(self):
        for name, expected in FILE_HASHES.items():
            with self.subTest(file=name):
                path = os.path.join(RAW_DIR, name)
                with open(path, "rb") as handle:
                    actual = hashlib.md5(handle.read()).hexdigest()
                self.assertEqual(actual, expected)

    def test_source_metadata_is_cited_and_not_field_validated(self):
        self.assertEqual(rul.SOURCE_DOI, "10.5281/zenodo.15346912")
        self.assertEqual(rul.SOURCE_LICENSE, "CC BY 4.0")
        self.assertEqual(rul.ARCHIVE_MD5, "79a22f36e80606c69d0e9e4da5bb2b7a")
        self.assertIn("not our motor", rul.LABEL)
        self.assertIn("not field-validated", rul.LABEL)


class CmapssDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train, cls.test, cls.true_rul = rul.load_raw(RAW_DIR)
        cls.targets = rul.make_targets(cls.train)

    def test_file_shapes(self):
        self.assertEqual(self.train.shape, (20631, 26))
        self.assertEqual(self.test.shape, (13096, 26))
        self.assertEqual(self.true_rul.shape, (100, 1))

    def test_target_is_last_cycle_minus_current_cycle_capped(self):
        last = rul.last_cycles(self.train)
        unit_one = self.train[self.train[:, 0] == 1]
        self.assertEqual(last[1], unit_one[-1, 1])
        self.assertEqual(self.targets[0], float(rul.RUL_CAP))
        self.assertEqual(self.targets[int(unit_one.shape[0]) - 1], 0.0)
        for unit in (1, 42, 100):
            rows = np.flatnonzero(self.train[:, 0] == unit)
            with self.subTest(unit=unit):
                self.assertEqual(self.targets[rows[-1]], 0.0)
                self.assertLessEqual(self.targets[rows[0]], rul.RUL_CAP)
        self.assertTrue(np.all(self.targets >= 0))

    def test_target_is_not_subtracted_from_the_unit_id(self):
        # A unit-id target would repeat every 192 cycles for unit 1; the real
        # target is monotone within a unit and reaches zero only at its end.
        unit_one = np.flatnonzero(self.train[:, 0] == 1)
        series = self.targets[unit_one]
        self.assertTrue(np.all(np.diff(series) <= 0))
        self.assertEqual(int(np.sum(series == 0.0)), 1)

    def test_windows_have_expected_shape_and_never_read_future_cycles(self):
        matrix, values, units, _ = rul.build_windows(self.train, self.targets)
        self.assertEqual(matrix.shape[0], values.shape[0])
        self.assertEqual(matrix.shape[1], rul.N_FEATURES)
        self.assertEqual(len(np.unique(units)), rul.N_UNITS)

        # The first window of unit 1 uses only its first 30 cycles. Feeding the
        # same unit truncated to 40 cycles must give an identical feature row.
        unit_one = self.train[self.train[:, 0] == 1][:40]
        truncated, _, _, _ = rul.build_windows(unit_one)
        np.testing.assert_allclose(matrix[0], truncated[0])

    def test_changing_the_labels_does_not_change_the_features(self):
        first, _, _, _ = rul.build_windows(self.train, self.targets)
        second, _, _, _ = rul.build_windows(
            self.train, np.full_like(self.targets, 999.0)
        )
        np.testing.assert_array_equal(first, second)


class CmapssBenchmarkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = rul.evaluate(RAW_DIR)

    def test_validation_units_are_held_out_by_unit(self):
        self.assertEqual(rul.VALIDATION_UNITS, frozenset(range(81, 101)))
        self.assertEqual(len(rul.VALIDATION_UNITS), 20)

    def test_official_test_metrics_are_reproduced(self):
        official = self.report["official_test"]
        self.assertEqual(official["n_units"], 100)
        self.assertAlmostEqual(official["rmse_cycles"], 15.51, delta=0.5)
        self.assertAlmostEqual(official["mae_cycles"], 11.51, delta=0.5)
        self.assertLess(
            official["rmse_cycles"], self.report["constant_baseline"]["rmse_cycles"]
        )

    def test_validation_last_window_is_reported(self):
        validation = self.report["validation_last_window"]
        self.assertEqual(validation["n_units"], 20)
        self.assertLess(validation["rmse_cycles"], 5.0)

    def test_report_labels_state_it_is_a_benchmark_only(self):
        self.assertEqual(self.report["status"], "benchmark_complete")
        self.assertIn("not our motor", self.report["label"])
        self.assertIn("not field-validated", self.report["label"])
        self.assertIs(self.report["source"]["field_validation"], False)
        self.assertEqual(self.report["source"]["doi"], rul.SOURCE_DOI)


class CmapssCliTest(unittest.TestCase):
    @staticmethod
    def _write_small_fixture(directory):
        """Minimal FD001-shaped input: 100 units, 35 cycles, 26 columns.

        This only exercises the CLI plumbing; the real-data metrics are checked
        separately against the unmodified NASA files.
        """

        def rows(name, cycles):
            with open(os.path.join(directory, name), "w") as handle:
                for unit in range(1, 101):
                    for cycle in range(1, cycles + 1):
                        values = [float(unit), float(cycle)] + [
                            float(unit + cycle + col) for col in range(1, 25)
                        ]
                        handle.write(
                            " ".join(f"{value:.4f}" for value in values) + "\n"
                        )

        rows("train_FD001.txt", 35)
        rows("test_FD001.txt", 35)
        with open(os.path.join(directory, "RUL_FD001.txt"), "w") as handle:
            handle.write("\n".join("50" for _ in range(100)) + "\n")

    def test_cli_writes_json_report(self):
        script = os.path.join(ROOT, "ml", "train_rul_cmapss.py")
        with tempfile.TemporaryDirectory() as tmp:
            self._write_small_fixture(tmp)
            report_path = os.path.join(tmp, "report.json")
            proc = subprocess.run(
                [
                    sys.executable,
                    script,
                    "--raw-dir",
                    tmp,
                    "--report",
                    report_path,
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(report_path) as handle:
                written = json.load(handle)
            printed = json.loads(proc.stdout)
        self.assertEqual(written, printed)
        self.assertEqual(written["status"], "benchmark_complete")
        self.assertEqual(written["official_test"]["n_units"], 100)
        self.assertIn("not field-validated", written["label"])

    def test_cli_rejects_missing_raw_files(self):
        script = os.path.join(ROOT, "ml", "train_rul_cmapss.py")
        with tempfile.TemporaryDirectory() as tmp:
            proc = subprocess.run(
                [
                    sys.executable,
                    script,
                    "--raw-dir",
                    tmp,
                    "--report",
                    os.path.join(tmp, "report.json"),
                ],
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("ERROR", proc.stderr)


if __name__ == "__main__":
    unittest.main()
