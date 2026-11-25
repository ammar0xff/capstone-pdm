#!/usr/bin/env python3
"""RUL benchmark on NASA C-MAPSS FD001 — public simulated turbofan data.

This is deliberately separate from the runtime four-class diagnosis. It trains
a Random Forest regressor on run-to-failure histories from a public, cited
dataset and evaluates against NASA's withheld RUL labels. The result validates
the *pipeline on a public benchmark only*: it is not a remaining-life claim for
our induction motor and must never be presented as field validation.

Source: NASA PCoE, DOI 10.5281/zenodo.15346912, CC BY 4.0.
See `data/cmapss/README.md` for file hashes and citation.

Usage:

    python3 ml/train_rul_cmapss.py [--raw-dir data/cmapss] \
        [--report ml/rul_cmapss_report.json] [--model-out path.joblib]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RAW_DIR = ROOT / "data" / "cmapss"
DEFAULT_REPORT = ROOT / "ml" / "rul_cmapss_report.json"

SOURCE_DOI = "10.5281/zenodo.15346912"
SOURCE_URL = "https://zenodo.org/records/15346912"
SOURCE_LICENSE = "CC BY 4.0"
ARCHIVE_MD5 = "79a22f36e80606c69d0e9e4da5bb2b7a"

LABEL = (
    "NASA C-MAPSS FD001 simulated turbofan benchmark - "
    "not our motor, not field-validated"
)

N_COLUMNS = 26
N_UNITS = 100
CONSTANT_SENSORS = frozenset({5, 14, 22, 23})
SETTING_COLS = (2, 3, 4)
SENSOR_COLS = tuple(c for c in range(5, 26) if c not in CONSTANT_SENSORS)
FEATURE_COLS = SETTING_COLS + SENSOR_COLS
N_FEATURES = len(SETTING_COLS) + 3 * len(SENSOR_COLS)
WINDOW = 30
RUL_CAP = 125
VALIDATION_UNITS = frozenset(range(81, N_UNITS + 1))
N_ESTIMATORS = 100
RANDOM_STATE = 42
N_JOBS = 4


def load_raw(raw_dir: Path | str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load the three unmodified FD001 text files."""

    raw_dir = Path(raw_dir)
    names = ("train_FD001.txt", "test_FD001.txt", "RUL_FD001.txt")
    missing = [name for name in names if not (raw_dir / name).is_file()]
    if missing:
        raise ValueError(f"missing C-MAPSS files in {raw_dir}: {', '.join(missing)}")

    train = np.loadtxt(raw_dir / names[0])
    test = np.loadtxt(raw_dir / names[1])
    true_rul = np.loadtxt(raw_dir / names[2])
    if true_rul.ndim == 1:
        true_rul = true_rul.reshape(-1, 1)
    for name, array, expected_cols in (
        (names[0], train, N_COLUMNS),
        (names[1], test, N_COLUMNS),
        (names[2], true_rul, 1),
    ):
        if array.ndim != 2 or array.shape[1] != expected_cols:
            raise ValueError(f"{name} has unexpected shape {array.shape}")
    if train.shape[0] == 0 or test.shape[0] == 0 or true_rul.shape[0] != N_UNITS:
        raise ValueError("FD001 row or unit counts are wrong")
    return train, test, true_rul


def last_cycles(data: np.ndarray) -> dict[int, float]:
    """Last observed cycle for each unit."""

    result: dict[int, float] = {}
    for unit in np.unique(data[:, 0]):
        unit = int(unit)
        rows = data[data[:, 0] == unit]
        if rows.shape[0] == 0:
            raise ValueError(f"unit {unit} has no rows")
        result[unit] = float(rows[-1, 1])
    if set(result) != set(range(1, N_UNITS + 1)):
        raise ValueError(f"expected units 1..{N_UNITS}, got {sorted(result)}")
    return result


def make_targets(train: np.ndarray) -> np.ndarray:
    """Per-row RUL = last cycle of that unit minus this cycle, capped at 125.

    The RUL label is a target only. It is never copied into the feature matrix.
    """

    last = last_cycles(train)
    last_by_unit = np.array([last[u] for u in range(1, N_UNITS + 1)])
    unit_index = train[:, 0].astype(int) - 1
    if np.any(unit_index < 0) or np.any(unit_index >= N_UNITS):
        raise ValueError("unit id outside 1..100")
    return np.clip(last_by_unit[unit_index] - train[:, 1], 0.0, float(RUL_CAP))


