"""Checks the raw measurement reader: no calibration, correct CSV, clean stop."""

import csv
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "edge"))

import raw_measure  # noqa: E402


class FakeADXL:
    def __init__(self, frames):
        self.frames = iter(frames)

    def read_raw(self):
        return next(self.frames)


class FakeTC:
    def __init__(self, frames):
        self.frames = iter(frames)

    def read_temp(self):
        return next(self.frames)


class RawMeasureTest(unittest.TestCase):
    def test_read_frame_keeps_sensor_values_untouched(self):
        frame = raw_measure.read_frame(
            FakeADXL([(-12, 45, 256)]),
            FakeTC([(13.25, 0, 0x01A8)]),
            7,
        )
        self.assertEqual(frame["n"], 7)
        self.assertEqual(frame["adxl_x_lsb"], -12)
        self.assertEqual(frame["adxl_y_lsb"], 45)
        self.assertEqual(frame["adxl_z_lsb"], 256)
        self.assertEqual(frame["max6675_word_hex"], "0x01A8")
        self.assertEqual(frame["max6675_adc_counts"], 53)
        self.assertEqual(frame["open_tc"], 0)
        self.assertEqual(frame["temp_datasheet_c"], 13.25)

    def test_read_frame_returns_none_when_a_sensor_fails(self):
        self.assertIsNone(
            raw_measure.read_frame(FakeADXL([None]), FakeTC([(1.0, 0, 8)]), 1)
        )
        self.assertIsNone(
            raw_measure.read_frame(FakeADXL([(1, 2, 3)]), FakeTC([(None, 1, 0)]), 1)
        )

    def test_format_frame_marks_temperature_as_uncalibrated(self):
        frame = raw_measure.read_frame(
            FakeADXL([(1, 2, 3)]), FakeTC([(9.5, 0, 0x0026)]), 1
        )
        text = raw_measure.format_frame(frame)
        self.assertIn("ADXL LSB", text)
        self.assertIn("0x0026", text)
        self.assertIn("UNCALIBRATED", text)

    def test_collect_writes_raw_csv_and_stops_at_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "raw.csv"
            lines = []
            taken = raw_measure.collect(
                FakeADXL([(1, 2, 3), (4, 5, 6)]),
                FakeTC([(1.0, 0, 0x0008), (2.0, 1, 0x0010)]),
                count=2,
                interval=0,
                csv_path=target,
                emit=lines.append,
            )
            self.assertEqual(taken, 2)
            self.assertEqual(len(lines), 2)
            with open(target) as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["adxl_x_lsb"], "1")
            self.assertEqual(rows[1]["adxl_z_lsb"], "6")
            self.assertEqual(rows[0]["max6675_word_hex"], "0x0008")
            self.assertEqual(rows[1]["open_tc"], "1")

    def test_help_reports_raw_only_purpose(self):
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, "edge", "raw_measure.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("cal.json", result.stdout)
        self.assertIn("--csv", result.stdout)

    def test_invalid_interval_and_count_are_rejected(self):
        with self.assertRaises(Exception):
            raw_measure.positive_float("0")
        with self.assertRaises(Exception):
            raw_measure.non_negative_int("-1")


if __name__ == "__main__":
    unittest.main()
