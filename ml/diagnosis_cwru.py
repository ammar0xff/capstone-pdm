#!/usr/bin/env python3
"""Four-class diagnosis benchmark on a real CWRU induction motor.

This is a **diagnosis** benchmark, not an RUL benchmark and not a measurement
from the capstone rig. It uses short, steady-state drive-end vibration recordings
from CWRU's 2 hp Reliance Electric induction motor: healthy, inner-race fault,
rolling-element fault and outer-race fault at 0 hp / about 1797 rpm. The four
classes are bearing-condition classes, not the deployed runtime taxonomy
(healthy / imbalance / bearing defect / thermal runaway), so this result must not
be presented as validation of the deployed classifier on our motor.

Windows are taken inside non-overlapping contiguous sample blocks. A fold holds
out whole blocks from every recording; windows from different folds never share
a vibration sample. The scaler and Random Forest are fitted only on training
folds. No future sample is used by a feature.

Usage:

    python3 ml/diagnosis_cwru.py [--report ml/diagnosis_cwru_report.json]

To use another motor's recordings, supply a manifest. File names are resolved
inside ``--data-dir``. ``md5`` is optional for a user-supplied file.

    python3 ml/diagnosis_cwru.py --data-dir /path/to/recordings \
        --manifest /path/to/classes.json --report /tmp/diagnosis.json

Manifest format:

    {
      "sample_rate_hz": 12000,
      "sources": [
        {"file": "healthy.mat", "channel": "DE_time",
         "class_name": "healthy", "class_id": 0, "md5": "..."}
      ]
    }
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.io import loadmat
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = ROOT / "data" / "cwru"
DEFAULT_REPORT = ROOT / "ml" / "diagnosis_cwru_report.json"

LABEL = "BENCHMARK / NOT OUR MOTOR / NOT FIELD-VALIDATED"
OPERATOR_LABEL = "OPERATOR-SUPPLIED / PROVENANCE UNVERIFIED / NOT FIELD-VALIDATED"
LICENCE_GAP = "[NEED: explicit CWRU licence; exact catalogue number]"
SOURCE_URLS = (
    "https://engineering.case.edu/bearingdatacenter/welcome",
    "https://engineering.case.edu/bearingdatacenter/bearing-information",
    "https://engineering.case.edu/bearingdatacenter/normal-baseline-data",
    "https://engineering.case.edu/bearingdatacenter/12k-drive-end-bearing-fault-data",
)
LICENSE_NOTE = (
    "The official CWRU pages state no explicit reuse licence: "
    "[NEED: explicit CWRU licence; exact catalogue number]. A republished copy "
    "on IEEE DataPort (DOI 10.21227/g8ts-zd15) is marked CC BY 4.0; CWRU remains "
    "the origin and that licence is not invented for the official files."
)

DEFAULT_CLASS_NAMES = ("healthy", "inner_race", "ball", "outer_race")
DEFAULT_SOURCES: tuple[dict[str, Any], ...] = (
    {
        "file": "Normal_0.mat",
        "channel": "X097_DE_time",
        "class_name": "healthy",
        "class_id": 0,
        "md5": "ee410e7243aefcd8b7120876556464e7",
    },
    {
        "file": "IR007_0.mat",
        "channel": "X105_DE_time",
        "class_name": "inner_race",
        "class_id": 1,
        "md5": "f14821b40412f33018279198da7f9cdc",
    },
    {
        "file": "B007_0.mat",
        "channel": "X118_DE_time",
        "class_name": "ball",
        "class_id": 2,
        "md5": "ff0f20588edc64140ae33888fcf1114a",
    },
    {
        "file": "OR007@6_0.mat",
        "channel": "X130_DE_time",
        "class_name": "outer_race",
        "class_id": 3,
        "md5": "e45f73f65cc3de4482d28d758503f2c1",
    },
)
EXCLUDED_SOURCES = (
    {
        "files": ["Normal_1.mat", "Normal_2.mat", "Normal_3.mat"],
        "reason": "healthy recordings at 1/2/3 hp; excluded to keep 0 hp / ~1797 rpm conditions comparable",
    },
    {
        "files": ["X118_BA_time", "X105_BA_time", "X130_BA_time"],
        "reason": "base accelerometer arrays are not the drive-end channel used here",
    },
)

DEFAULT_SAMPLE_RATE_HZ = 12000
DEFAULT_WINDOW_SAMPLES = 1024
DEFAULT_HOP_SAMPLES = 512
DEFAULT_BLOCK_SAMPLES = 4096
DEFAULT_N_FOLDS = 5
N_ESTIMATORS = 200
MAX_DEPTH = 12
RANDOM_STATE = 42

FEATURE_NAMES = (
    "rms",
    "peak",
    "std",
    "kurtosis",
    "skewness",
    "crest_factor",
    "shape_factor",
    "impulse_factor",
    "clearance_factor",
    "spectral_centroid_hz",
    "log_band_power_0_100hz",
    "log_band_power_100_500hz",
    "log_band_power_500_1500hz",
    "log_band_power_1500_3000hz",
    "log_band_power_3000_6000hz",
    "peak_fft_bin_hz",
)
BAND_EDGES_HZ = (
    (0.0, 100.0),
    (100.0, 500.0),
    (500.0, 1500.0),
    (1500.0, 3000.0),
    (3000.0, 6000.0),
)
EPS = 1e-12


@dataclass(frozen=True)
class Recording:
    """One hash-verified vibration recording with an explicit condition label."""

    file_name: str
    channel: str
    class_id: int
    class_name: str
    samples: np.ndarray


@dataclass(frozen=True)
class WindowSpan:
    """The exact sample span used by one feature vector."""

    group: str
    file_name: str
    start: int
    end: int


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_config(
    *, window_samples: int, hop_samples: int, block_samples: int, n_folds: int
) -> None:
    for name, value in (
        ("window_samples", window_samples),
        ("hop_samples", hop_samples),
        ("block_samples", block_samples),
        ("n_folds", n_folds),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
    if window_samples > block_samples:
        raise ValueError("window_samples cannot exceed block_samples")
    if hop_samples > window_samples:
        raise ValueError("hop_samples cannot exceed window_samples")
    if n_folds < 2:
        raise ValueError("n_folds must be at least 2")


def _read_sources(
    data_dir: Path,
    sources: Sequence[Mapping[str, Any]],
    *,
    block_samples: int,
    window_samples: int,
    verify_hashes: bool,
) -> tuple[list[Recording], tuple[str, ...]]:
    if not sources:
        raise ValueError("at least one labelled recording is required")
    class_ids = [int(source["class_id"]) for source in sources]
    if len(set(class_ids)) != len(class_ids) or min(class_ids) < 0:
        raise ValueError("class_id values must be unique non-negative integers")
    class_names: dict[int, str] = {}
    for source in sources:
        class_id = int(source["class_id"])
        name = str(source["class_name"]).strip()
        if not name:
            raise ValueError("class_name cannot be empty")
        if class_id in class_names and class_names[class_id] != name:
            raise ValueError("class_id maps to more than one class_name")
        class_names[class_id] = name
    if sorted(class_names) != list(range(len(class_names))):
        raise ValueError("class_id values must be contiguous from 0")

    recordings: list[Recording] = []
    for source in sources:
        path = data_dir / str(source["file"])
        if not path.is_file():
            raise ValueError(f"recording not found: {path}")
        expected_md5 = source.get("md5")
        actual_md5 = _md5(path)
        if verify_hashes and expected_md5 and actual_md5 != str(expected_md5):
            raise ValueError(f"source hash mismatch for {path.name}")
        contents = loadmat(str(path))
        channel = str(source["channel"])
        if channel not in contents:
            raise ValueError(f"channel {channel!r} not found in {path.name}")
        samples = np.asarray(contents[channel], dtype=float).ravel()
        if samples.size < block_samples + window_samples - 1:
            raise ValueError(f"{path.name} is too short for the configured blocks")
        if not np.isfinite(samples).all():
            raise ValueError(f"{path.name} contains non-finite vibration samples")
        recordings.append(
            Recording(
                file_name=path.name,
                channel=channel,
                class_id=int(source["class_id"]),
                class_name=class_names[int(source["class_id"])],
                samples=samples,
            )
        )
    ordered_names = tuple(class_names[class_id] for class_id in sorted(class_names))
    return recordings, ordered_names


def _window_features(
    window: np.ndarray,
    *,
    sample_rate_hz: int,
    band_edges: Sequence[tuple[float, float]],
) -> np.ndarray:
    centred = window - float(np.mean(window))
    rms = float(np.sqrt(np.mean(centred**2)))
    peak = float(np.max(np.abs(centred)))
    std = float(np.std(centred))
    abs_mean = float(np.mean(np.abs(centred)))
    root_abs_mean = float(np.sqrt(np.mean(np.sqrt(np.abs(centred)))))
    spectrum = np.abs(np.fft.rfft(centred * np.hanning(centred.size)))
    frequencies = np.fft.rfftfreq(centred.size, 1.0 / sample_rate_hz)
    total = float(np.sum(spectrum)) + EPS
    values = [
        rms,
        peak,
        std,
        float(np.mean(centred**4) / (std**4 + EPS)),
        float(np.mean(centred**3) / (std**3 + EPS)),
        peak / (rms + EPS),
        rms / (abs_mean + EPS),
        peak / (abs_mean + EPS),
        peak / (root_abs_mean**2 + EPS),
        float(np.sum(spectrum * frequencies) / total),
    ]
    for low, high in band_edges:
        power = float(np.sum(spectrum[(frequencies >= low) & (frequencies < high)]))
        values.append(float(np.log10(power / total + 1e-9)))
    values.append(float(frequencies[int(np.argmax(spectrum))]))
    feature_vector = np.asarray(values, dtype=float)
    if (
        feature_vector.shape != (len(FEATURE_NAMES),)
        or not np.isfinite(feature_vector).all()
    ):
        raise ValueError("non-finite diagnosis feature vector")
    return feature_vector


def _build_matrix(
    recordings: Sequence[Recording],
    *,
    sample_rate_hz: int,
    window_samples: int,
    hop_samples: int,
    block_samples: int,
    n_folds: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[WindowSpan], dict[str, int]]:
    features: list[np.ndarray] = []
    labels: list[int] = []
    spans: list[WindowSpan] = []
    for recording in recordings:
        samples = recording.samples
        block_starts = list(range(0, samples.size - window_samples + 1, block_samples))
        for block_index, block_start in enumerate(block_starts):
            block_end = min(block_start + block_samples, samples.size)
            starts = range(block_start, block_end - window_samples + 1, hop_samples)
            for start in starts:
                features.append(
                    _window_features(
                        samples[start : start + window_samples],
                        sample_rate_hz=sample_rate_hz,
                        band_edges=BAND_EDGES_HZ,
                    )
                )
                labels.append(recording.class_id)
                spans.append(
                    WindowSpan(
                        group=f"{recording.file_name}:block_{block_index:03d}",
                        file_name=recording.file_name,
                        start=start,
                        end=start + window_samples,
                    )
                )
    if not features:
        raise ValueError("no complete diagnosis windows were produced")

    by_file: dict[str, list[WindowSpan]] = {}
    for span in spans:
        by_file.setdefault(span.file_name, []).append(span)
    for file_name, file_spans in by_file.items():
        ordered = sorted(file_spans, key=lambda span: span.start)
        for earlier, later in zip(ordered, ordered[1:]):
            if earlier.group != later.group and later.start < earlier.end:
                raise ValueError(f"overlapping windows across folds in {file_name}")

    by_group: dict[str, list[WindowSpan]] = {}
    for span in spans:
        by_group.setdefault(span.group, []).append(span)
    groups_by_file: dict[str, list[str]] = {}
    for group, group_spans in by_group.items():
        groups_by_file.setdefault(group_spans[0].file_name, []).append(group)

    group_to_fold: dict[str, int] = {}
    for groups in groups_by_file.values():
        for index, group in enumerate(groups):
            group_to_fold[group] = min(n_folds - 1, index * n_folds // len(groups))

    folds = np.asarray([group_to_fold[span.group] for span in spans], dtype=int)
    return (
        np.vstack(features),
        np.asarray(labels, dtype=int),
        folds,
        spans,
        group_to_fold,
    )


def _round_scores(
    y_true: np.ndarray, y_pred: np.ndarray, class_names: Sequence[str]
) -> dict[str, Any]:
    accuracy = float(np.mean(y_true == y_pred))
    confusion = []
    per_class: dict[str, Any] = {}
    for class_id, name in enumerate(class_names):
        true_mask = y_true == class_id
        pred_mask = y_pred == class_id
        true_positive = int(np.sum(true_mask & pred_mask))
        false_positive = int(np.sum(~true_mask & pred_mask))
        false_negative = int(np.sum(true_mask & ~pred_mask))
        support = int(np.sum(true_mask))
        precision = (
            true_positive / (true_positive + false_positive)
            if (true_positive + false_positive)
            else 0.0
        )
        recall = true_positive / support if support else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
        confusion.append([true_positive, false_positive, false_negative, support])
        per_class[name] = {
            "support": support,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
    macro = {
        "precision": round(
            float(np.mean([item["precision"] for item in per_class.values()])), 4
        ),
        "recall": round(
            float(np.mean([item["recall"] for item in per_class.values()])), 4
        ),
        "f1": round(float(np.mean([item["f1"] for item in per_class.values()])), 4),
    }
    return {
        "accuracy": round(accuracy, 4),
        "macro": macro,
        "per_class": per_class,
        "confusion_tp_fp_fn_support": confusion,
    }


def evaluate(
    data_dir: str | Path = DEFAULT_DATA_DIR,
    *,
    manifest: Mapping[str, Any] | None = None,
    window_samples: int = DEFAULT_WINDOW_SAMPLES,
    hop_samples: int = DEFAULT_HOP_SAMPLES,
    block_samples: int = DEFAULT_BLOCK_SAMPLES,
    n_folds: int = DEFAULT_N_FOLDS,
    verify_hashes: bool = True,
) -> dict[str, Any]:
    """Evaluate a block-disjoint four-class diagnosis benchmark."""

    _validate_config(
        window_samples=window_samples,
        hop_samples=hop_samples,
        block_samples=block_samples,
        n_folds=n_folds,
    )
    config = dict(manifest or {})
    sources = config.get("sources", DEFAULT_SOURCES)
    sample_rate_hz = int(config.get("sample_rate_hz", DEFAULT_SAMPLE_RATE_HZ))
    if sample_rate_hz <= 0:
        raise ValueError("sample_rate_hz must be positive")
    recordings, class_names = _read_sources(
        Path(data_dir),
        sources,
        block_samples=block_samples,
        window_samples=window_samples,
        verify_hashes=verify_hashes,
    )
    matrix, labels, folds, spans, group_to_fold = _build_matrix(
        recordings,
        sample_rate_hz=sample_rate_hz,
        window_samples=window_samples,
        hop_samples=hop_samples,
        block_samples=block_samples,
        n_folds=n_folds,
    )
    if len(class_names) < 2:
        raise ValueError("at least two condition classes are required")
    for fold in range(n_folds):
        test_classes = {int(label) for label in labels[folds == fold]}
        if len(test_classes) != len(class_names):
            raise ValueError(f"fold {fold} does not contain every condition class")

    predictions = np.zeros(labels.shape, dtype=int)
    majority_predictions = np.zeros(labels.shape, dtype=int)
    per_fold: dict[str, Any] = {}
    for fold in range(n_folds):
        train = folds != fold
        test = folds == fold
        model = make_pipeline(
            StandardScaler(),
            RandomForestClassifier(
                n_estimators=N_ESTIMATORS,
                max_depth=MAX_DEPTH,
                random_state=RANDOM_STATE,
                n_jobs=1,
            ),
        )
        model.fit(matrix[train], labels[train])
        predictions[test] = model.predict(matrix[test])
        counts = np.bincount(labels[train], minlength=len(class_names))
        majority_predictions[test] = int(np.argmax(counts))
        test_groups = sorted(
            {span.group for span, group_fold in zip(spans, folds) if group_fold == fold}
        )
        train_groups = sorted(set(group_to_fold) - set(test_groups))
        if set(test_groups) & set(train_groups):
            raise ValueError("train and test groups overlap")
        per_fold[f"fold_{fold + 1}"] = {
            "test_groups": test_groups,
            "train_group_count": len(train_groups),
            "test_windows": int(np.sum(test)),
            "accuracy": round(float(np.mean(labels[test] == predictions[test])), 4),
            "majority_baseline_accuracy": round(
                float(np.mean(labels[test] == majority_predictions[test])), 4
            ),
        }

    scores = _round_scores(labels, predictions, class_names)
    baseline = _round_scores(labels, majority_predictions, class_names)
    operator_supplied = manifest is not None
    if operator_supplied:
        label = OPERATOR_LABEL
        task = "labelled condition diagnosis on operator-supplied recordings; not RUL"
        dataset = "operator-supplied labelled recordings"
        motor = "[NEED: motor identity and provenance]"
        source_urls: list[str] = []
        licence_note = "[NEED: operator-supplied reuse licence evidence]"
        licence_gap = "[NEED: motor identity and reuse licence]"
        operating_point = "operator-supplied"
        not_our_motor: bool | None = None
    else:
        label = LABEL
        task = (
            "four-class bearing-condition diagnosis on a real induction motor; "
            "not the deployed runtime taxonomy and not RUL"
        )
        dataset = "CWRU Bearing Data Center drive-end vibration recordings"
        motor = "2 hp Reliance Electric induction motor"
        source_urls = list(SOURCE_URLS)
        licence_note = LICENSE_NOTE
        licence_gap = LICENCE_GAP
        operating_point = "0 hp, approximately 1797 rpm"
        not_our_motor = True
    return {
        "status": "diagnosis_benchmark_complete",
        "label": label,
        "task": task,
        "source": {
            "dataset": dataset,
            "motor": motor,
            "source_urls": source_urls,
            "licence_note": licence_note,
            "licence_gap": licence_gap,
            "operator_supplied": operator_supplied,
            "our_motor": False,
            "operator_confirmed_failure": False,
            "field_validation": False,
            "source_files": [
                {
                    "file": recording.file_name,
                    "channel": recording.channel,
                    "class_name": recording.class_name,
                    "class_id": recording.class_id,
                    "md5": next(
                        str(item.get("md5", ""))
                        for item in sources
                        if str(item["file"]) == recording.file_name
                    ),
                }
                for recording in recordings
            ],
            "excluded_sources": [dict(item) for item in EXCLUDED_SOURCES]
            if manifest is None
            else [],
        },
        "data": {
            "n_recordings": len(recordings),
            "n_groups": len(group_to_fold),
            "n_windows": int(labels.size),
            "n_folds": n_folds,
            "class_names": list(class_names),
            "class_counts": {
                name: int(np.sum(labels == class_id))
                for class_id, name in enumerate(class_names)
            },
            "sample_rate_hz": sample_rate_hz,
            "operating_point": operating_point,
        },
        "method": {
            "validation": "grouped k-fold; contiguous 4096-sample blocks held out together",
            "block_samples": block_samples,
            "window_samples": window_samples,
            "hop_samples": hop_samples,
            "sample_disjoint_folds": True,
            "causal": True,
            "features": list(FEATURE_NAMES),
            "scaler": "StandardScaler fitted on training folds only",
            "model": (
                f"RandomForestClassifier(n_estimators={N_ESTIMATORS}, "
                f"max_depth={MAX_DEPTH}, random_state={RANDOM_STATE})"
            ),
            "seed": RANDOM_STATE,
            "baseline": "majority condition class fitted on training folds only",
        },
        "metrics": scores,
        "majority_class_baseline": baseline,
        "per_fold": per_fold,
        "readiness": {
            "not_our_motor": not_our_motor,
            "not_field_validated": True,
            "runtime_classifier_changed": False,
            "dashboard_or_firebase_changed": False,
            "rul_claim": None,
            "operator_action_required": True,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument(
        "--manifest", default=None, help="optional JSON class mapping for another motor"
    )
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument(
        "--no-verify-hash",
        action="store_true",
        help="skip source MD5 checks (only for user-supplied recordings)",
    )
    args = parser.parse_args(argv)
    try:
        manifest: dict[str, Any] | None = None
        if args.manifest:
            manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        report = evaluate(
            args.data_dir,
            manifest=manifest,
            verify_hashes=not args.no_verify_hash,
        )
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
