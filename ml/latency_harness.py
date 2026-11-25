#!/usr/bin/env python3
"""Per-window decision latency (gate + RF) with percentiles. Read-only, writes one JSON.

Measures PdMClassifier.predict() on the host it runs on, on a fixed synthetic feature set that
exercises both stage-1 outcomes (gate dormant, gate breached so the RF runs). It is a compute
latency of the decision step only. It does NOT include sampling, network or Firebase time, and a
number from a laptop says nothing about the Pi; run it on the Pi later, same command.

    python ml/latency_harness.py --n 2000 --out /tmp/latency.json --note "host label"
"""
import argparse, json, os, platform, statistics, sys, time

ML_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ML_DIR)
from rf_predictor import PdMClassifier  # noqa: E402

NOMINAL = {"rms_dyn": 0.01, "peak_dyn": 0.03, "crest_factor": 2.5, "kurtosis": 3.0, "temp_c": 25.0,
           "temp_slope": 0.1, "sound_rms": 0.01, "sound_db": 70.0, "sound_zcr": 0.05}
BREACH = dict(NOMINAL, rms_dyn=0.2, peak_dyn=0.5, crest_factor=5.0, kurtosis=8.0, temp_c=60.0)


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q / 100 * (len(xs) - 1))))]


def summarize(xs):
    return {"n": len(xs), "mean_ms": round(statistics.fmean(xs), 4), "p50_ms": round(pct(xs, 50), 4),
            "p95_ms": round(pct(xs, 95), 4), "p99_ms": round(pct(xs, 99), 4), "max_ms": round(max(xs), 4)}


def measure(clf, features, n, warmup=20):
    for _ in range(warmup):
        clf.predict(features)
    out = []
    for _ in range(n):
        t = time.perf_counter(); clf.predict(features); out.append((time.perf_counter() - t) * 1000.0)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--out", default="")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    clf = PdMClassifier()
    res = {"host": platform.platform(), "machine": platform.machine(), "python": platform.python_version(),
           "note": a.note, "model_loaded": clf.model is not None,
           "stage1_dormant": summarize(measure(clf, NOMINAL, a.n)),
           "stage1_breached_rf_runs": summarize(measure(clf, BREACH, a.n)),
           "scope": "decision compute only; excludes sampling, network, cloud"}
    txt = json.dumps(res, indent=2)
    print(txt)
    if a.out:
        with open(a.out, "w") as f:
            f.write(txt)


if __name__ == "__main__":
    main()
