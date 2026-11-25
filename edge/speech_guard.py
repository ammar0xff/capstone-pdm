"""Speech guard CANDIDATE for the INMP441 microphone path.

Status: candidate only. Not wired into edge_daq.py and not used by any alarm
rule. Its thresholds are placeholders until it is calibrated on a motor-only
recording and tested on motor-only, noise-only and both recordings.

Idea (stated as a hypothesis, not a result): a running motor is close to
stationary, while speech has more energy in 300-3400 Hz than the motor-only
baseline AND that energy rises and falls a few times per second (syllables).
The guard watches both. While it says "speech-like", the caller keeps the last
non-speech mic values instead of updating them. It does not remove speech from
the signal and it does not claim to separate motor sound from speech.
"""
import numpy as np

SPEECH_BAND = (300.0, 3400.0)
MOD_BAND = (2.0, 8.0)


class SpeechGuard:
    def __init__(self, rate=48000, chunk_samples=2400, window_chunks=40,
                 k_sigma=4.0, mod_ratio=0.35):
        self.rate = rate
        self.chunk = chunk_samples
        self.frame_rate = rate / chunk_samples  # chunks per second (20 at 48k/2400)
        self.window = window_chunks  # 40 chunks = 2 s
        self.k_sigma = k_sigma
        self.mod_ratio = mod_ratio
        freqs = np.fft.rfftfreq(chunk_samples, 1.0 / rate)
        self._band = (freqs >= SPEECH_BAND[0]) & (freqs <= SPEECH_BAND[1])
        self._win = np.hanning(chunk_samples)
        self.baseline_mean = None
        self.baseline_std = None
        self.ring = []
        self.last_good = None

    def band_energy_db(self, chunk):
        x = np.asarray(chunk, dtype=np.float64)
        x = x - x.mean()
        spec = np.abs(np.fft.rfft(x * self._win)) ** 2
        return 10.0 * np.log10(spec[self._band].sum() + 1e-18)

    def calibrate(self, chunks):
        """Learn the motor-only speech-band energy from a motor-only recording."""
        e = np.array([self.band_energy_db(c) for c in chunks])
        if len(e) < self.window:
            raise ValueError("need at least one window of motor-only chunks")
        self.baseline_mean = float(e.mean())
        self.baseline_std = float(max(e.std(), 0.5))  # floor in dB
        self.ring = []

    def modulation_ratio(self, energies_db):
        """Share of envelope fluctuation power that sits at 2-8 Hz."""
        env = 10 ** (np.asarray(energies_db) / 20.0)
        env = env - env.mean()
        if len(env) < 8 or np.allclose(env, 0):
            return 0.0
        p = np.abs(np.fft.rfft(env)) ** 2
        f = np.fft.rfftfreq(len(env), 1.0 / self.frame_rate)
        total = p[1:].sum()
        if total <= 0:
            return 0.0
        m = (f >= MOD_BAND[0]) & (f <= MOD_BAND[1])
        return float(p[m].sum() / total)

    def update(self, chunk):
        """Feed one chunk. Returns dict with speech_like (None until calibrated)."""
        e = self.band_energy_db(chunk)
        self.ring.append(e)
        self.ring = self.ring[-self.window:]
        if self.baseline_mean is None or len(self.ring) < self.window:
            return {"speech_like": None, "band_db": e, "excess_db": None, "mod_ratio": None}
        recent = float(np.mean(self.ring[-10:]))  # last 0.5 s
        excess = (recent - self.baseline_mean) / self.baseline_std
        mod = self.modulation_ratio(self.ring)
        speech_like = bool(excess > self.k_sigma and mod > self.mod_ratio)
        return {"speech_like": speech_like, "band_db": e, "excess_db": excess, "mod_ratio": mod}

    def filter_metrics(self, metrics, verdict):
        """Hold the last non-speech metrics while speech-like. Reversible: caller
        can ignore this and keep raw metrics. Returns (metrics_to_use, held)."""
        if verdict["speech_like"] and self.last_good is not None:
            return self.last_good, True
        if not verdict["speech_like"]:
            self.last_good = dict(metrics)
        return metrics, False
