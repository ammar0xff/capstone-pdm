"""Speech gate for the microphone level rule (G31).

Marks a short audio chunk as speech when at least SPEECH_FRAC of its energy sits in
300-3400 Hz, and holds that flag for HOLD_CHUNKS chunks (1 s at 20 chunks/s).
It only decides whether the mic level rule (dB / ZCR) may raise a Warning.
It never changes the raw mic numbers, the vibration gate or the 0.04 g rule.
Not a speech recognizer: music, TV and any loud broadband 300-3400 Hz sound also count as speech-like.
"""
import numpy as np

SPEECH_LO = 300.0
SPEECH_HI = 3400.0
SPEECH_FRAC = 0.30
HOLD_CHUNKS = 20
MIN_RMS = 0.001  # about 60 dB on this mic scale: quieter chunks are never called speech (room noise)


class SpeechGate:
    def __init__(self, rate=48000, chunk_samples=2400, speech_frac=SPEECH_FRAC, hold_chunks=HOLD_CHUNKS):
        self.speech_frac = speech_frac
        self.hold_chunks = hold_chunks
        freqs = np.fft.rfftfreq(chunk_samples, 1.0 / rate)
        self._band = (freqs >= SPEECH_LO) & (freqs <= SPEECH_HI)
        self._win = np.hanning(chunk_samples)
        self._n = chunk_samples
        self._since = 10 ** 9  # chunks since last speech-like chunk

    def band_fraction(self, chunk):
        x = np.asarray(chunk, dtype=np.float64)
        if len(x) != self._n:
            return 0.0
        x = x - x.mean()
        p = np.abs(np.fft.rfft(x * self._win)) ** 2
        tot = p.sum()
        if tot <= 1e-18:
            return 0.0
        return float(p[self._band].sum() / tot)

    def update(self, chunk):
        """Feed one chunk. Returns True while speech-like (including the hold time)."""
        x = np.asarray(chunk, dtype=np.float64)
        loud_enough = len(x) > 0 and float(np.sqrt(np.mean(x ** 2))) >= MIN_RMS
        if loud_enough and self.band_fraction(chunk) >= self.speech_frac:
            self._since = 0
        else:
            self._since += 1
        return self._since < self.hold_chunks
