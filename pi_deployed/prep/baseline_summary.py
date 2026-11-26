#!/usr/bin/env python3
"""Read-only summary of hot_backup.csv rows in the current 14-field layout. Changes nothing, proposes nothing live.
Usage: baseline_summary.py hot_backup.csv [--from EPOCH] [--to EPOCH] [--json out.json]
The file is UNLABELLED. Output describes what the sensors read in the chosen window. It says nothing about fault
detection accuracy, and the numbers are only a 'healthy baseline' if the user confirms the window was healthy."""
import csv, sys, json, argparse, collections, math
COLS = ["timestamp","seq","g_mag","rms_dyn","kurtosis","crest_factor","peak_dyn","temp_c","temp_slope","sound_db","sound_zcr","state","fault_label","fault_proba"]
FEATS = ["g_mag","rms_dyn","kurtosis","crest_factor","peak_dyn","temp_c","temp_slope","sound_db","sound_zcr"]
# Current rule values from edge_daq (ml/gate_thresholds.py EDGE). Reported against, never changed here.
T = {"sound_fault_db":88.0,"sound_fault_zcr":0.28,"vib_warn_kurtosis":5.0,"vib_fault_kurtosis":7.0,"vib_kurtosis_min_rms":0.03,
     "vib_warn_peak":0.25,"vib_fault_peak":0.40,"thermal_warn_temp":50.0,"thermal_warn_slope":5.0,"thermal_fault_temp":70.0,"thermal_fault_slope":10.0}
def pct(v, p):
    v = sorted(v); 
    if not v: return None
    k = (len(v)-1)*p/100; f = math.floor(k); c = math.ceil(k); return round(v[f]+(v[c]-v[f])*(k-f), 5)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("csv"); ap.add_argument("--from", dest="t0", type=float); ap.add_argument("--to", dest="t1", type=float); ap.add_argument("--json")
    a = ap.parse_args(); lay = collections.Counter(); rows = []
    for r in csv.reader(open(a.csv, newline="")):
        lay[len(r)] += 1
        if len(r) != 14: continue
        try: ts = float(r[0]); vals = {c: float(r[COLS.index(c)]) for c in FEATS}
        except ValueError: continue
        if (a.t0 and ts < a.t0) or (a.t1 and ts > a.t1): continue
        if any(math.isnan(x) or math.isinf(x) for x in vals.values()): continue
        vals["ts"] = ts; vals["state"] = r[11]; rows.append(vals)
    out = {"source": a.csv, "field_count_layouts": dict(lay), "rows_used": len(rows), "note": "unlabelled data; layout 14 only; older layouts not used and not modified"}
    if not rows: print(json.dumps(out, indent=1)); return
    ts = [r["ts"] for r in rows]; out["span_hours"] = round((max(ts)-min(ts))/3600, 2)
    gaps = sorted(b-a_ for a_, b in zip(ts, ts[1:])); out["gap_s"] = {"median": pct(gaps, 50), "p95": pct(gaps, 95), "p99": pct(gaps, 99), "max": round(gaps[-1], 2) if gaps else None, "gt_5s": sum(g > 5 for g in gaps)}
    out["state_counts"] = dict(collections.Counter(r["state"] for r in rows))
    out["features"] = {f: {"min": pct([r[f] for r in rows], 0), "p1": pct([r[f] for r in rows], 1), "p5": pct([r[f] for r in rows], 5), "p50": pct([r[f] for r in rows], 50),
                           "p95": pct([r[f] for r in rows], 95), "p99": pct([r[f] for r in rows], 99), "p99.9": pct([r[f] for r in rows], 99.9), "max": pct([r[f] for r in rows], 100)} for f in FEATS}
    n = len(rows); frac = lambda fn: round(sum(1 for r in rows if fn(r))/n, 4)
    out["rule_fire_share"] = {
        "sound_db_gt_88": frac(lambda r: r["sound_db"] > T["sound_fault_db"]), "sound_zcr_gt_0.28": frac(lambda r: r["sound_zcr"] > T["sound_fault_zcr"]),
        "kurtosis_gt_5_and_rms_gt_0.03": frac(lambda r: r["kurtosis"] > T["vib_warn_kurtosis"] and r["rms_dyn"] > T["vib_kurtosis_min_rms"]),
        "kurtosis_gt_7_and_rms_gt_0.03": frac(lambda r: r["kurtosis"] > T["vib_fault_kurtosis"] and r["rms_dyn"] > T["vib_kurtosis_min_rms"]),
        "peak_gt_0.25": frac(lambda r: r["peak_dyn"] > T["vib_warn_peak"]), "peak_gt_0.40": frac(lambda r: r["peak_dyn"] > T["vib_fault_peak"]),
        "temp_gt_50_or_slope_gt_5": frac(lambda r: r["temp_c"] > T["thermal_warn_temp"] or r["temp_slope"] > T["thermal_warn_slope"]),
        "temp_gt_70_or_slope_gt_10": frac(lambda r: r["temp_c"] > T["thermal_fault_temp"] or r["temp_slope"] > T["thermal_fault_slope"])}
    hr = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        h = int(r["ts"]//3600); hr[h][0] += 1; hr[h][1] += r["sound_db"] > T["sound_fault_db"]
    out["sound_db_gt_88_share_by_hour"] = {h: round(v[1]/v[0], 3) for h, v in sorted(hr.items()) if v[0] >= 60}
    out["reading_hints"] = ["A rule fire share far above 0 in a window the user confirms was healthy means that rule's threshold does not match this rig/mic.",
        "sound_db is an uncalibrated mic level. A motor-off recording is needed to separate room noise from motor noise.",
        "Candidate thresholds are decisions for the user after a confirmed healthy window. This script never writes or applies them."]
    print(json.dumps(out, indent=1))
    if a.json: json.dump(out, open(a.json, "w"), indent=1)
main()
