#!/usr/bin/env python3
"""Measure single-window Random Forest inference latency on the current host.

Runs the same 100 single-core ``predict_proba`` calls as ``train_rf.py`` so the
number can be compared across machines (training host vs Raspberry Pi).

Usage:
    python ml/benchmark_latency.py
    python ml/benchmark_latency.py --model /home/renad/pdm/ml/model.joblib \
        --meta /home/renad/pdm/ml/model_meta.json --csv /tmp/windows.csv \
        --note "Raspberry Pi 4 Model B"
"""

import argparse
import csv
import hashlib
import json
import os
import platform
import time

import joblib
import numpy as np
import sklearn

ML_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=os.path.join(ML_DIR, "model.joblib"))
    parser.add_argument("--meta", default=os.path.join(ML_DIR, "model_meta.json"))
    parser.add_argument("--csv", default=os.path.join(ML_DIR, "windows.csv"))
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    with open(args.meta) as f:
        features = json.load(f)["features"]
    with open(args.csv) as f:
        rows = list(csv.DictReader(f))[: args.n]
    if not rows:
        raise ValueError(f"No rows in {args.csv}")
    X = np.array(
        [[float(row[col]) for col in features] for row in rows], dtype=np.float32
    )

    model = joblib.load(args.model)
    model.n_jobs = 1
    for i in range(min(5, len(X))):  # warm-up, excluded from the measurement
        model.predict_proba(X[i : i + 1])

    start = time.perf_counter()
    for i in range(len(X)):
        model.predict_proba(X[i : i + 1])
    latency_ms = ((time.perf_counter() - start) / len(X)) * 1000.0

    proba = model.predict_proba(X)
    prediction_digest = hashlib.md5(np.round(proba, 6).tobytes()).hexdigest()

    result = {
        "host": platform.node(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "sklearn": sklearn.__version__,
        "numpy": np.__version__,
        "windows": len(X),
        "n_estimators": len(model.estimators_),
        "inference_latency_ms": round(latency_ms, 3),
        "prediction_digest": prediction_digest,
        "model": args.model,
        "note": args.note,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
