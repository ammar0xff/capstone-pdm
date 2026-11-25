#!/usr/bin/env python3
"""Labelled NASA IMS bearing RUL benchmark with explicit provenance.

This is a **public bearing** run-to-failure benchmark from the University of
Cincinnati IMS / Rexnord tests hosted by NASA Open Data. It is deliberately
separate from ``ml.rul_from_rig``: no number produced here is a life estimate
for the capstone motor, and a dataset-defined end of test is not operator
confirmation of a failure on our rig.

The vendored CSV contains causal per-snapshot features derived from the four
bearings whose failures are documented in the NASA IMS README: set 1 bearing 3
(inner race), set 1 bearing 4 (rolling element), set 2 bearing 1 (outer race)
and set 3 bearing 3 (outer race). Each snapshot is a one-second, 20 kHz
vibration record; nominal time between snapshots is 5 minutes for the first 43
records of set 1 and 10 minutes after that. Those gaps are recorded cadence,
not wall-clock operating hours.

Method: for each held-out bearing, normalise log RMS by that bearing's own
first 10% of snapshots, fit a straight line to the last ``TREND_WINDOW``
normalised values, extrapolate to the 75th-percentile terminal health of the
other bearings, and compare with nominal minutes remaining to the last
published snapshot. Every prediction at snapshot *i* reads only snapshots
0..i of the held bearing; nothing from its future is used.

Usage:

    python3 ml/rul_nasa_ims.py [--csv data/nasa_ims/failed_bearings.csv] \
        [--report ml/rul_nasa_ims_report.json]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "data" / "nasa_ims" / "failed_bearings.csv"
DEFAULT_REPORT = ROOT / "ml" / "rul_nasa_ims_report.json"

LABEL = "BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED"
PORTAL_URL = "https://data.nasa.gov/dataset/ims-bearings"
ARCHIVE_URL = "https://data.nasa.gov/docs/legacy/IMS.zip"
ARCHIVE_SHA256 = "6cb42c263b0281c725abf99f4b9fcf49915c949f31dbd2333877dc2e06ce9ec2"
LICENSE_EVIDENCE = "https://www.usa.gov/government-works"
CITATION = (
    "Qiu, H., Lee, J. and Lin, J. (2006) Wavelet Filter-based Weak Signature "
    "Detection Method and its Application on Roller Bearing Prognostics. "
    "Journal of Sound and Vibration 289, 1066-1090."
)

# (bearing id, set, failure, zero-based channel indices in the raw snapshot)
BEARING_CONFIG: tuple[tuple[str, str, str, tuple[int, ...]], ...] = (
    ("s1_b3", "1st_test", "inner race", (4, 5)),
    ("s1_b4", "1st_test", "rolling element", (6, 7)),
    ("s2_b1", "2nd_test", "outer race", (0,)),
    ("s3_b3", "3rd_test", "outer race", (2,)),
)

TREND_WINDOW = 40
TAIL_FRACTION = 0.20
TERMINAL_PERCENTILE = 75.0
BASELINE_FRACTION = 0.10
MIN_ROWS = 20
CSV_COLUMNS = (
    "set",
    "bearing",
    "failure",
    "snapshot",
    "minutes",
    "timestamp",
    "rms1",
    "kurt1",
    "rms2",
    "kurt2",
)


@dataclass(frozen=True)
class Bearing:
    """One documented failed-bearing trajectory from a public NASA IMS test."""

    run_id: str
    snapshots: np.ndarray
    minutes: np.ndarray
    health: np.ndarray

    @property
    def duration_min(self) -> float:
        return float(self.minutes[-1] - self.minutes[0])

    @property
    def terminal_health(self) -> float:
        return float(np.median(self.health[-10:]))


def _normalised_log_rms(log_rms: np.ndarray) -> np.ndarray:
    """Subtract the bearing's own early baseline; fixed and never refitted."""

    baseline_rows = max(3, int(math.ceil(BASELINE_FRACTION * log_rms.size)))
    return log_rms - float(np.median(log_rms[:baseline_rows]))


def load_csv(path: Path | str) -> dict[str, Bearing]:
    """Read the vendored derived features and enforce their data contract."""

    path = Path(path)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            raise ValueError(f"{path.name} has unexpected columns {reader.fieldnames}")
        rows: dict[str, list[dict[str, str]]] = {}
        for row in reader:
            rows.setdefault(row["bearing"], []).append(row)

    expected = {config[0]: config for config in BEARING_CONFIG}
    if set(rows) != set(expected):
        raise ValueError(f"{path.name} bearings do not match the documented failures")

    bearings: dict[str, Bearing] = {}
    for bearing_id, entries in rows.items():
        config = expected[bearing_id]
        if len(entries) < MIN_ROWS:
            raise ValueError(f"{bearing_id} has fewer than {MIN_ROWS} snapshots")
        if any(
            entry["set"] != config[1] or entry["failure"] != config[2]
            for entry in entries
        ):
            raise ValueError(f"{bearing_id} set or failure label is inconsistent")
        snapshots = np.array([int(entry["snapshot"]) for entry in entries], dtype=float)
        minutes = np.array([float(entry["minutes"]) for entry in entries], dtype=float)
        if np.any(np.diff(snapshots) <= 0) or np.any(np.diff(minutes) <= 0):
            raise ValueError(f"{bearing_id} snapshots are not strictly increasing")
        channel_count = len(config[3])
        columns = tuple(f"rms{index + 1}" for index in range(channel_count))
        raw = [[float(entry[column]) for column in columns] for entry in entries]
        values = np.asarray(raw, dtype=float)
        if values.shape != (len(entries), channel_count):
            raise ValueError(f"{bearing_id} RMS columns are incomplete")
        if not np.isfinite(values).all() or np.any(values <= 0.0):
            raise ValueError(f"{bearing_id} RMS values must be finite and positive")
        health = _normalised_log_rms(np.log(values).mean(axis=1))
        if not np.isfinite(health).all():
            raise ValueError(f"{bearing_id} health indicator is not finite")
        bearings[bearing_id] = Bearing(bearing_id, snapshots, minutes, health)
    return bearings


