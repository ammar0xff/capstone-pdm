#!/usr/bin/env python3
"""Target-rig run-to-failure RUL trainer and evaluator.

This is the last code path needed to turn the existing condition-monitoring
project into predictive maintenance *once the operator supplies real
run-to-failure data from our rig*. It reads a CSV of the same nine features that
the runtime Stage-2 classifier already uses, builds causal trailing-window
features, labels every window in seconds to an operator-accepted failure
timestamp, evaluates with leave-one-run-out validation, and can save a final
regressor for estimating RUL from a current partial run.

Nothing here imports the classifier, writes Firebase, changes the dashboard or
touches Stage-1/Stage-2 behaviour. The report is deliberately labelled **not
field-validated** until the operator accepts the failure endpoint and reviews
the measured metrics.

CSV contract (one row per logged window):

    run_id,timestamp,failure_timestamp,rms_dyn,peak_dyn,crest_factor,
    kurtosis,temp_c,temp_slope,sound_db,sound_zcr[,sound_rms]

``timestamp`` and ``failure_timestamp`` are Unix seconds. ``failure_timestamp``
must be constant for a run and at or after its last sample. ``sound_rms`` is
optional; when it is absent it is reconstructed from ``sound_db`` with the
inverse of the transform already used in ``edge/edge_daq.py``, strictly inside
the unclamped 30–120 dB range.

Usage:

    python3 ml/rul_from_rig.py --history /path/to/rig_runs.csv \
        --report ml/rul_from_rig_report.json --model-out ml/rul_from_rig_model.joblib

    python3 ml/rul_from_rig.py --mode predict --model ml/rul_from_rig_model.joblib \
        --history /path/to/current_run.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = ROOT / "ml" / "rul_from_rig_report.json"
DEFAULT_MODEL = ROOT / "ml" / "rul_from_rig_model.joblib"

BASE_REQUIRED_COLUMNS: tuple[str, ...] = (
    "run_id",
    "timestamp",
    "rms_dyn",
    "peak_dyn",
    "crest_factor",
    "kurtosis",
    "temp_c",
    "temp_slope",
    "sound_db",
    "sound_zcr",
)
FAILURE_COLUMN = "failure_timestamp"
SOUND_RMS_COLUMN = "sound_rms"
SOUND_DB_COLUMN = "sound_db"

# Exactly the nine inputs passed to the deployed Stage-2 Random Forest in
# ml/rf_predictor.py. No new sensor or physical threshold is introduced.
FEATURE_NAMES: tuple[str, ...] = (
    "rms_dyn",
    "peak_dyn",
    "crest_factor",
    "kurtosis",
    "temp_c",
    "temp_slope",
    "sound_rms",
    "sound_db",
    "sound_zcr",
)
N_FEATURES = len(FEATURE_NAMES)
WINDOW = 10
N_ESTIMATORS = 100
RANDOM_STATE = 42
N_JOBS = 4
MIN_WINDOW = 2

LABEL = (
    "Target-rig run-to-failure RUL evaluation - "
    "not field-validated until the failure endpoint and report are operator-accepted"
)
PREDICTION_LABEL = (
    "Target-rig RUL estimate from an operator-fitted model - "
    "not field-validated until operator acceptance"
)


@dataclass(frozen=True)
class RigRun:
    """Causal features and labels for one run-to-failure experiment."""

    run_id: str
    n_rows: int
    first_time_s: float
    last_time_s: float
    failure_time_s: float | None
    duration_s: float
    features: np.ndarray
    times_s: np.ndarray
    rul_s: np.ndarray | None


@dataclass(frozen=True)
class RigDataset:
    """Validated runs plus provenance of the acoustic feature path."""

    runs: dict[str, RigRun]
    total_rows: int
    sound_rms_source: str


def _finite_float(value: Any, name: str) -> float:
    if value is None:
        raise ValueError(f"{name} is missing")
    if isinstance(value, str) and not value.strip():
        raise ValueError(f"{name} is empty")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a finite number, got {value!r}") from None
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return number


def _trailing_features(sequence: np.ndarray, window: int) -> np.ndarray:
    """Trailing mean/std/trend; row i reads only rows up to and including i."""

    if sequence.shape[0] < window:
        raise ValueError(f"need at least {window} rows, got {sequence.shape[0]}")
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


def _sound_rms(row: dict[str, str], row_number: int, derived: bool) -> float:
    if derived:
        sound_db = _finite_float(row.get(SOUND_DB_COLUMN), f"row {row_number} sound_db")
        # edge/edge_daq.py clamps outside [30, 120] dB, so the inverse is only
        # valid strictly inside that range. Never guess a clamped value.
        if not 30.0 < sound_db < 120.0:
            raise ValueError(
                f"row {row_number} sound_db={sound_db} is clamped; "
                "supply an explicit sound_rms column instead"
            )
        return 10.0 ** ((sound_db - 120.0) / 20.0)

    raw = row.get(SOUND_RMS_COLUMN)
    value = _finite_float(raw, f"row {row_number} sound_rms")
    if value < 0.0:
        raise ValueError(f"row {row_number} sound_rms must be non-negative")
    return value


def load_runs(
    csv_path: str | Path,
    window: int = WINDOW,
    require_failure: bool = True,
) -> RigDataset:
    """Validate a rig CSV and build causal features for every complete run."""

    if window < MIN_WINDOW:
        raise ValueError(f"window must be at least {MIN_WINDOW}, got {window}")

    required = list(BASE_REQUIRED_COLUMNS)
    if require_failure:
        required.append(FAILURE_COLUMN)

    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} has no CSV header")
        missing = [column for column in required if column not in reader.fieldnames]
        if missing:
            raise ValueError(
                f"missing column(s) in {csv_path}: {', '.join(missing)}; "
                f"available: {', '.join(reader.fieldnames)}"
            )
        rows = list(reader)

    if not rows:
        raise ValueError(f"{csv_path} has no data rows")

    if SOUND_RMS_COLUMN in reader.fieldnames:
        present = [bool((row.get(SOUND_RMS_COLUMN) or "").strip()) for row in rows]
        if not all(present) and any(present):
            raise ValueError(
                f"{csv_path} must fill sound_rms on every row or omit it on every row"
            )
        derived = not any(present)
    else:
        derived = True

    grouped: dict[str, list[tuple[float, float | None, list[float]]]] = {}
    for row_number, row in enumerate(rows, start=2):
        run_id = (row.get("run_id") or "").strip()
        if not run_id:
            raise ValueError(f"row {row_number} has an empty run_id")
        time_s = _finite_float(row.get("timestamp"), f"row {row_number} timestamp")
        failure_s: float | None = None
        if require_failure:
            failure_s = _finite_float(
                row.get(FAILURE_COLUMN), f"row {row_number} {FAILURE_COLUMN}"
            )
        values = [
            _finite_float(row.get(name), f"row {row_number} {name}")
            for name in FEATURE_NAMES
            if name != SOUND_RMS_COLUMN
        ]
        sound_rms_index = FEATURE_NAMES.index(SOUND_RMS_COLUMN)
        values.insert(sound_rms_index, _sound_rms(row, row_number, derived))
        grouped.setdefault(run_id, []).append((time_s, failure_s, values))

    runs: dict[str, RigRun] = {}
    for run_id, entries in grouped.items():
        times = np.asarray([entry[0] for entry in entries], dtype=float)
        if times.shape[0] < window:
            raise ValueError(
                f"run {run_id!r} has {times.shape[0]} rows; need at least {window}"
            )
        for index in range(1, times.shape[0]):
            if times[index] <= times[index - 1]:
                raise ValueError(
                    f"run {run_id!r} timestamps must strictly increase: "
                    f"row {index - 1}={times[index - 1]}, row {index}={times[index]}"
                )

        sequence = np.asarray([entry[2] for entry in entries], dtype=float)
        features = _trailing_features(sequence, window)
        window_times = times[window - 1 :]

        failure_time: float | None = None
        rul: np.ndarray | None = None
        if require_failure:
            failures = {entry[1] for entry in entries}
            if len(failures) != 1:
                raise ValueError(
                    f"run {run_id!r} has different {FAILURE_COLUMN} values across rows"
                )
            failure_time = float(next(iter(failures)))
            if failure_time < times[-1]:
                raise ValueError(
                    f"run {run_id!r} failure_timestamp {failure_time} "
                    f"is before its last sample {times[-1]}"
                )
            rul = failure_time - window_times
            if np.any(rul < 0.0):
                raise ValueError(f"run {run_id!r} produced negative RUL labels")

        duration = (
            (failure_time - float(times[0]))
            if failure_time is not None
            else float(times[-1] - times[0])
        )
        runs[run_id] = RigRun(
            run_id=run_id,
            n_rows=int(times.shape[0]),
            first_time_s=float(times[0]),
            last_time_s=float(times[-1]),
            failure_time_s=failure_time,
            duration_s=float(duration),
            features=features,
            times_s=window_times,
            rul_s=rul,
        )

    return RigDataset(
        runs=runs,
        total_rows=len(rows),
        sound_rms_source=(
            "explicit sound_rms column"
            if not derived
            else "derived from sound_db using edge/edge_daq.py inverse transform"
        ),
    )


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


def evaluate(csv_path: str | Path, window: int = WINDOW) -> dict[str, Any]:
    """Leave-one-run-out RUL evaluation on supplied target-rig failure runs."""

    dataset = load_runs(csv_path, window, require_failure=True)
    run_ids = list(dataset.runs)
    if len(run_ids) < 2:
        raise ValueError(
            f"need at least two complete run-to-failure runs, got {len(run_ids)}"
        )

    last_expected: list[float] = []
    last_predicted: list[float] = []
    last_baseline: list[float] = []
    all_expected: list[float] = []
    all_predicted: list[float] = []
    per_run: dict[str, dict[str, Any]] = {}

    for held in run_ids:
        train_ids = [run_id for run_id in run_ids if run_id != held]
        train_features = np.vstack(
            [dataset.runs[run_id].features for run_id in train_ids]
        )
        train_targets = np.concatenate(
            [dataset.runs[run_id].rul_s for run_id in train_ids]
        )
        model = make_model()
        model.fit(train_features, train_targets)

        held_run = dataset.runs[held]
        assert held_run.rul_s is not None  # guaranteed by require_failure=True
        prediction = model.predict(held_run.features)
        baseline = float(
            np.median([dataset.runs[run_id].duration_s for run_id in train_ids])
        )
        last_expected.append(float(held_run.rul_s[-1]))
        last_predicted.append(float(prediction[-1]))
        last_baseline.append(baseline)
        all_expected.extend(held_run.rul_s.tolist())
        all_predicted.extend(prediction.tolist())
        per_run[held] = {
            "n_rows": held_run.n_rows,
            "duration_s": held_run.duration_s,
            "failure_time_s": held_run.failure_time_s,
            "predicted_last_rul_s": float(prediction[-1]),
            "baseline_last_rul_s": baseline,
        }

    return {
        "status": "target_rig_evaluation_complete",
        "label": LABEL,
        "source": {
            "data_origin": (
                "operator-supplied run-to-failure CSV for the target rig; "
                "provenance must be attached by the operator"
            ),
            "history_path": str(csv_path),
            "field_validation": False,
            "failure_endpoint": (
                "operator-accepted failure_timestamp column; "
                "no physical failure threshold is inferred"
            ),
            "sound_rms_source": dataset.sound_rms_source,
        },
        "method": {
            "model": "RandomForestRegressor",
            "n_estimators": N_ESTIMATORS,
            "random_state": RANDOM_STATE,
            "window_rows": window,
            "n_features": int(features_per_window()),
            "feature_names": [
                f"{name}_{stat}"
                for name in FEATURE_NAMES
                for stat in ("mean", "std", "trend")
            ],
            "validation": "leave-one-run-out; all windows of the held run",
            "rul_endpoint": "failure_timestamp - window timestamp",
            "causality": "trailing statistics read only rows up to the labelled window",
        },
        "data": {
            "runs": run_ids,
            "n_runs": len(run_ids),
            "n_rows": dataset.total_rows,
            "n_windows": len(all_expected),
        },
        "last_window": {
            "n_runs": len(run_ids),
            **_scores(last_expected, last_predicted),
        },
        "all_windows": {
            "n_windows": len(all_expected),
            **_scores(all_expected, all_predicted),
        },
        "constant_baseline_last_window": {
            "description": "median duration of the other complete runs",
            **_scores(last_expected, last_baseline),
        },
        "per_run": per_run,
        "readiness": {
            "code_path": "ready",
            "runtime_or_dashboard_changed": False,
            "operator_acceptance_required": (
                "[NEED: operator-accepted failure endpoint and reviewed metric report]"
            ),
        },
    }


def features_per_window() -> int:
    return 3 * N_FEATURES


def fit_final_model(
    csv_path: str | Path, window: int = WINDOW
) -> RandomForestRegressor:
    """Fit a deployable regressor on every supplied target-rig failure run."""

    dataset = load_runs(csv_path, window, require_failure=True)
    features = np.vstack([run.features for run in dataset.runs.values()])
    targets = np.concatenate([run.rul_s for run in dataset.runs.values()])
    model = make_model()
    model.fit(features, targets)
    return model


def predict_current_rul(
    model_path: str | Path, history_csv: str | Path, window: int = WINDOW
) -> dict[str, Any]:
    """Estimate RUL for the last window of one current, incomplete run."""

    dataset = load_runs(history_csv, window, require_failure=False)
    if len(dataset.runs) != 1:
        raise ValueError(
            f"prediction history must contain exactly one run, got {len(dataset.runs)}"
        )
    run = next(iter(dataset.runs.values()))
    import joblib

    model = joblib.load(model_path)
    raw = float(model.predict(run.features)[-1])
    return {
        "status": "prediction_complete",
        "label": PREDICTION_LABEL,
        "run_id": run.run_id,
        "n_rows": run.n_rows,
        "n_windows": int(run.features.shape[0]),
        "last_timestamp_s": run.last_time_s,
        "rul_seconds": max(0.0, raw),
        "raw_rul_seconds": raw,
        "model_path": str(model_path),
        "field_validation": False,
        "operator_action_required": True,
        "source": {"sound_rms_source": dataset.sound_rms_source},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Target-rig run-to-failure RUL trainer/evaluator; "
            "not field-validated until operator acceptance."
        )
    )
    parser.add_argument("--mode", choices=("evaluate", "predict"), default="evaluate")
    parser.add_argument("--history", required=True, help="rig run CSV (Unix seconds)")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--window", type=int, default=WINDOW)
    parser.add_argument(
        "--model-out", default=None, help="save a regressor fitted on all runs"
    )
    parser.add_argument("--model", default=None, help="model to use in predict mode")
    args = parser.parse_args(argv)

    try:
        if args.mode == "evaluate":
            report = evaluate(args.history, args.window)
            if args.model_out:
                model = fit_final_model(args.history, args.window)
                import joblib

                joblib.dump(model, args.model_out)
            report_path = Path(args.report)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            if not args.model:
                raise ValueError("--model is required in predict mode")
            result = predict_current_rul(args.model, args.history, args.window)
            print(json.dumps(result, indent=2, sort_keys=True))
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
