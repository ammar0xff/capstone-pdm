#!/usr/bin/env python3
"""Real run-to-failure RUL benchmark on IEEE PHM 2012 PRONOSTIA bearings.

This is deliberately separate from the runtime four-class diagnosis. It learns
remaining useful life from six genuine bearing run-to-failure experiments and
validates by leaving one whole bearing out at a time. The result proves the RUL
pipeline on a public real-bearing benchmark only. It is **not** a life
prediction for our induction motor and must never be presented as field
validation.

PRONOSTIA ran a 250 W asynchronous motor with a gearbox at 1800/1650/1500 rpm
and 4000/4200/5000 N radial loads. Vibration was sampled at 25.6 kHz, with
2560 samples recorded every 10 s; temperature was sampled at 10 Hz, with 600
samples recorded each minute. Experiments stopped when vibration exceeded 20 g,
so the last vibration timestamp is the challenge-defined RUL endpoint.

Sources:
- NASA PHM dataset mirror: https://phm-datasets.s3.amazonaws.com/NASA/10.+FEMTO+Bearing.zip
- Publicly licensed copy: figshare DOI 10.6084/m9.figshare.30595484.v1 (CC BY 4.0)
- Challenge description: IEEE PHM 2012 Prognostic Challenge details PDF

See `data/pronostia/README.md` for provenance, hashes and licence limits.

Usage:

    python3 ml/rul_pronostia.py [--raw-dir data/pronostia] \
        [--report ml/rul_pronostia_report.json] [--window 10]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RAW_DIR = ROOT / "data" / "pronostia"
DEFAULT_REPORT = ROOT / "ml" / "rul_pronostia_report.json"

SOURCE_URL = "https://phm-datasets.s3.amazonaws.com/NASA/10.+FEMTO+Bearing.zip"
LICENSED_COPY_DOI = "10.6084/m9.figshare.30595484.v1"
LICENSED_COPY_LICENSE = "CC BY 4.0"
ARCHIVE_MD5 = "0feedeab9584a68199f1f72fe45e3d19"

LABEL = (
    "IEEE PHM 2012 PRONOSTIA/FEMTO-ST real bearing benchmark - "
    "offline result on a named public dataset"
)

BEARINGS: tuple[str, ...] = (
    "Bearing1_1",
    "Bearing1_2",
    "Bearing2_1",
    "Bearing2_2",
    "Bearing3_1",
    "Bearing3_2",
)
VIBRATION_NAMES: tuple[str, ...] = ("rms", "kurtosis", "peak", "crest")
FEATURE_NAMES: tuple[str, ...] = tuple(
    f"{name}_{stat}" for name in VIBRATION_NAMES for stat in ("mean", "std", "trend")
) + ("temp_mean_now", "temp_max_now", "temp_available")
N_FEATURES = len(FEATURE_NAMES)
WINDOW = 10
N_ESTIMATORS = 100
RANDOM_STATE = 42
N_JOBS = 4


@dataclass(frozen=True)
class BearingData:
    """Causal features and labels for one run-to-failure bearing."""

    name: str
    acc_files: int
    temp_files: int
    wall_clock_resets: int
    duration_s: float
    features: np.ndarray
    times_s: np.ndarray
    rul_s: np.ndarray


def _timestamp(hour: float, minute: float, second: float, fraction: float) -> float:
    return float(hour * 3600.0 + minute * 60.0 + second + fraction)


def _file_index(path: Path) -> int:
    """Recording number from acc_00001.csv / temp_00001.csv."""

    match = re.search(r"_(\d+)\.csv$", path.name)
    if match is None:
        raise ValueError(f"unexpected recording filename: {path.name}")
    return int(match.group(1))


def _read_csv(path: Path, expected_columns: int) -> np.ndarray:
    # The published PRONOSTIA CSVs are not uniform: most use commas, but some
    # temperature bursts use semicolons. Detect from the first line, unmodified.
    with open(path, encoding="utf-8") as handle:
        delimiter = ";" if ";" in handle.readline() else ","
    try:
        data = np.loadtxt(path, delimiter=delimiter, ndmin=2)
    except (OSError, ValueError) as error:
        raise ValueError(f"cannot parse {path.name}: {error}") from error
    if data.ndim != 2 or data.shape[1] != expected_columns or data.shape[0] == 0:
        raise ValueError(f"{path.name} has unexpected shape {data.shape}")
    return data


def acc_features(path: Path) -> tuple[float, np.ndarray]:
    """One 0.1 s vibration burst: start timestamp and four causal statistics."""

    data = _read_csv(path, 6)
    start = _timestamp(data[0, 0], data[0, 1], data[0, 2], data[0, 3] / 1_000_000.0)
    # Remove each axis' DC component, as the runtime dynamic-RMS gate does.
    x = data[:, 4] - float(np.mean(data[:, 4]))
    y = data[:, 5] - float(np.mean(data[:, 5]))
    dynamic = np.sqrt(x * x + y * y)
    rms = float(np.sqrt(np.mean(dynamic * dynamic)))
    if rms <= 0.0:
        raise ValueError(f"{path.name} has zero vibration energy")
    kurtosis = float(np.mean(dynamic**4) / (rms**4))
    peak = float(np.max(np.abs(dynamic)))
    return start, np.array([rms, kurtosis, peak, peak / rms], dtype=float)


def temp_features(path: Path) -> tuple[float, float, float]:
    """One temperature burst: start timestamp, mean and maximum RTD value."""

    data = _read_csv(path, 5)
    start = _timestamp(data[0, 0], data[0, 1], data[0, 2], data[0, 3] / 10.0)
    return start, float(np.mean(data[:, 4])), float(np.max(data[:, 4]))


def _trailing_features(sequence: np.ndarray, window: int) -> np.ndarray:
    """Trailing mean/std/trend; every row reads only rows up to its own index."""

    if sequence.shape[0] < window:
        raise ValueError(f"need at least {window} recordings, got {sequence.shape[0]}")
    half = max(1, window // 2)
    result = np.empty((sequence.shape[0] - window + 1, 3 * sequence.shape[1]))
    for position in range(window - 1, sequence.shape[0]):
        end = position + 1
        segment = sequence[end - window : end]
        mean = np.mean(segment, axis=0)
        std = np.std(segment, axis=0)
        trend = np.mean(segment[-half:], axis=0) - np.mean(segment[:half], axis=0)
        result[position - window + 1] = np.concatenate((mean, std, trend))
    return result


def load_bearing(path: Path, window: int = WINDOW) -> BearingData:
    """Build causal features and RUL labels for one bearing directory."""

    acc_paths = sorted(path.glob("acc_*.csv"))
    if len(acc_paths) < window:
        raise ValueError(f"{path.name} has only {len(acc_paths)} acc files")
    temp_paths = sorted(path.glob("temp_*.csv"))

    wall_starts: list[float] = []
    vibration: list[np.ndarray] = []
    for acc_path in acc_paths:
        start, values = acc_features(acc_path)
        wall_starts.append(start)
        vibration.append(values)
    acc_indices = np.asarray([_file_index(path) for path in acc_paths], dtype=int)
    if np.any(np.diff(acc_indices) <= 0):
        raise ValueError(f"{path.name} acc recording numbers are not increasing")
    # The published wall-clock column resets twice in Bearing1_1. Use the
    # recording number with the documented 10 s cadence instead; this is
    # monotonic and causal, and the anomaly is counted in the report.
    wall_times = np.asarray(wall_starts, dtype=float)
    wall_clock_resets = int(np.sum(np.diff(wall_times) <= 0))
    times = (acc_indices - acc_indices[0]) * 10.0
    vibration_sequence = np.vstack(vibration)

    if temp_paths:
        temp_rows: list[tuple[float, float, float]] = []
        temp_indices: list[int] = []
        for temp_path in temp_paths:
            temp_rows.append(temp_features(temp_path))
            temp_indices.append(_file_index(temp_path))
        if np.any(np.diff(np.asarray(temp_indices, dtype=int)) <= 0):
            raise ValueError(f"{path.name} temp recording numbers are not increasing")
        # Temperature bursts are one per minute; align them by recording number.
        temp_time = (np.asarray(temp_indices, dtype=int) - temp_indices[0]) * 60.0
        temp_mean = np.asarray([row[1] for row in temp_rows], dtype=float)
        temp_max = np.asarray([row[2] for row in temp_rows], dtype=float)
        # asof join: use only the last temperature burst at or before this acc burst.
        indices = np.searchsorted(temp_time, times, side="right") - 1
        available = (indices >= 0).astype(float)
        safe = np.maximum(indices, 0)
        mean_now = np.where(available.astype(bool), temp_mean[safe], 0.0)
        max_now = np.where(available.astype(bool), temp_max[safe], 0.0)
    else:
        # PRONOSTIA has no temperature files for two learning bearings. A fixed
        # zero value plus a flag is causal; it does not read any future sample.
        available = np.zeros(times.shape[0], dtype=float)
        mean_now = np.zeros(times.shape[0], dtype=float)
        max_now = np.zeros(times.shape[0], dtype=float)

    burst_sequence = np.column_stack((vibration_sequence, mean_now, max_now, available))
    windowed = _trailing_features(burst_sequence, window)
    # Temperature trends are not meaningful when the flag is zero; keep only
    # the current temperature and availability as explicit scalar features.
    features = np.column_stack(
        (
            windowed[:, : 3 * len(VIBRATION_NAMES)],
            mean_now[window - 1 :],
            max_now[window - 1 :],
            available[window - 1 :],
        )
    )
    if features.shape[1] != N_FEATURES:
        raise ValueError(f"expected {N_FEATURES} features, got {features.shape[1]}")

    # The challenge endpoint is the final vibration burst (20 g stop rule).
    window_times = times[window - 1 :]
    end_time = float(times[-1])
    rul = end_time - window_times
    if np.any(rul < 0):
        raise ValueError(f"{path.name} has negative RUL labels")
    return BearingData(
        name=path.name,
        acc_files=len(acc_paths),
        temp_files=len(temp_paths),
        wall_clock_resets=wall_clock_resets,
        duration_s=end_time - float(times[0]),
        features=features,
        times_s=window_times,
        rul_s=rul,
    )


def load_dataset(raw_dir: Path | str, window: int = WINDOW) -> dict[str, BearingData]:
    """Load exactly the six canonical learning bearings; never the test set."""

    raw_dir = Path(raw_dir)
    directories = {path.name: path for path in raw_dir.iterdir() if path.is_dir()}
    expected = set(BEARINGS)
    found = set(directories)
    if found != expected:
        missing = sorted(expected - found)
        extra = sorted(found - expected)
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if extra:
            details.append("unexpected: " + ", ".join(extra))
        raise ValueError(
            f"unexpected PRONOSTIA bearings in {raw_dir} ({'; '.join(details)})"
        )
    return {name: load_bearing(directories[name], window) for name in BEARINGS}


def make_model() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=N_ESTIMATORS,
        random_state=RANDOM_STATE,
        n_jobs=N_JOBS,
        min_samples_leaf=2,
    )


def rmse(expected: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(mean_squared_error(expected, predicted)))


def _scores(expected: list[float], predicted: list[float]) -> dict[str, float]:
    actual = np.asarray(expected, dtype=float)
    estimate = np.asarray(predicted, dtype=float)
    return {
        "mae_s": float(mean_absolute_error(actual, estimate)),
        "rmse_s": rmse(actual, estimate),
    }


def evaluate(
    raw_dir: Path | str = DEFAULT_RAW_DIR, window: int = WINDOW
) -> dict[str, Any]:
    """Leave-one-bearing-out RUL evaluation on the real PRONOSTIA learning set."""

    data = load_dataset(raw_dir, window)
    last_expected: list[float] = []
    last_predicted: list[float] = []
    last_baseline: list[float] = []
    all_expected: list[float] = []
    all_predicted: list[float] = []
    per_bearing: dict[str, dict[str, Any]] = {}

    for held in BEARINGS:
        train_features = np.vstack(
            [data[name].features for name in BEARINGS if name != held]
        )
        train_targets = np.concatenate(
            [data[name].rul_s for name in BEARINGS if name != held]
        )
        model = make_model()
        model.fit(train_features, train_targets)

        held_data = data[held]
        prediction = model.predict(held_data.features)
        baseline = float(
            np.median([data[name].duration_s for name in BEARINGS if name != held])
        )
        last_expected.append(float(held_data.rul_s[-1]))
        last_predicted.append(float(prediction[-1]))
        last_baseline.append(baseline)
        all_expected.extend(held_data.rul_s.tolist())
        all_predicted.extend(prediction.tolist())
        per_bearing[held] = {
            "condition": held.split("_")[0],
            "acc_files": held_data.acc_files,
            "temp_files": held_data.temp_files,
            "duration_s": held_data.duration_s,
            "predicted_last_rul_s": float(prediction[-1]),
            "baseline_last_rul_s": baseline,
        }

    return {
        "status": "benchmark_complete",
        "label": LABEL,
        "source": {
            "dataset": "IEEE PHM 2012 PRONOSTIA/FEMTO-ST bearing learning set",
            "url": SOURCE_URL,
            "licensed_copy_doi": LICENSED_COPY_DOI,
            "licensed_copy_license": LICENSED_COPY_LICENSE,
            "archive_md5": ARCHIVE_MD5,
            "explicit_femto_license": "[NEED: explicit FEMTO-ST dataset licence]",
            "our_motor": False,
            "field_validation": False,
        },
        "method": {
            "model": "RandomForestRegressor",
            "n_estimators": N_ESTIMATORS,
            "random_state": RANDOM_STATE,
            "window_recordings": window,
            "recording_interval_s": 10,
            "n_features": N_FEATURES,
            "feature_names": list(FEATURE_NAMES),
            "validation": "leave-one-bearing-out; all windows of the held bearing",
            "rul_endpoint": "last vibration recording (challenge 20 g stop rule)",
            "timebase": "recording number x published cadence (10 s vibration, 60 s temperature); wall-clock resets counted, not used",
        },
        "data": {
            "bearings": list(BEARINGS),
            "acc_files": sum(item.acc_files for item in data.values()),
            "temp_files": sum(item.temp_files for item in data.values()),
            "wall_clock_resets": {
                name: item.wall_clock_resets for name, item in data.items()
            },
            "rpm_and_load": {
                "Bearing1_x": "1800 rpm / 4000 N",
                "Bearing2_x": "1650 rpm / 4200 N",
                "Bearing3_x": "1500 rpm / 5000 N",
            },
        },
        "last_window": {
            "n_bearings": len(BEARINGS),
            **_scores(last_expected, last_predicted),
        },
        "all_windows": {
            "n_windows": len(all_expected),
            **_scores(all_expected, all_predicted),
        },
        "constant_baseline_last_window": {
            "description": "median duration of the five training bearings",
            **_scores(last_expected, last_baseline),
        },
        "per_bearing": per_bearing,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Real run-to-failure bearing RUL benchmark, "
            "not field-validated."
        )
    )
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--window", type=int, default=WINDOW)
    parser.add_argument(
        "--model-out",
        default=None,
        help="Optional path to save a regressor fitted on all six bearings",
    )
    args = parser.parse_args(argv)

    try:
        report = evaluate(args.raw_dir, args.window)
        if args.model_out:
            data = load_dataset(args.raw_dir, args.window)
            features = np.vstack([item.features for item in data.values()])
            targets = np.concatenate([item.rul_s for item in data.values()])
            model = make_model()
            model.fit(features, targets)
            # joblib is already a project dependency; import only when needed.
            import joblib

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
