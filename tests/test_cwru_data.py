"""Integrity checks for the vendored CWRU real-motor sample.

These are real measurements from a 2 hp Reliance Electric induction motor, but
the faults were seeded and the files are short steady-state recordings. They
can support a real-motor diagnosis benchmark, not a time-to-failure claim.
"""

import hashlib
import os
import unittest

import scipy.io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "cwru")
FILE_HASHES = {
    "Normal_0.mat": "ee410e7243aefcd8b7120876556464e7",
    "Normal_1.mat": "3983dcddead0d4b910ee1e8d3da164b9",
    "Normal_2.mat": "edc080a0b4fbc0c2ec8b7f1403372b73",
    "Normal_3.mat": "cc57a511b95785c805055d99281ea2bb",
    "IR007_0.mat": "f14821b40412f33018279198da7f9cdc",
    "B007_0.mat": "ff0f20588edc64140ae33888fcf1114a",
    "OR007@6_0.mat": "e45f73f65cc3de4482d28d758503f2c1",
}


class CwruDataTest(unittest.TestCase):
    def test_all_files_match_recorded_hashes(self):
        self.assertEqual(
            {name for name in os.listdir(RAW_DIR) if name.endswith(".mat")},
            set(FILE_HASHES),
        )
        for name, expected in FILE_HASHES.items():
            with self.subTest(file=name):
                with open(os.path.join(RAW_DIR, name), "rb") as handle:
                    self.assertEqual(hashlib.md5(handle.read()).hexdigest(), expected)

    def test_drive_end_vibration_array_is_present(self):
        for name, key in (
            ("Normal_0.mat", "X097_DE_time"),
            ("IR007_0.mat", "X105_DE_time"),
            ("B007_0.mat", "X118_DE_time"),
            ("OR007@6_0.mat", "X130_DE_time"),
        ):
            with self.subTest(file=name):
                contents = scipy.io.loadmat(os.path.join(RAW_DIR, name))
                self.assertIn(key, contents)
                array = contents[key]
                self.assertEqual(array.ndim, 2)
                self.assertEqual(array.shape[1], 1)
                self.assertGreater(array.shape[0], 100_000)

    def test_healthy_and_faulted_files_come_from_the_same_rig(self):
        healthy = scipy.io.loadmat(os.path.join(RAW_DIR, "Normal_0.mat"))
        faulted = scipy.io.loadmat(os.path.join(RAW_DIR, "IR007_0.mat"))
        for rpm in (healthy["X097RPM"], faulted["X105RPM"]):
            with self.subTest(rpm=rpm):
                # CWRU quotes ~1797 rpm for 0 hp; the logged value is 1796.
                self.assertAlmostEqual(int(rpm.ravel()[0]), 1797, delta=5)


if __name__ == "__main__":
    unittest.main()
