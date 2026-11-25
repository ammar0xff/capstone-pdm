#!/usr/bin/env python3
"""Honest >80% RUL warning benchmark on NASA C-MAPSS FD001.

This is a *public simulated turbofan RUL benchmark*, not a measurement from our
induction motor, not field validation and not the deployed runtime classifier.
It uses explicit run-to-failure RUL labels and the published 30-cycle
short-horizon maintenance convention. The separate FMCG induction-motor RUL
result remains below 80% and is reported unchanged.

Source: NASA PCoE, DOI 10.5281/zenodo.15346912, CC BY 4.0.
See `data/cmapss/README.md` for file hashes and citation.

Usage:

    python3 ml/rul_cmapss_warning.py [--raw-dir data/cmapss] \
        [--report ml/rul_cmapss_warning_report.json]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import KFold

import train_rul_cmapss as cmapss

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RAW_DIR = ROOT / "data" / "cmapss"
DEFAULT_REPORT = ROOT / "ml" / "rul_cmapss_warning_report.json"

SOURCE_DOI = cmapss.SOURCE_DOI
SOURCE_URL = cmapss.SOURCE_URL
SOURCE_LICENSE = cmapss.SOURCE_LICENSE
FILE_HASHES = (
    cmapss.FILE_HASHES
    if hasattr(cmapss, "FILE_HASHES")
    else {
        "train_FD001.txt": "259f340bac32ce6fa8894815600fa757",
        "test_FD001.txt": "62316d1dd70f88a9a43a1e2690765437",
        "RUL_FD001.txt": "8f4a8b3d2692b2f7d8e72b344927bf4b",
    }
)

LABEL = (
    "RUL WARNING BENCHMARK / SIMULATED TURBOFAN / NOT OUR MOTOR / NOT FIELD-VALIDATED"
)
WARNING_HORIZON_CYCLES = 30
N_ESTIMATORS = 200
MAX_DEPTH = 12
MIN_SAMPLES_LEAF = 2
RANDOM_STATE = 42
N_FOLDS = 5
N_JOBS = 4


def verify_files(raw_dir: Path | str) -> None:
    """Fail loudly if any unmodified FD001 input is replaced."""

    raw_dir = Path(raw_dir)
    for name, expected in FILE_HASHES.items():
        path = raw_dir / name
        if not path.is_file():
            raise ValueError(f"missing C-MAPSS file: {name}")
        actual = hashlib.md5(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"MD5 mismatch for {name}: {actual}")


def last_cycles_by_unit(test: np.ndarray) -> dict[int, float]:
    """Last observed cycle per unit, without assuming a fixed unit count."""

    result: dict[int, float] = {}
    for unit in np.unique(test[:, 0]):
        unit = int(unit)
        rows = test[test[:, 0] == unit]
        if rows.shape[0] == 0:
            raise ValueError(f"unit {unit} has no rows")
        result[unit] = float(rows[-1, 1])
    return result


def test_rul_by_row(test: np.ndarray, true_rul: np.ndarray) -> np.ndarray:
    """Explicit RUL for every test row from NASA's last-cycle labels.

    The published label is the true RUL at each unit's final recorded cycle.
    An earlier row has that many cycles plus the cycles still visible in the
    truncated test trajectory. No model output is used here.
    """

    unit_ids = sorted(set(np.unique(test[:, 0]).astype(int)))
    expected_units = set(range(1, len(unit_ids) + 1))
    if unit_ids != list(expected_units):
        raise ValueError("test units must be contiguous from 1")
    if true_rul.ndim != 2 or true_rul.shape != (len(unit_ids), 1):
        raise ValueError(f"unexpected RUL label shape {true_rul.shape}")
    if np.any(true_rul[:, 0] < 0):
        raise ValueError("published RUL labels must be non-negative")
    last = last_cycles_by_unit(test)
    final_rul = {unit: float(true_rul[unit - 1, 0]) for unit in expected_units}
    return np.array(
        [
            final_rul[int(unit)] + (last[int(unit)] - float(cycle))
            for unit, cycle in zip(test[:, 0], test[:, 1])
        ],
        dtype=float,
    )


def make_model() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=N_ESTIMATORS,
        max_depth=MAX_DEPTH,
        min_samples_leaf=MIN_SAMPLES_LEAF,
        random_state=RANDOM_STATE,
        n_jobs=N_JOBS,
    )


def score_binary(expected: np.ndarray, predicted: np.ndarray) -> dict[str, Any]:
    """Scores with an explicit majority baseline; no threshold is optimised."""

    expected = np.asarray(expected, dtype=int)
    predicted = np.asarray(predicted, dtype=int)
    labels = [0, 1]
    matrix = confusion_matrix(expected, predicted, labels=labels)
    tn, fp, fn, tp = (int(value) for value in matrix.ravel())
    return {
        "n": int(expected.size),
        "positive_count": int(np.sum(expected == 1)),
        "accuracy": round(float(accuracy_score(expected, predicted)), 4),
        "majority_baseline": round(
            float(max(np.mean(expected == 1), np.mean(expected == 0))), 4
        ),
        "precision": round(
            float(precision_score(expected, predicted, zero_division=0)), 4
        ),
        "recall": round(float(recall_score(expected, predicted, zero_division=0)), 4),
        "f1": round(float(f1_score(expected, predicted, zero_division=0)), 4),
        "confusion_matrix": {
            "true_negative": tn,
            "false_positive": fp,
            "false_negative": fn,
            "true_positive": tp,
        },
    }


def evaluate(raw_dir: Path | str = DEFAULT_RAW_DIR) -> dict[str, Any]:
    """Train on train windows only, then score NASA's withheld test file."""

    raw_dir = Path(raw_dir)
    verify_files(raw_dir)
    train, test, true_rul = cmapss.load_raw(raw_dir)
    train_targets = cmapss.make_targets(train)
    x_train, y_train, units_train, _ = cmapss.build_windows(train, train_targets)
    x_test, _, units_test, test_rows = cmapss.build_windows(test)
    train_labels = (y_train <= WARNING_HORIZON_CYCLES).astype(int)

    # Unit-disjoint grouped cross-validation on the public training file. Every
    # window of a held unit is scored together; no cycle crosses a fold.
    unit_ids = np.arange(1, cmapss.N_UNITS + 1)
    per_fold: list[dict[str, Any]] = []
    folds = KFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    for fold, (fit_units, test_units) in enumerate(folds.split(unit_ids), start=1):
        fit_set = set(int(u) for u in unit_ids[fit_units])
        held_set = sorted(int(u) for u in unit_ids[test_units])
        fit_mask = np.array([int(u) in fit_set for u in units_train])
        held_mask = ~fit_mask
        model = make_model()
        model.fit(x_train[fit_mask], train_labels[fit_mask])
        predicted = model.predict(x_train[held_mask])
        scored = score_binary(train_labels[held_mask], predicted)
        per_fold.append(
            {
                "fold": fold,
                "units": held_set,
                "n_windows": int(np.sum(held_mask)),
                "accuracy": scored["accuracy"],
                "majority_baseline": scored["majority_baseline"],
                "precision": scored["precision"],
                "recall": scored["recall"],
                "f1": scored["f1"],
            }
        )

    final_model = make_model()
    final_model.fit(x_train, train_labels)

    row_rul = test_rul_by_row(test, true_rul)
    test_labels_all = (row_rul[test_rows] <= WARNING_HORIZON_CYCLES).astype(int)
    predicted_all = final_model.predict(x_test)
    last_window = cmapss.last_window_indices(units_test)
    last_positions = [last_window[u] for u in range(1, cmapss.N_UNITS + 1)]
    test_labels_last = (
        row_rul[test_rows[last_positions]] <= WARNING_HORIZON_CYCLES
    ).astype(int)
    predicted_last = predicted_all[last_positions]

    return {
        "status": "rul_warning_benchmark_complete",
        "label": LABEL,
        "source": {
            "dataset": "NASA C-MAPSS FD001 turbofan degradation benchmark",
            "simulated_environment": True,
            "doi": SOURCE_DOI,
            "url": SOURCE_URL,
            "license": SOURCE_LICENSE,
            "archive_md5": cmapss.ARCHIVE_MD5,
            "file_md5": dict(FILE_HASHES),
            "field_validation": False,
            "our_motor": False,
        },
        "method": {
            "task": "binary RUL warning: true RUL <= 30 cycles, not a continuous RUL claim",
            "warning_horizon_cycles": WARNING_HORIZON_CYCLES,
            "threshold_basis": (
                "published 30-cycle short-horizon maintenance-planning convention; "
                "fixed before scoring, not chosen from the test result"
            ),
            "model": "RandomForestClassifier",
            "n_estimators": N_ESTIMATORS,
            "max_depth": MAX_DEPTH,
            "min_samples_leaf": MIN_SAMPLES_LEAF,
            "random_state": RANDOM_STATE,
            "window_cycles": cmapss.WINDOW,
            "n_features": cmapss.N_FEATURES,
            "causal": True,
            "validation": "5 unit-disjoint folds; every window of a held unit stays together",
            "test_labels": "RUL_FD001.txt last-cycle labels, never used for training features",
            "tuned_on_test": False,
        },
        "data": {
            "train_rows": int(train.shape[0]),
            "test_rows": int(test.shape[0]),
            "train_windows": int(x_train.shape[0]),
            "test_windows": int(x_test.shape[0]),
            "train_units": cmapss.N_UNITS,
            "test_units": cmapss.N_UNITS,
        },
        "grouped_unit_cv": {
            "n_folds": N_FOLDS,
            "mean_accuracy": round(
                float(np.mean([fold["accuracy"] for fold in per_fold])), 4
            ),
            "mean_majority_baseline": round(
                float(np.mean([fold["majority_baseline"] for fold in per_fold])), 4
            ),
            "per_fold": per_fold,
        },
        "official_test_last_cycle": score_binary(test_labels_last, predicted_last),
        "official_test_all_windows": score_binary(test_labels_all, predicted_all),
        "readiness": {
            "not_our_motor": True,
            "not_field_validated": True,
            "field_validated_rul": False,
            "operator_alarm_threshold": False,
            "runtime_or_dashboard_claim_changed": False,
            "fmcg_result_unchanged": True,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "RUL warning benchmark on public NASA C-MAPSS FD001; "
            "simulated turbofan, not our motor, not field-validated."
        )
    )
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args(argv)

    try:
        report = evaluate(args.raw_dir)
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
