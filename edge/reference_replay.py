#!/usr/bin/env python3
"""Reference-data replay: a public benchmark recording used as a stand-in for the motor signal.

Runs the benchmark through the same steps the live DAQ uses (rms_dyn, SPC gate, rule-based fault
state, commissioning baseline) and writes packets in the live schema to its OWN state directory.
It never touches the live services, the live state file, Firebase or the 0.04 g gate. The dashboard
shows the source on screen. It does not claim the data was measured on our motor or validated on the rig.

Stand-in mapping (all printed in every packet under "reference_data"):
- Dataset: IEEE PHM 2012 PRONOSTIA (FEMTO-ST), bearing run-to-failure, 25.6 kHz, 2 axes, 2560 samples every 10 s.
- Per snapshot: remove DC per axis, band-limit to `band_hz` (default 180 Hz, the Pi stream band), take the
  2-axis dynamic magnitude, then rms_dyn / peak_dyn / crest / kurtosis as defined in edge_daq.py.
- The commissioning run starts after `settle_snapshots` (default 30, i.e. 5 minutes of run-in). Started at snapshot 1 it
  is refused by the drift rule, because PRONOSTIA's first minutes are higher than the steady level (checked on Bearing1_2).
- Amplitude is rescaled so the median of `ref_snapshots` snapshots right after the run-in equals `healthy_g`
  (default 0.03 g, the order of the rig's quiet level). The scale factor is reported.
- One snapshot stands for one gate window. The commissioning run uses `commission_snapshots` of them.
"""
import argparse
import glob
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "ml"))
import commissioning  # noqa: E402
from gate_thresholds import edge_flags  # noqa: E402

FS = 25600
SNAP_PERIOD_S = 10.0
DATASET = "PRONOSTIA"
LABEL_EN = "Reference data: PRONOSTIA, stand-in for the motor signal (public benchmark)"
LABEL_AR = "بيانات مرجعية: PRONOSTIA، بديل لإشارة الموتور (benchmark عام)"


def bandlimit(x, fc, fs=FS):
    X = np.fft.rfft(x)
    X[np.fft.rfftfreq(len(x), 1.0 / fs) > fc] = 0
    return np.fft.irfft(X, len(x))


def snapshot_features(h, v, band_hz=180.0):
    """rms_dyn, peak_dyn, crest, kurtosis of the band-limited 2-axis dynamic magnitude (same definitions as edge_daq.py)."""
    h = bandlimit(np.asarray(h, float) - np.mean(h), band_hz)
    v = bandlimit(np.asarray(v, float) - np.mean(v), band_hz)
    mag = np.sqrt(h * h + v * v)
    rms = float(np.sqrt(np.mean(mag ** 2)))
    peak = float(mag.max())
    mean = float(mag.mean()); var = float(np.var(mag))
    kurt = float(np.mean((mag - mean) ** 4) / var ** 2) if var > 1e-12 else 3.0
    return {"rms_dyn": rms, "peak_dyn": peak, "crest_factor": peak / (rms + 1e-9), "kurtosis": kurt}


def list_snapshots(bearing_dir):
    files = sorted(glob.glob(os.path.join(bearing_dir, "acc_*.csv")))
    if not files:
        raise FileNotFoundError("no acc_*.csv files in %s" % bearing_dir)
    return files


def read_snapshot(path):
    d = np.loadtxt(path, delimiter=",", usecols=(4, 5))
    return d[:, 0], d[:, 1]


TREND_WINDOW = 120   # snapshots (20 min of dataset time)
TREND_MIN = 60


