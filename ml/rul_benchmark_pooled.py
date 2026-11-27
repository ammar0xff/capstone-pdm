#!/usr/bin/env python3
"""Benchmark RUL v1: one pooled model on public run-to-failure bearings (XJTU-SY, NASA IMS, PRONOSTIA).

Predicts remaining life as a FRACTION of the run (1.0 = new, 0.0 = end of run) from causal vibration
health features (rms, kurtosis only, the two every dataset has). Leave-one-bearing-out evaluation.
OFFLINE RESULT / NAMED PUBLIC DATASETS. Not validated on the G12 fan motor. No claim for our motor.
Usage: python3 ml/rul_benchmark_pooled.py [--report ml/rul_benchmark_pooled_report.json]
"""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
LABEL = "OFFLINE RESULT / NAMED PUBLIC DATASETS / NOT OUR MOTOR"
MAXPTS = 500
FEATURE_NAMES = ["norm_log_rms_med20", "slope40", "kurt_mean20", "run_max_norm", "norm_log_rms_raw"]

def _trail(x, w, fn):
    return np.array([fn(x[max(0, i - w + 1): i + 1]) for i in range(len(x))])

def features(rms: np.ndarray, kurt: np.ndarray) -> np.ndarray:
    """Causal features: row i only reads samples 0..i."""
    lr = np.log(np.maximum(rms, 1e-12))
    ref = np.array([np.median(lr[: max(1, min(i + 1, 30))]) for i in range(len(lr))])
    n = lr - ref
    sm = _trail(n, 20, np.median)
    def slope(seg):
        if len(seg) < 5: return 0.0
        t = np.arange(len(seg), dtype=float); return float(np.polyfit(t, seg, 1)[0])
    sl = _trail(sm, 40, slope)
    km = _trail(kurt, 20, np.mean)
    mx = np.maximum.accumulate(sm)
    return np.column_stack([sm, sl * 40, km, mx, n])

def load_xjtu():
    out = {}
    for p in sorted((ROOT / "data/xjtu_sy_mendeley/csv").glob("bearing*.csv")):
        d = np.loadtxt(p, delimiter=",", skiprows=1)
        out["XJTU-SY " + p.stem] = (d[:, 2], d[:, 3])
    return out

def load_ims():
    rows = {}
    with open(ROOT / "data/nasa_ims/failed_bearings.csv", newline="") as f:
        for r in csv.DictReader(f): rows.setdefault(r["bearing"], []).append(r)
    return {"NASA IMS " + k: (np.array([float(r["rms1"]) for r in v]), np.array([float(r["kurt1"]) + 3.0 for r in v])) for k, v in rows.items()}

def load_pronostia(cache=ROOT / "ml" / "_pronostia_rms_kurt.npz"):
    from ml.rul_pronostia import acc_features
    if cache.exists():
        z = np.load(cache, allow_pickle=True); return {k: (z[k][0], z[k][1]) for k in z.files}
    out = {}
    for d in sorted((ROOT / "data/pronostia").glob("Bearing*")):
        fs = sorted(d.glob("acc_*.csv"))
        arr = np.array([acc_features(f)[1][:2] for f in fs])
        out["PRONOSTIA " + d.name] = (arr[:, 0], arr[:, 1]); print(d.name, len(fs), flush=True)
    np.savez(cache, **{k: np.array(v) for k, v in out.items()})
    return out

def build():
    data = {}
    data.update(load_xjtu()); data.update(load_ims()); data.update(load_pronostia())
    series = {}
    for k, (rms, kurt) in data.items():
        n = len(rms); X = features(rms, kurt); y = 1.0 - np.arange(n) / (n - 1)
        stride = max(1, n // MAXPTS)
        series[k] = (X[::stride], y[::stride], n)
    return series

def make_model():
    from sklearn.ensemble import RandomForestRegressor
    return RandomForestRegressor(n_estimators=40, min_samples_leaf=20, max_depth=6, random_state=0, n_jobs=-1)

def export_json(model, names, path):
    trees = []
    for e in model.estimators_:
        t = e.tree_
        trees.append({"f": t.feature.tolist(), "t": [round(float(v), 6) for v in t.threshold], "l": t.children_left.tolist(), "r": t.children_right.tolist(), "v": [round(float(v[0][0]), 5) for v in t.value]})
    json.dump({"label": LABEL, "features": FEATURE_NAMES, "target": "remaining life fraction of the run (1=new, 0=end)", "trained_on": names,
               "leave_one_bearing_out_mae_tail20": None, "trees": trees}, open(path, "w"), separators=(",", ":"))

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--report", default=str(ROOT / "ml/rul_benchmark_pooled_report.json"))
    a = ap.parse_args(argv)
    S = build(); names = sorted(S); res = {}
    for held in names:
        tr = [k for k in names if k != held]
        X = np.vstack([S[k][0] for k in tr]); y = np.concatenate([S[k][1] for k in tr])
        m = make_model().fit(X, y); Xh, yh, n = S[held]; p = np.clip(m.predict(Xh), 0, 1)
        tail = yh <= 0.2; late = yh <= 0.5
        const = float(np.median(y))
        res[held] = dict(snapshots=n, mae_all=float(np.mean(np.abs(p - yh))), mae_tail20=float(np.mean(np.abs(p[tail] - yh[tail]))),
            const_mae_all=float(np.mean(np.abs(const - yh))), const_mae_tail20=float(np.mean(np.abs(const - yh[tail]))),
            corr=float(np.corrcoef(p, yh)[0, 1]) if np.std(p) > 0 else 0.0,
            warn_hit=bool(np.any(p[tail] < 0.3)), false_warn_early=float(np.mean(p[yh > 0.5] < 0.3)))
        print(held, {k: round(v, 3) if isinstance(v, float) else v for k, v in res[held].items()}, flush=True)
    agg = {k: float(np.mean([r[k] for r in res.values()])) for k in ("mae_all", "mae_tail20", "const_mae_all", "const_mae_tail20", "corr", "false_warn_early")}
    agg["bearings_warned_in_last_20pct"] = int(sum(r["warn_hit"] for r in res.values())); agg["n_bearings"] = len(res)
    X = np.vstack([S[k][0] for k in names]); y = np.concatenate([S[k][1] for k in names])
    final = make_model().fit(X, y)
    export_json(final, names, ROOT / "ml/rul_benchmark_pooled_model.json")
    import joblib; joblib.dump({"model": final, "features": FEATURE_NAMES, "trained_on": names, "label": LABEL}, ROOT / "ml/rul_benchmark_pooled.joblib")
    json.dump({"label": LABEL, "target": "remaining life fraction of the run (1=new, 0=end)", "features": FEATURE_NAMES,
        "validation": "leave-one-bearing-out over all pooled bearings", "per_bearing": res, "aggregate": agg,
        "not_our_motor": True, "not_field_validated": True}, open(a.report, "w"), indent=1)
    print("AGG", json.dumps(agg)); return 0
if __name__ == "__main__": raise SystemExit(main())