def build_windows(
    data: np.ndarray, targets: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray, np.ndarray]:
    """Turn each unit's sensor history into trailing-window feature rows.

    Features are the trailing 30-cycle mean of three settings plus, for each of
    the 17 non-constant sensors, its trailing mean, standard deviation and
    short-minus-long mean trend. No future cycle and no RUL label is read.
    """

    features: list[np.ndarray] = []
    values: list[float] = []
    units: list[int] = []
    row_indices: list[int] = []
    half = WINDOW // 2

    for unit in np.unique(data[:, 0]):
        unit = int(unit)
        indices = np.flatnonzero(data[:, 0] == unit)
        rows = data[indices]
        if rows.shape[0] < WINDOW:
            raise ValueError(f"unit {unit} has fewer than {WINDOW} cycles")
        if not np.all(np.diff(rows[:, 1]) > 0):
            raise ValueError(f"unit {unit} cycles are not strictly increasing")

        x = rows[:, list(FEATURE_COLS)]
        cumulative = np.vstack([np.zeros(x.shape[1]), np.cumsum(x, axis=0)])
        cumulative_sq = np.vstack([np.zeros(x.shape[1]), np.cumsum(x * x, axis=0)])

        for position in range(WINDOW - 1, len(indices)):
            end = position + 1
            start = end - WINDOW
            mean = (cumulative[end] - cumulative[start]) / WINDOW
            variance = np.maximum(
                (cumulative_sq[end] - cumulative_sq[start]) / WINDOW - mean * mean,
                0.0,
            )
            std = np.sqrt(variance)
            short = (cumulative[end] - cumulative[end - half]) / half
            trend = short - mean
            features.append(
                np.concatenate(
                    [
                        mean[: len(SETTING_COLS)],
                        mean[len(SETTING_COLS) :],
                        std[len(SETTING_COLS) :],
                        trend[len(SETTING_COLS) :],
                    ]
                )
            )
            units.append(unit)
            row_indices.append(int(indices[position]))
            if targets is not None:
                values.append(float(targets[indices[position]]))

    matrix = np.vstack(features)
    if matrix.shape[1] != N_FEATURES:
        raise ValueError(f"expected {N_FEATURES} features, got {matrix.shape[1]}")
    return (
        matrix,
        np.asarray(values, dtype=float) if targets is not None else None,
        np.asarray(units, dtype=int),
        np.asarray(row_indices, dtype=int),
    )


def last_window_indices(units: np.ndarray) -> dict[int, int]:
    """Index of the final window belonging to each unit."""

    result: dict[int, int] = {}
    for position, unit in enumerate(units):
        result[int(unit)] = position
    if set(result) != set(range(1, N_UNITS + 1)):
        raise ValueError("not every unit has a trailing window")
    return result


def make_model() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=N_ESTIMATORS,
        random_state=RANDOM_STATE,
        n_jobs=N_JOBS,
        min_samples_leaf=2,
    )


def rmse(expected: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(expected, predicted)))


def evaluate(raw_dir: Path | str = DEFAULT_RAW_DIR) -> dict[str, Any]:
    """Train, validate by unit, then score on NASA's withheld test labels."""

    train, test, true_rul = load_raw(raw_dir)
    targets = make_targets(train)
    x_train, y_train, units_train, _ = build_windows(train, targets)
    x_test, _, units_test, _ = build_windows(test)

    train_last = last_window_indices(units_train)
    test_last = last_window_indices(units_test)
    test_positions = [test_last[u] for u in range(1, N_UNITS + 1)]

    fit_mask = ~np.isin(units_train, list(VALIDATION_UNITS))
    val_positions = [train_last[u] for u in sorted(VALIDATION_UNITS)]

    validation_model = make_model()
    validation_model.fit(x_train[fit_mask], y_train[fit_mask])
    validation_prediction = validation_model.predict(x_train[val_positions])
    validation_expected = y_train[val_positions]

    final_model = make_model()
    final_model.fit(x_train, y_train)
    test_prediction = final_model.predict(x_test[test_positions])

    baseline_prediction = np.full(N_UNITS, float(np.median(y_train)))
    return {
        "status": "benchmark_complete",
        "label": LABEL,
        "source": {
            "dataset": "NASA C-MAPSS FD001 (simulated turbofan)",
            "doi": SOURCE_DOI,
            "url": SOURCE_URL,
            "license": SOURCE_LICENSE,
            "archive_md5": ARCHIVE_MD5,
            "field_validation": False,
        },
        "method": {
            "model": "RandomForestRegressor",
            "n_estimators": N_ESTIMATORS,
            "random_state": RANDOM_STATE,
            "window_cycles": WINDOW,
            "rul_cap_cycles": RUL_CAP,
            "n_features": N_FEATURES,
            "validation_units": "81-100 (held out by unit)",
        },
        "data": {
            "train_rows": int(train.shape[0]),
            "test_rows": int(test.shape[0]),
            "train_units": N_UNITS,
            "test_units": N_UNITS,
            "test_labels": "RUL_FD001.txt (NASA withheld ground truth)",
        },
        "validation_last_window": {
            "n_units": len(val_positions),
            "rmse_cycles": rmse(validation_expected, validation_prediction),
            "mae_cycles": float(
                mean_absolute_error(validation_expected, validation_prediction)
            ),
        },
        "official_test": {
            "n_units": N_UNITS,
            "rmse_cycles": rmse(true_rul, test_prediction),
            "mae_cycles": float(mean_absolute_error(true_rul, test_prediction)),
        },
        "constant_baseline": {"rmse_cycles": rmse(true_rul, baseline_prediction)},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="RUL benchmark on public NASA C-MAPSS FD001 data; not field-validated."
    )
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument(
        "--model-out",
        default=None,
        help="Optional path to save the trained benchmark regressor",
    )
    args = parser.parse_args(argv)

    try:
        report = evaluate(args.raw_dir)
        if args.model_out:
            train, _, _ = load_raw(args.raw_dir)
            model = make_model()
            model.fit(build_windows(train, make_targets(train))[0], make_targets(train))
            joblib.dump(model, args.model_out)
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
