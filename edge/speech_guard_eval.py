"""Offline check of the speech guard on the three joint recordings.

Usage: python3 speech_guard_eval.py motor.wav noise.wav both.wav
Each file: mono or stereo WAV (left channel used), 48 kHz. Records are
motor only, speech/noise only, and both. The guard is calibrated on the first
60% of motor.wav and scored on the rest of motor.wav, and on the other files.
Reports the share of chunks flagged speech-like. Pass criteria are set by the
team before running, for example: motor-only flagged under 5%, speech-only
over 80%, both over 60%. This script only measures, it decides nothing.
"""
import sys, wave
import numpy as np
from speech_guard import SpeechGuard

N = 2400


def load(path):
    with wave.open(path, "rb") as w:
        ch, sw, rate = w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(w.getnframes())
    if sw == 4:
        a = np.frombuffer(raw, dtype=np.int32).astype(np.float64) / 2147483648.0
    elif sw == 2:
        a = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    else:
        raise SystemExit("unsupported sample width")
    a = a.reshape(-1, ch)[:, 0]
    if rate != 48000:
        raise SystemExit("expected 48 kHz, got %d" % rate)
    n = len(a) // N
    return a[: n * N].reshape(n, N)


def score(g, chunks):
    g.ring = []
    flags = [g.update(c)["speech_like"] for c in chunks]
    valid = [f for f in flags if f is not None]
    return (sum(valid) / len(valid)) if valid else float("nan"), len(valid)


def main(motor, noise, both):
    m = load(motor)
    cut = int(len(m) * 0.6)
    g = SpeechGuard()
    g.calibrate(m[:cut])
    for name, ch in (("motor only (held-out 40%)", m[cut:]), ("speech/noise only", load(noise)), ("both", load(both))):
        frac, n = score(g, ch)
        print("%-28s flagged %.1f%% of %d scored chunks" % (name, 100 * frac, n))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
