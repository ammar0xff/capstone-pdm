"""Speech-reduction CANDIDATE for the microphone LEVEL features. Offline only.

Hypothesis: with one microphone, the motor is the near-stationary part of the
signal and speech is the changing part. Per frequency bin, the median
magnitude over the last ~2 s is a causal estimate of the stationary (motor
and room hum) spectrum. A mask min(1, median/|X|) keeps what stays constant
and shrinks what jumps above it. The result is used ONLY to recompute mic
level features (rms, dB, ZCR). The raw features stay available beside it.

Known cost: any short transient is shrunk too, so mic-based impact detection
is lost by design. Fault transients are carried by the accelerometer, which
speech does not reach. Causal delay: about one second until the median adapts.
This is not wired into the Pi and has not been validated on real speech.
"""
import numpy as np


def extract_stationary(x, rate=48000, frame=2400, hop=1200, hist_frames=40, floor=0.05):
    x = np.asarray(x, dtype=np.float64)
    win = np.hanning(frame)
    n_frames = 1 + (len(x) - frame) // hop
    out = np.zeros(len(x))
    norm = np.zeros(len(x))
    mags = []
    for i in range(n_frames):
        seg = x[i * hop:i * hop + frame] * win
        spec = np.fft.rfft(seg)
        mag = np.abs(spec)
        mags.append(mag)
        hist = np.array(mags[-hist_frames:])
        med = np.median(hist, axis=0)
        mask = np.clip(med / (mag + 1e-12), floor, 1.0)
        y = np.fft.irfft(spec * mask, frame) * win
        out[i * hop:i * hop + frame] += y
        norm[i * hop:i * hop + frame] += win ** 2
    return out / np.maximum(norm, 1e-9)


def level_features(x):
    x = np.asarray(x, dtype=np.float64)
    rms = float(np.sqrt(np.mean(x ** 2)))
    zcr = float(np.mean(np.abs(np.diff(np.signbit(x).astype(np.int8)))))
    return {"rms": rms, "db": 120.0 + 20.0 * np.log10(rms + 1e-9), "zcr": zcr}