def predict_rul(
    health: np.ndarray, index: int, threshold: float, naive: float
) -> float:
    """Extrapolate the trailing trend; never read a snapshot after ``index``."""

    start = max(0, index - TREND_WINDOW + 1)
    segment = health[start : index + 1]
    if segment.size < 3:
        return naive
    times = np.arange(start, index + 1, dtype=float)
    slope = float(np.polyfit(times, segment, 1)[0])
    if not math.isfinite(slope) or slope <= 1e-6:
        return naive
    estimate = (threshold - float(health[index])) / slope
    if not math.isfinite(estimate):
        return naive
    return float(min(max(estimate, 0.0), 2.0 * naive))


def _scores(expected: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "mae_min": round(float(np.mean(np.abs(expected - predicted))), 3),
        "rmse_min": round(float(np.sqrt(np.mean(np.square(expected - predicted)))), 3),
    }


def evaluate(
    csv_path: Path | str = DEFAULT_CSV, *, tail_fraction: float = TAIL_FRACTION
) -> dict[str, Any]:
    """Leave-one-bearing-out evaluation on the four documented NASA IMS failures."""

    if not 0 < tail_fraction <= 1:
        raise ValueError("tail_fraction must be in (0, 1]")
    bearings = load_csv(csv_path)
    if len(bearings) < 2:
        raise ValueError("at least two bearing runs are required")
    expected: list[float] = []
    predicted: list[float] = []
    baseline: list[float] = []
    per_bearing: dict[str, dict[str, Any]] = {}

    for held_id in sorted(bearings):
        held = bearings[held_id]
        others = [item for name, item in sorted(bearings.items()) if name != held_id]
        threshold = float(
            np.percentile(
                [item.terminal_health for item in others], TERMINAL_PERCENTILE
            )
        )
        naive = float(np.median([item.duration_min for item in others]))
        tail_start = int(np.floor((1.0 - tail_fraction) * (held.snapshots.size - 1)))
        estimates = [
            predict_rul(held.health, index, threshold, naive)
            if index >= tail_start
            else 0.0
            for index in range(held.snapshots.size)
        ]
        tail = np.arange(tail_start, held.snapshots.size)
        rul = held.minutes[-1] - held.minutes[tail]
        expected.extend(rul.tolist())
        predicted.extend([estimates[index] for index in tail])
        baseline.extend([naive] * tail.size)
        failure = next(config[2] for config in BEARING_CONFIG if config[0] == held_id)
        per_bearing[held_id] = {
            "failure": failure,
            "snapshots": int(held.snapshots.size),
            "nominal_duration_min": round(held.duration_min, 3),
            "predicted_last_rul_min": round(estimates[-1], 3),
            "tail_windows": int(tail.size),
        }

    expected_array = np.asarray(expected, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    baseline_array = np.asarray(baseline, dtype=float)
    return {
        "status": "benchmark_complete",
        "label": LABEL,
        "source": {
            "dataset": "NASA IMS Bearings run-to-failure tests (University of Cincinnati IMS / Rexnord)",
            "portal_url": PORTAL_URL,
            "archive_url": ARCHIVE_URL,
            "archive_sha256": ARCHIVE_SHA256,
            "license_evidence": LICENSE_EVIDENCE,
            "license_note": "portal metadata names US Government Work; page displays other-license-specified",
            "citation": CITATION,
            "our_motor": False,
            "operator_confirmed_failure": False,
            "field_validation": False,
        },
        "data": {
            "bearings": sorted(bearings),
            "n_bearings": len(bearings),
            "n_snapshots": int(sum(item.snapshots.size for item in bearings.values())),
            "snapshot_period_min": (
                "5 for the first 43 snapshots of set 1, then 10; nominal recorded "
                "cadence, not wall-clock operating hours"
            ),
            "columns_used": [
                "RMS of selected 20 kHz vibration channels (20,480 samples per snapshot)"
            ],
            "columns_not_available": [
                "temperature",
                "sound_db",
                "sound_zcr",
                "sound_rms",
            ],
            "rul_endpoint": (
                "last published snapshot of each documented failed-bearing test "
                "(dataset-defined end of test)"
            ),
        },
        "method": {
            "indicator": (
                "mean log RMS across selected channels minus the bearing's own first "
                "10% median (causal normalisation)"
            ),
            "trend_window_snapshots": TREND_WINDOW,
            "terminal_health_percentile_from_training_bearings": TERMINAL_PERCENTILE,
            "prediction_cap_minutes": "2 x median nominal duration of the other bearings; no field basis",
            "validation": "leave-one-bearing-out; last 20% of the held bearing's snapshots",
            "baseline": "constant median nominal duration of the other bearings",
            "tail_fraction": tail_fraction,
            "causal": True,
        },
        "tail_windows": {
            "n_windows": int(expected_array.size),
            **_scores(expected_array, predicted_array),
        },
        "constant_baseline_tail_windows": _scores(expected_array, baseline_array),
        "per_bearing": per_bearing,
        "readiness": {
            "not_our_motor": True,
            "not_field_validated": True,
            "hours_to_failure_for_our_rig": None,
            "operator_action_required": True,
            "runtime_or_dashboard_claim_changed": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.csv)
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
