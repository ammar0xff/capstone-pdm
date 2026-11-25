import os, sys, unittest
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "edge"))
from speech_guard import SpeechGuard

RATE, N = 48000, 2400
rng = np.random.default_rng(0)


def motor(n_chunks):
    t = np.arange(n_chunks * N) / RATE
    x = 0.02 * np.sin(2 * np.pi * 120 * t) + 0.01 * np.sin(2 * np.pi * 240 * t) + 0.003 * rng.standard_normal(len(t))
    return x.reshape(n_chunks, N)


def synthetic_speechlike(n_chunks):
    # SYNTHETIC stand-in: band-limited noise amplitude-modulated at 4 Hz. Not real speech.
    t = np.arange(n_chunks * N) / RATE
    noise = rng.standard_normal(len(t))
    spec = np.fft.rfft(noise); f = np.fft.rfftfreq(len(t), 1 / RATE)
    spec[(f < 300) | (f > 3400)] = 0
    band = np.fft.irfft(spec, len(t))
    band = band / band.std() * 0.05
    env = 0.5 * (1 + np.sin(2 * np.pi * 4 * t))
    return (band * env).reshape(n_chunks, N)


class T(unittest.TestCase):
    def setUp(self):
        self.g = SpeechGuard(RATE, N)
        self.g.calibrate(motor(120))

    def run_stream(self, chunks):
        out = []
        for c in chunks:
            out.append(self.g.update(c)["speech_like"])
        return out

    def test_uncalibrated_returns_none(self):
        g = SpeechGuard(RATE, N)
        self.assertIsNone(g.update(motor(1)[0])["speech_like"])

    def test_motor_only_not_flagged(self):
        r = self.run_stream(motor(100))
        self.assertFalse(any(x for x in r if x is not None))

    def test_synthetic_modulated_band_flagged(self):
        mix = motor(100) + synthetic_speechlike(100)
        r = self.run_stream(mix)
        self.assertTrue(sum(1 for x in r if x) > 30)

    def test_hold_keeps_last_good(self):
        g = self.g
        good = {"rms": 0.01}
        g.filter_metrics(good, {"speech_like": False})
        used, held = g.filter_metrics({"rms": 0.5}, {"speech_like": True})
        self.assertTrue(held)
        self.assertEqual(used["rms"], 0.01)


if __name__ == "__main__":
    unittest.main()
