"""Quantify what the stationary-extraction candidate does to each recording.

Usage: python3 mic_filter_report.py file1.wav [file2.wav ...]
No thresholds and no pass/fail. For each WAV (left channel) prints raw vs filtered
level features and the mic-side transient measures (crest factor, kurtosis, 99.9th
percentile amplitude), the first 3 s are skipped (the median needs history).
Read the rows side by side: motor-only should barely change, speech-only should
drop, and any transient loss shows in the crest/kurtosis/percentile columns.
"""
import sys, wave
import numpy as np
from stationary_extract import extract_stationary, level_features

R = 48000


def load(path):
    with wave.open(path, "rb") as w:
        ch, sw, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(w.getnframes())
    dt, sc = (np.int32, 2147483648.0) if sw == 4 else (np.int16, 32768.0)
    x = np.frombuffer(raw, dtype=dt).astype(np.float64) / sc
    if rate != R:
        raise SystemExit("%s: expected 48 kHz, got %d" % (path, rate))
    return x.reshape(-1, ch)[:, 0]


def shape(x):
    x = x - x.mean()
    s = x.std() + 1e-12
    return {"crest": float(np.max(np.abs(x)) / s), "kurt": float(np.mean((x / s) ** 4)),
            "p999": float(np.percentile(np.abs(x), 99.9))}


def main(paths):
    print("%-34s %s" % ("file / version", "rms      dB     zcr     crest  kurt   p99.9"))
    for p in paths:
        x = load(p)
        if len(x) < 5 * R:
            print(p, "too short (need >5 s)"); continue
        y = extract_stationary(x)
        sl = slice(3 * R, len(x) - 3000)
        for name, sig in (("raw", x[sl]), ("filtered", y[sl])):
            f = level_features(sig); s = shape(sig)
            print("%-34s %.5f %.1f  %.4f  %.2f  %.2f  %.5f" % (p.split("/")[-1][:24] + " " + name, f["rms"], f["db"], f["zcr"], s["crest"], s["kurt"], s["p999"]))


if __name__ == "__main__":
    main(sys.argv[1:] or sys.exit(__doc__))