def rul_trend(hist, ucl_fault, total, now_idx):
    """Straight-line trend of rms_dyn over the last TREND_WINDOW snapshots, extrapolated to the active fault limit.
    Same guards as the browser indicator (docs/EXPERIMENTAL_TREND_INDICATOR.md): slope > 0, R^2 >= 0.6, rise >= 3 residual sd
    and >= 10% of the mean. Dataset time. A trend estimate, not a validated RUL. The dataset's own end of run is reported
    next to it so the estimate can be compared with what happened."""
    out = {"status": "insufficient", "window": len(hist), "true_remaining_h": round((total - 1 - now_idx) * SNAP_PERIOD_S / 3600, 3),
           "note": "Trend estimate in dataset time, not a validated RUL. Dataset run-end shown for comparison."}
    if len(hist) < TREND_MIN:
        return out
    y = np.asarray(hist[-TREND_WINDOW:], float); x = np.arange(len(y)) * SNAP_PERIOD_S
    slope, icpt = np.polyfit(x, y, 1)
    fit = slope * x + icpt; res = y - fit
    ss_tot = float(np.sum((y - y.mean()) ** 2)); r2 = 1 - float(np.sum(res ** 2)) / ss_tot if ss_tot > 0 else 0.0
    rsd = float(np.std(res, ddof=2)); rise = slope * x[-1]
    cur = float(fit[-1])
    if cur >= ucl_fault:
        out["status"] = "at_limit"; return out
    if slope <= 0 or r2 < 0.6:
        out["status"] = "no_upward_trend"; return out
    if rise < 3 * rsd or rise < 0.10 * float(y.mean()):
        out["status"] = "no_upward_trend"; return out
    out["status"] = "estimate"
    out["hours_to_limit"] = round((ucl_fault - cur) / slope / 3600.0, 3)
    out["r2"] = round(r2, 2)
    return out


def make_packet(seq, feats, flags, baseline, source, comm, ref, now):
    mu, sg = baseline["mu"], baseline["sigma"]
    z = (feats["rms_dyn"] - mu) / sg
    if flags["any_fault"]:
        state, label = "Fault", "Rule-based fault state (elevated rms)"
        advice = "Vibration exceeded the 3-sigma limit of the active baseline. Rule result on reference data."
    elif flags["vib_warn"]:
        state, label = "Warning", "Rule-based warning (elevated rms)"
        advice = "Vibration exceeded the 2-sigma limit of the active baseline. Rule result on reference data."
    else:
        state, label = "Healthy", "No rule triggered"
        advice = "No alarm rule fired. This is a rule result on reference data, not a check of motor health."
    return {
        "timestamp": now, "uptime_s": round(seq * SNAP_PERIOD_S, 1), "seq": seq, "state": state,
        "fault_label": label, "fault_proba": 0.0, "fault_proba_source": "rule", "advice": advice,
        "input_valid": True, "online": True,
        "vibration": {"rms_dyn": round(feats["rms_dyn"], 5), "peak_dyn": round(feats["peak_dyn"], 4),
                      "crest_factor": round(feats["crest_factor"], 2), "kurtosis": round(feats["kurtosis"], 2),
                      "g_total": 1.0, "ax": 0.0, "ay": 0.0, "az": 1.0, "fs_hz": 400.0},
        "temperature": {"temp_c": 0.0, "slope_c_per_min": 0.0, "open_tc": 0},
        "acoustic": {"rms": 0.0, "peak": 0.0, "db_spl": 0.0, "zcr": 0.0, "crest_factor": 0.0, "status": "n/a"},
        "system": {"adxl_ok": True, "max6675_ok": False, "acoustic_ok": False, "storage_ok": True},
        "spc": {"baseline_source": source, "baseline_mu": mu, "baseline_sigma": sg, "z_score": round(z, 2),
                "ucl_warning": round(mu + 2 * sg, 4), "ucl_fault": round(mu + 3 * sg, 4)},
        "commissioning": comm,
        "reference_data": ref,
    }


def write_state(state_dir, pkt):
    tmp = os.path.join(state_dir, "latest_state.tmp")
    with open(tmp, "w") as f:
        json.dump(pkt, f)
    os.replace(tmp, os.path.join(state_dir, "latest_state.json"))


