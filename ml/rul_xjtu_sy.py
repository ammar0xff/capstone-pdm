#!/usr/bin/env python3
"""Labelled XJTU-SY bearing RUL benchmark with explicit provenance.

This is a **public bearing** run-to-failure benchmark. It is deliberately
separate from ``ml.rul_from_rig``: no number produced here is a life estimate
for the capstone motor, and no public dataset endpoint is operator acceptance
of a failure on our rig.

The vendored data are the 15 ``VelFeaturesB_*.mat`` feature matrices from the
CC BY 4.0 Mendeley Data record derived from the original XJTU-SY vibration
archive. Each row is one one-minute snapshot. The benchmark uses only three
causal time-domain features (horizontal maximum amplitude, RMS and kurtosis)
because they exist in every derived record. There is no temperature and no
acoustic channel, so this benchmark cannot validate our temperature or sound
features.

Method: for each held-out bearing, fit a straight-line trend to the last
``TREND_WINDOW`` snapshots of a log-health indicator, extrapolate to the
75th-percentile terminal health of the other 14 bearings, and compare the
result with the time remaining to the dataset-defined end of that bearing.
Every prediction at snapshot *i* reads only snapshots 0..i and other bearings;
nothing from the held bearing's future is used.

Usage:

    python3 ml/rul_xjtu_sy.py [--csv-dir data/xjtu_sy_mendeley/csv] \
        [--report ml/rul_xjtu_sy_report.json]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV_DIR = ROOT / "data" / "xjtu_sy_mendeley" / "csv"
DEFAULT_REPORT = ROOT / "ml" / "rul_xjtu_sy_report.json"

LABEL = "OFFLINE RESULT / NAMED PUBLIC DATASET"
SOURCE_URL = "https://biaowang.tech/xjtu-sy-bearing-datasets"
MIRROR_URL = "https://github.com/WangBiaoXJTU/xjtu-sy-bearing-datasets"
DERIVED_DATA_DOI = "10.17632/mpn45f4gxc.1"
DERIVED_DATA_URL = "https://data.mendeley.com/datasets/mpn45f4gxc/1"
DERIVED_DATA_LICENSE = "CC BY 4.0"
CITATION = (
    "Wang, B., Lei, Y., Li, N. and Li, N. (2020) A Hybrid Prognostics Approach "
    "for Estimating Remaining Useful Life of Rolling Element Bearings. IEEE "
    "Transactions on Reliability, 69(1), 401-412. doi:10.1109/TR.2018.2882682"
)
N_FEATURES = 54
SAMPLE_INTERVAL_MIN = 1.0
TREND_WINDOW = 40
TAIL_FRACTION = 0.20
TERMINAL_PERCENTILE = 75.0
MIN_ROWS = 10


@dataclass(frozen=True)
class Bearing:
    """One complete run-to-failure trajectory from the public benchmark."""

    run_id: str
    snapshots: np.ndarray
    health: np.ndarray

    @property
    def duration_min(self) -> float:
        return float(self.snapshots[-1] - self.snapshots[0]) * SAMPLE_INTERVAL_MIN

    @property
    def terminal_health(self) -> float:
        return float(np.median(self.health[-10:]))


def _health_indicator(features: np.ndarray) -> np.ndarray:
    """Mean of three log time-domain health features; finite and causal."""

    peak = np.log(np.maximum(features[:, 0], 1e-12))
    rms = np.log(np.maximum(features[:, 1], 1e-12))
    kurtosis = np.log1p(np.maximum(features[:, 2], 0.0))
    return (peak + rms + kurtosis) / 3.0


def load_bearing(path: Path) -> Bearing:
    """Read one derived feature matrix; the last snapshot defines the endpoint."""

    data = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
    if data.ndim != 2 or data.shape[1] != N_FEATURES + 1 or data.shape[0] < MIN_ROWS:
        raise ValueError(f"{path.name} has unexpected shape {data.shape}")
    if not np.isfinite(data).all():
        raise ValueError(f"{path.name} contains non-finite values")
    snapshots = data[:, 0]
    if np.any(np.diff(snapshots) <= 0):
        raise ValueError(f"{path.name} snapshots are not strictly increasing")
    return Bearing(path.stem, snapshots, _health_indicator(data[:, 1:]))


def load_dataset(csv_dir: Path | str) -> dict[str, Bearing]:
    files = sorted(Path(csv_dir).glob("bearing*.csv"))
    if not files:
        raise ValueError(f"no bearing feature CSVs found in {csv_dir}")
    bearings: dict[str, Bearing] = {}
    for path in files:
        bearing = load_bearing(path)
        if bearing.run_id in bearings:
            raise ValueError(f"duplicate bearing id {bearing.run_id}")
        bearings[bearing.run_id] = bearing
    if len(bearings) < 2:
        raise ValueError("at least two bearing runs are required")
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
    csv_dir: Path | str = DEFAULT_CSV_DIR, *, tail_fraction: float = TAIL_FRACTION
) -> dict[str, Any]:
    """Leave-one-bearing-out evaluation on the public XJTU-SY derived features."""

    if not 0 < tail_fraction <= 1:
        raise ValueError("tail_fraction must be in (0, 1]")
    bearings = load_dataset(csv_dir)
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
        estimates: list[float] = []
        for index in range(held.snapshots.size):
            estimates.append(
                predict_rul(held.health, index, threshold, naive)
                if index >= tail_start
                else 0.0
            )
        tail = np.arange(tail_start, held.snapshots.size)
        rul = (held.snapshots[-1] - held.snapshots[tail]) * SAMPLE_INTERVAL_MIN
        expected.extend(rul.tolist())
        predicted.extend([estimates[i] for i in tail])
        baseline.extend([naive] * tail.size)
        per_bearing[held_id] = {
            "snapshots": int(held.snapshots.size),
            "duration_min": round(held.duration_min, 3),
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
            "dataset": "XJTU-SY bearing run-to-failure data (derived CC BY 4.0 feature record)",
            "official_page": SOURCE_URL,
            "official_mirror": MIRROR_URL,
            "derived_data_doi": DERIVED_DATA_DOI,
            "derived_data_url": DERIVED_DATA_URL,
            "derived_data_license": DERIVED_DATA_LICENSE,
            "original_data_license": "[NEED: explicit XJTU-SY reuse licence; page requests citation only]",
            "citation": CITATION,
            "our_motor": False,
            "operator_confirmed_failure": False,
            "field_validation": False,
        },
        "data": {
            "bearings": sorted(bearings),
            "n_bearings": len(bearings),
            "n_snapshots": int(sum(item.snapshots.size for item in bearings.values())),
            "snapshot_period_min": SAMPLE_INTERVAL_MIN,
            "columns_used": [
                "feature_01 (peak)",
                "feature_02 (RMS)",
                "feature_03 (kurtosis)",
            ],
            "columns_not_available": [
                "temperature",
                "sound_db",
                "sound_zcr",
                "sound_rms",
            ],
            "rul_endpoint": "last published snapshot of each bearing run (dataset-defined end of life)",
        },
        "method": {
            "indicator": "mean of log peak, log RMS and log1p kurtosis (horizontal axis)",
            "trend_window_snapshots": TREND_WINDOW,
            "terminal_health_percentile_from_training_bearings": TERMINAL_PERCENTILE,
            "prediction_cap_minutes": "2 x median training duration; no field basis",
            "validation": "leave-one-bearing-out; last 20% of the held bearing's snapshots",
            "baseline": "constant median duration of the other 14 bearings",
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
    parser.add_argument("--csv-dir", default=str(DEFAULT_CSV_DIR))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args(argv)
    try:
        report = evaluate(args.csv_dir)
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
