#!/usr/bin/env python3
"""Labelled RUL benchmark on a real FMCG three-phase induction motor.

Source: Zenodo DOI 10.5281/zenodo.15637023, CC BY 4.0, companion paper
DOI 10.35784/acs_7299. The paper states that RUL is the number of hours a
motor runs from startup to shutdown or retirement, taken from SAP Plant
Maintenance history and combined with accelerometer readings. This is a
**public industrial benchmark**, not a measurement from our capstone rig.

The source CSV contains several concatenated operating periods. A run here is
a contiguous, strictly time-ordered block whose `RUL (jam)` label descends to
zero; blocks that never reach zero are excluded rather than relabelled. The
benchmark uses leave-one-run-out validation on the last 20% of the held run.
Every feature at row *i* uses only rows 0..i of that same run.

A second, explicitly configured task reports 24-hour failure-warning accuracy:
truth is `RUL <= 24 h`, prediction is predicted RUL <= 24 h. The 24-hour value
is a benchmark bin, not an operator-approved alarm threshold.

Usage:

    python3 ml/rul_fmcg.py [--csv data/fmcg_induction_rul/raw.csv] \
        [--report ml/rul_fmcg_report.json]
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "data" / "fmcg_induction_rul" / "raw.csv"
DEFAULT_REPORT = ROOT / "ml" / "rul_fmcg_report.json"

LABEL = "OFFLINE RESULT / NAMED PUBLIC DATASET"
ZENODO_URL = "https://zenodo.org/records/15637023"
SOURCE_MD5 = "52df07317901bdb7647c86df479d06c6"
LICENSE = "CC BY 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
PAPER_DOI = "10.35784/acs_7299"
CITATION = (
    "Anindhito, M. D. (2025). Dataset for Predicting Downtime and RUL for "
    "3 Phase Induction Motor from FMCG Company [Dataset]. Zenodo, "
    "DOI 10.5281/zenodo.15637023. Companion paper: Anindhito & Suharjito, "
    "Applied Computer Science 21(3), 72-86, DOI 10.35784/acs_7299."
)

RAW_COLUMNS = {
    "RMSVelX (mm/s)": "rms_x",
    "RMSVelY (mm/s)": "rms_y",
    "RMSVelZ (mm/s)": "rms_z",
    "Temperature (°C)": "temp_c",
    "ElectricalStatorFrequency (Hz)": "stator_hz",
    "Rotation Speed (rpm)": "speed_rpm",
    "Slip Frequency (Hz)": "slip_hz",
    "Torque (Nm)": "torque_nm",
    "AccelerationGeometricMean (mm/s²)": "accel_geo",
    "BearingState": "bearing_state",
    "MisalignmentState": "misalignment_state",
    "UnbalanceState": "unbalance_state",
    "VelocityGeometricMean (mm/s)": "velocity_geo",
}
VALUE_COLUMNS = tuple(RAW_COLUMNS.values())
FEATURE_COLUMNS = ("elapsed_h",) + tuple(
    f"{name}_{stat}" for name in VALUE_COLUMNS for stat in ("mean5", "std5")
)

MIN_RUN_ROWS = 100
MIN_DECREASES = 20
MIN_START_RUL = 50.0
TRAILING_WINDOW = 5
TAIL_FRACTION = 0.20
WARNING_THRESHOLD_H = 24.0
N_ESTIMATORS = 200
MAX_DEPTH = 12
RANDOM_STATE = 42


@dataclass(frozen=True)
class Run:
    """One contiguous RUL-to-zero trajectory from the public source."""

    run_id: str
    source_rows: tuple[int, ...]
    timestamps: tuple[dt.datetime, ...]
    rul_h: np.ndarray
    features: np.ndarray
    downtime_yes: int

    @property
    def duration_h(self) -> float:
        seconds = (self.timestamps[-1] - self.timestamps[0]).total_seconds()
        return float(seconds / 3600.0)


def _parse_date(cell: str) -> dt.date:
    text = cell.strip()
    if text.isdigit():
        return dt.date(1899, 12, 30) + dt.timedelta(days=int(text))
    return dt.date.fromisoformat(text[:10])


def _parse_timestamp(date_cell: str, time_cell: str) -> dt.datetime:
    clock = time_cell.strip().split(" ")[-1]
    hour, minute, second = (int(part) for part in clock.split(":"))
    return dt.datetime.combine(_parse_date(date_cell), dt.time(hour, minute, second))


def _number(cell: str) -> float:
    text = cell.strip()
    if not text:
        return float("nan")
    return float(text)


def _trailing_stats(values: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    """Causal trailing mean and population std; leading rows use fewer samples."""

    means = np.empty(values.size, dtype=float)
    stds = np.empty(values.size, dtype=float)
    for index in range(values.size):
        segment = values[max(0, index - window + 1) : index + 1]
        finite = segment[np.isfinite(segment)]
        if finite.size:
            means[index] = float(np.mean(finite))
            stds[index] = float(np.std(finite))
        else:
            means[index] = 0.0
            stds[index] = 0.0
    return means, stds


def _build_features(
    values: np.ndarray, timestamps: tuple[dt.datetime, ...]
) -> np.ndarray:
    columns: list[np.ndarray] = []
    elapsed = np.array(
        [(stamp - timestamps[0]).total_seconds() / 3600.0 for stamp in timestamps],
        dtype=float,
    )
    columns.append(elapsed)
    for column in range(values.shape[1]):
        mean, std = _trailing_stats(values[:, column], TRAILING_WINDOW)
        columns.extend((mean, std))
    return np.column_stack(columns)


def load_runs(path: Path | str = DEFAULT_CSV) -> dict[str, Run]:
    """Parse the source CSV and keep only complete RUL-to-zero trajectories."""

    path = Path(path)
    with path.open(newline="", encoding="cp1252") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        header = tuple(reader.fieldnames or ())
        required = set(RAW_COLUMNS) | {"Date", "Time", "RUL (jam)", "Downtime"}
        if not required.issubset(header):
            raise ValueError(f"{path.name} is missing source columns")

        rows: list[dict[str, Any]] = []
        for line, row in enumerate(reader, start=2):
            try:
                timestamp = _parse_timestamp(row["Date"], row["Time"])
                rul = _number(row["RUL (jam)"])
                values = {
                    name: _number(row[source]) for source, name in RAW_COLUMNS.items()
                }
                downtime = row["Downtime"].strip().upper()
            except (ValueError, KeyError, TypeError) as error:
                raise ValueError(f"{path.name}:{line}: invalid source row") from error
            if not math.isfinite(rul) or rul < 0.0:
                raise ValueError(
                    f"{path.name}:{line}: RUL must be finite and non-negative"
                )
            if downtime not in {"YES", "NO"}:
                raise ValueError(f"{path.name}:{line}: Downtime must be YES or NO")
            rows.append(
                {
                    "index": line,
                    "timestamp": timestamp,
                    "rul": rul,
                    "values": values,
                    "downtime": downtime,
                }
            )

    if not rows:
        raise ValueError(f"{path.name} has no rows")

    segments: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    previous_rul: float | None = None
    for row in rows:
        if previous_rul is not None and row["rul"] > previous_rul + 1e-9:
            segments.append(current)
            current = []
        current.append(row)
        previous_rul = row["rul"]
    segments.append(current)

    runs: dict[str, Run] = {}
    for segment in segments:
        rul_values = np.array([row["rul"] for row in segment], dtype=float)
        decreases = int(np.sum(np.diff(rul_values) < -1e-9))
        timestamps = tuple(row["timestamp"] for row in segment)
        ordered = all(
            later > earlier for earlier, later in zip(timestamps, timestamps[1:])
        )
        eligible = (
            len(segment) >= MIN_RUN_ROWS
            and decreases >= MIN_DECREASES
            and float(np.min(rul_values)) <= 1e-9
            and float(np.max(rul_values)) >= MIN_START_RUL
            and ordered
        )
        if not eligible:
            continue
        matrix = np.array(
            [[row["values"][name] for name in VALUE_COLUMNS] for row in segment],
            dtype=float,
        )
        run_id = f"run_{len(runs) + 1:02d}"
        runs[run_id] = Run(
            run_id=run_id,
            source_rows=tuple(row["index"] for row in segment),
            timestamps=timestamps,
            rul_h=rul_values,
            features=_build_features(matrix, timestamps),
            downtime_yes=sum(row["downtime"] == "YES" for row in segment),
        )
    if len(runs) < 3:
        raise ValueError(f"{path.name} has fewer than three complete RUL-to-zero runs")
    return runs


def _fit_predict(
    train_runs: Sequence[Run], test_run: Run
) -> tuple[np.ndarray, np.ndarray]:
    """Fit imputer and regressor on other runs only; predict causal test rows."""

    x_train = np.vstack([run.features for run in train_runs])
    y_train = np.concatenate([run.rul_h for run in train_runs])
    imputer = SimpleImputer(strategy="median")
    x_train = imputer.fit_transform(x_train)
    model = RandomForestRegressor(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        random_state=RANDOM_STATE,
        n_jobs=1,
    )
    model.fit(x_train, y_train)
    predicted = model.predict(imputer.transform(test_run.features))
    return np.clip(predicted, 0.0, float(np.max(y_train))), y_train


def _scores(expected: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "mae_h": round(float(np.mean(np.abs(expected - predicted))), 3),
        "rmse_h": round(float(np.sqrt(np.mean(np.square(expected - predicted)))), 3),
    }


def _warning_scores(
    expected: np.ndarray, predicted: np.ndarray, threshold: float
) -> dict[str, float]:
    truth = expected <= threshold
    alert = predicted <= threshold
    true_positive = int(np.sum(truth & alert))
    false_positive = int(np.sum(~truth & alert))
    false_negative = int(np.sum(truth & ~alert))
    true_negative = int(np.sum(~truth & ~alert))
    total = len(expected)
    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 0.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 0.0
    )
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "accuracy": round((true_positive + true_negative) / total, 3),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
    }


def evaluate(
    csv_path: Path | str = DEFAULT_CSV,
    *,
    tail_fraction: float = TAIL_FRACTION,
    warning_threshold_h: float = WARNING_THRESHOLD_H,
) -> dict[str, Any]:
    """Leave-one-run-out evaluation on the last fraction of the held run."""

    if not 0 < tail_fraction <= 1:
        raise ValueError("tail_fraction must be in (0, 1]")
    if warning_threshold_h <= 0:
        raise ValueError("warning_threshold_h must be positive")
    runs = load_runs(csv_path)
    expected: list[float] = []
    predicted: list[float] = []
    zero_baseline: list[float] = []
    median_baseline: list[float] = []
    per_run: dict[str, Any] = {}

    for held_id in sorted(runs):
        held = runs[held_id]
        train = [run for name, run in sorted(runs.items()) if name != held_id]
        tail_start = int(math.floor((1.0 - tail_fraction) * (held.rul_h.size - 1)))
        estimates, y_train = _fit_predict(train, held)
        tail = np.arange(tail_start, held.rul_h.size)
        truth = held.rul_h[tail]
        guess = estimates[tail]
        expected.extend(truth.tolist())
        predicted.extend(guess.tolist())
        zero_baseline.extend([0.0] * tail.size)
        median_baseline.extend([float(np.median(y_train))] * tail.size)
        per_run[held_id] = {
            "source_rows": [held.source_rows[0], held.source_rows[-1]],
            "rows": int(held.rul_h.size),
            "duration_h": round(held.duration_h, 3),
            "downtime_yes_rows": held.downtime_yes,
            "train_runs": [run.run_id for run in train],
            "tail_rows": int(tail.size),
            "actual_last_rul_h": round(float(held.rul_h[-1]), 3),
            "predicted_last_rul_h": round(float(guess[-1]), 3),
            "tail_mae_h": _scores(truth, guess)["mae_h"],
            **_warning_scores(truth, guess, warning_threshold_h),
        }

    expected_array = np.asarray(expected, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    return {
        "status": "benchmark_complete",
        "label": LABEL,
        "source": {
            "dataset": "FMCG 160 kW three-phase induction motor vibration and maintenance records",
            "zenodo_url": ZENODO_URL,
            "doi": "10.5281/zenodo.15637023",
            "source_filename": "Downtime and RUL Prediction .csv",
            "source_md5": SOURCE_MD5,
            "license": LICENSE,
            "license_url": LICENSE_URL,
            "paper_doi": PAPER_DOI,
            "citation": CITATION,
            "our_motor": False,
            "operator_confirmed_failure": False,
            "field_validation": False,
        },
        "data": {
            "n_runs": len(runs),
            "n_rows": int(sum(run.rul_h.size for run in runs.values())),
            "rul_unit": "hours from startup to shutdown or retirement (paper definition)",
            "rul_endpoint": "source RUL label reaches 0; Downtime=YES is present in two runs",
            "channels_used": list(VALUE_COLUMNS),
            "channels_not_available": [
                "airborne acoustic level",
                "four-class fault label",
            ],
            "date_note": "source mixes ISO dates and Excel serial dates; both are converted once at load",
        },
        "method": {
            "validation": "leave-one-run-out; last 20% of the held run's rows",
            "tail_fraction": tail_fraction,
            "features": "trailing 5-row causal mean and std for each numeric channel plus elapsed hours",
            "model": f"RandomForestRegressor(n_estimators={N_ESTIMATORS}, max_depth={MAX_DEPTH}, random_state={RANDOM_STATE})",
            "imputation": "median fitted on training runs only",
            "warning_threshold_h": warning_threshold_h,
            "warning_label": "benchmark bin RUL <= 24 h, not an operator-approved alarm",
            "causal": True,
            "baseline": (
                "constant zero, constant median RUL of the training runs, and "
                "a constant no-warning classifier"
            ),
        },
        "tail_windows": {
            "n_rows": int(expected_array.size),
            **_scores(expected_array, predicted_array),
            **_warning_scores(expected_array, predicted_array, warning_threshold_h),
        },
        "constant_zero_baseline_tail_windows": _scores(
            expected_array, np.zeros_like(expected_array)
        ),
        "constant_median_baseline_tail_windows": _scores(
            expected_array, np.asarray(median_baseline, dtype=float)
        ),
        "constant_no_warning_baseline_tail_windows": _warning_scores(
            expected_array,
            np.full_like(expected_array, warning_threshold_h + 1.0),
            warning_threshold_h,
        ),
        "per_run": per_run,
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