def run(bearing_dir, state_dir, speed=2.0, band_hz=180.0, healthy_g=0.03, ref_snapshots=30,
        commission_snapshots=180, min_samples=150, settle_snapshots=30, autostart=True, loop=False, max_snapshots=None,
        stop=lambda: False):
    """Replay `bearing_dir` into `state_dir`. speed = snapshots per second of wall time (0 = as fast as possible)."""
    os.makedirs(state_dir, exist_ok=True)
    files = list_snapshots(bearing_dir)
    if max_snapshots:
        files = files[:max_snapshots]
    name = os.path.basename(os.path.normpath(bearing_dir))
    cmd_file = os.path.join(state_dir, "commission_cmd.json")
    while True:
        # scale from the first ref_snapshots snapshots (healthy start of the run)
        ref = [snapshot_features(*read_snapshot(f), band_hz)["rms_dyn"]
               for f in files[settle_snapshots:settle_snapshots + ref_snapshots]]
        scale = healthy_g / float(np.median(ref))
        sim = {"t": 0.0}
        hist = []
        cm = commissioning.Commissioner(os.path.join(state_dir, "commissioned_baseline.json"),
                                        clock=lambda: sim["t"], target_s=commission_snapshots * SNAP_PERIOD_S,
                                        min_samples=min_samples, min_gap_s=SNAP_PERIOD_S * 0.5)
        cm.reset()  # every pass starts from the default baseline; an old replay baseline is kept under a dated name
        for i, f in enumerate(files):
            if stop():
                return
            if autostart and i == settle_snapshots:
                cm.start()  # after the run-in, as an operator would: the first minutes of a run are not steady
            if os.path.exists(cmd_file):
                try:
                    with open(cmd_file) as cf:
                        c = json.load(cf).get("cmd")
                finally:
                    os.remove(cmd_file)
                {"start": cm.start, "cancel": cm.cancel, "reset": cm.reset}.get(c, lambda: None)()
            sim["t"] = i * SNAP_PERIOD_S
            raw = snapshot_features(*read_snapshot(f), band_hz)
            feats = {"rms_dyn": raw["rms_dyn"] * scale, "peak_dyn": raw["peak_dyn"] * scale,
                     "crest_factor": raw["crest_factor"], "kurtosis": raw["kurtosis"]}
            cm.feed(feats["rms_dyn"], math.isfinite(feats["rms_dyn"]))
            hist.append(feats["rms_dyn"])
            b = cm.baseline
            lim = commissioning.limits(b)
            flags = edge_flags(feats["rms_dyn"], feats["kurtosis"], feats["peak_dyn"], 25.0, 0.0, 0.0, 0.0,
                               lim["ucl_warning"], lim["ucl_fault"])
            ref_info = {"label_en": LABEL_EN, "label_ar": LABEL_AR, "dataset": DATASET, "recording": name,
                        "snapshot": i + 1, "snapshots_total": len(files), "dataset_time_h": round(i * SNAP_PERIOD_S / 3600, 3),
                        "band_hz": band_hz, "amplitude_scale": round(scale, 5), "healthy_level_g": healthy_g,
                        "note": "Public benchmark recording replayed as a stand-in for the motor signal; amplitude rescaled.",
                        "rul_trend": rul_trend(hist, lim["ucl_fault"], len(files), i)}
            pkt = make_packet(i + 1, feats, flags, b, b["source"], cm.status(), ref_info, time.time())
            write_state(state_dir, pkt)
            if speed and speed > 0:
                time.sleep(1.0 / speed)
        if not loop:
            return pkt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--bearing-dir", required=True, help="e.g. data/pronostia/Bearing1_2")
    ap.add_argument("--state-dir", default="/dev/shm/pdm_reference", help="separate from the live state dir")
    ap.add_argument("--speed", type=float, default=2.0, help="snapshots per second (0 = fastest)")
    ap.add_argument("--band-hz", type=float, default=180.0)
    ap.add_argument("--healthy-g", type=float, default=0.03)
    ap.add_argument("--settle", type=int, default=30, help="snapshots of run-in before commissioning starts")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--no-autostart", action="store_true", help="do not start commissioning automatically")
    a = ap.parse_args(argv)
    live = os.environ.get("G12_STATE_DIR")
    if live and os.path.abspath(live) == os.path.abspath(a.state_dir):
        sys.exit("refusing to write into the live state directory")
    run(a.bearing_dir, a.state_dir, a.speed, a.band_hz, a.healthy_g, settle_snapshots=a.settle,
        autostart=not a.no_autostart, loop=a.loop)


if __name__ == "__main__":
    main()
