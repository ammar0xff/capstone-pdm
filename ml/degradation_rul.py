#!/usr/bin/env python3
"""Offline degradation-model RUL estimator — NOT field-validated.

This is an optional analysis tool. It fits a trend to a condition indicator
(time, value) history and estimates when that indicator would cross a
threshold supplied by the operator. It is deliberately separate from the
runtime four-class diagnosis: nothing here writes to Firebase, the dashboard
or the model, and no physical threshold is bundled with the code.

MathWorks' RUL taxonomy (Predictive Maintenance, Part 3) puts this under
*degradation models*: usable when a trendable condition indicator and a known
failure threshold exist. We have no field-validated failure threshold, so every
result is explicitly labelled "not field-validated" and the threshold is
recorded as operator-supplied.

Usage (on a host, offline):

    python3 ml/degradation_rul.py \\
        --history /path/to/raw_measurements.csv \\
        --time-column unix_time --value-column sound_rms \\
        --threshold '<operator value>' [--model linear|exponential]

The threshold is required: there is no invented default.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np

MODELS = ("linear", "exponential")
MIN_POINTS = 3

# Defaults match the columns written by edge/raw_measuree.py on the Pi.
DEFAULT_TIME_COLUMN = "unix_time"
DEFAULT_VALUE_COLUMN = "sound_rms"

LABEL = (
    "Degradation-model estimate with an operator-supplied threshold "
    "(not field-validated)"
)


def _finite_float(value: Any, name: str) -> float:
    """Convert to float or raise ValueError with a precise reason."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a finite number, got {value!r}") from None
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return number


def estimate_rul(
    history: Iterable[Sequence[float]], threshold: float, model: str = "linear"
) -> dict[str, Any]:
    """Estimate time to an operator-supplied threshold from a trend.

    Parameters
    ----------
    history : iterable of (time, value) pairs
        Time-ordered observations of one condition indicator. Times must be
        strictly increasing and at least three points are required.
    threshold : float
        Failure/action threshold supplied by the operator. No default exists.
    model : {"linear", "exponential"}
        ``linear`` fits value = slope * time + intercept. ``exponential``
        fits log(value) = slope * time + intercept, so values and threshold
        must be positive.

    Returns
    -------
    dict
        Always contains ``status`` (``estimated``, ``threshold_reached`` or
        ``no_increasing_trend``), ``rul_seconds``, ``estimated_cross_time``,
        ``slope``, ``intercept``, ``threshold``, ``threshold_source`` and
        ``label``. Every result carries the "not field-validated" label.

    Raises
    ------
    ValueError
        For invalid history, threshold or model. Garbage never returns a
        plausible-looking estimate.
    """

    if model not in MODELS:
        raise ValueError(f"unknown model {model!r}; expected one of {MODELS}")

    points = list(history)
    if len(points) < MIN_POINTS:
        raise ValueError(
            f"history needs at least {MIN_POINTS} points, got {len(points)}"
        )

    times: list[float] = []
    values: list[float] = []
    for index, point in enumerate(points):
        try:
            raw_time, raw_value = point
        except (TypeError, ValueError):
            raise ValueError(f"point {index} must be a (time, value) pair") from None
        times.append(_finite_float(raw_time, f"point {index} time"))
        values.append(_finite_float(raw_value, f"point {index} value"))

    for index in range(1, len(times)):
        if times[index] <= times[index - 1]:
            raise ValueError(
                "history times must be strictly increasing: "
                f"point {index - 1}={times[index - 1]}, point {index}={times[index]}"
            )

    threshold_value = _finite_float(threshold, "threshold")

    if model == "exponential":
        if threshold_value <= 0.0:
            raise ValueError("exponential threshold must be positive")
        if any(value <= 0.0 for value in values):
            raise ValueError("exponential history values must be positive")
        fit_values = [math.log(value) for value in values]
    else:
        fit_values = values

    time_array = np.asarray(times, dtype=float)
    fit_array = np.asarray(fit_values, dtype=float)
    slope, intercept = (
        float(coefficient) for coefficient in np.polyfit(time_array, fit_array, 1)
    )

    last_time = times[-1]
    last_value = values[-1]
    increasing = slope > 0.0
    estimated_cross_time: float | None = None

    if increasing:
        if model == "exponential":
            estimated_cross_time = (math.log(threshold_value) - intercept) / slope
        else:
            estimated_cross_time = (threshold_value - intercept) / slope

    if last_value >= threshold_value:
        status = "threshold_reached"
        rul_seconds: float | None = 0.0
    elif not increasing:
        status = "no_increasing_trend"
        rul_seconds = None
        estimated_cross_time = None
    else:
        status = "estimated"
        rul_seconds = max(0.0, estimated_cross_time - last_time)

    return {
        "status": status,
        "model": model,
        "rul_seconds": rul_seconds,
        "estimated_cross_time": estimated_cross_time,
        "slope": slope,
        "intercept": intercept,
        "threshold": threshold_value,
        "threshold_source": "operator-supplied",
        "label": LABEL,
        "last_time": last_time,
        "last_value": last_value,
        "n_points": len(points),
    }


def load_history(
    csv_path: str, time_column: str, value_column: str
) -> list[tuple[float, float]]:
    """Read (time, value) pairs from named CSV columns, validating every row."""

    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{csv_path} has no CSV header")
        missing = [
            column
            for column in (time_column, value_column)
            if column not in reader.fieldnames
        ]
        if missing:
            raise ValueError(
                f"missing column(s) in {csv_path}: {', '.join(missing)}; "
                f"available: {', '.join(reader.fieldnames)}"
            )

        history: list[tuple[float, float]] = []
        for row_number, row in enumerate(reader, start=2):
            raw_time = row.get(time_column)
            raw_value = row.get(value_column)
            if raw_time is None or raw_value is None:
                raise ValueError(f"row {row_number} is missing a required cell")
            history.append(
                (
                    _finite_float(raw_time, f"row {row_number} {time_column}"),
                    _finite_float(raw_value, f"row {row_number} {value_column}"),
                )
            )

    return history


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Offline degradation-model RUL estimate (not field-validated). "
            "The threshold is supplied by the operator; no default exists."
        )
    )
    parser.add_argument("--history", required=True, help="CSV history file")
    parser.add_argument(
        "--threshold",
        type=float,
        required=True,
        metavar="VALUE",
        help="operator-supplied failure/action threshold (required)",
    )
    parser.add_argument("--model", choices=MODELS, default="linear")
    parser.add_argument("--time-column", default=DEFAULT_TIME_COLUMN)
    parser.add_argument("--value-column", default=DEFAULT_VALUE_COLUMN)
    args = parser.parse_args(argv)

    try:
        history = load_history(args.history, args.time_column, args.value_column)
        result = estimate_rul(history, threshold=args.threshold, model=args.model)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
