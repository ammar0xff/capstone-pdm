import os, sys, unittest
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "edge"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stationary_extract import extract_stationary, level_features
import test_speech_guard as t

R = 48000
SK, TAIL = 3 * R, 3000  # skip 3 s warm-up and the unnormalised tail


class T(unittest.TestCase):
    def test_synthetic_behaviour(self):
        m = t.motor(200).reshape(-1)
        s = t.synthetic_speechlike(200).reshape(-1)
        sl = slice(SK, -TAIL)
        mo = level_features(extract_stationary(m)[sl])["rms"] / level_features(m[sl])["rms"]
        sp = level_features(extract_stationary(s)[sl])["rms"] / level_features(s[sl])["rms"]
        self.assertGreater(mo, 0.9)   # motor-like level kept (synthetic)
        self.assertLess(sp, 0.6)      # modulated band noise reduced (synthetic)


if __name__ == "__main__":
    unittest.main()
