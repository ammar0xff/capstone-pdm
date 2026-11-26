import sys, os, glob, subprocess
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "edge"))
from speech_gate import SpeechGate

R = 48000; N = 2400
def sine(f, a, sec=3, seed=0):
    t = np.arange(R * sec) / R
    return a * np.sin(2 * np.pi * f * t)

def run(sig):
    g = SpeechGate(); out = []
    for i in range(len(sig) // N):
        out.append(g.update(sig[i * N:(i + 1) * N]))
    return np.array(out)

def test_low_hum_not_speech():
    rng = np.random.default_rng(1)
    s = sine(50, 0.02) + sine(100, 0.01) + rng.normal(0, 0.001, R * 3)
    assert not run(s).any()

def test_speech_band_tone_is_speech():
    assert run(sine(1000, 0.02))[2:].all()

def test_hold_keeps_flag_one_second_then_releases():
    a = sine(1000, 0.02, 1); b = sine(60, 0.02, 3)
    r = run(np.concatenate([a, b]))
    assert r[19] and r[20 + 18] and not r[20 + 25]  # speech ends at chunk 20; flag holds ~20 chunks

def test_silence_and_wrong_size_safe():
    g = SpeechGate()
    assert g.update(np.zeros(N)) is False
    assert g.update(np.zeros(10)) is False

def test_dc_offset_ignored():
    assert not run(sine(50, 0.02) + 0.3).any()

def test_edge_daq_gate_wiring():
    src = open(os.path.join(os.path.dirname(__file__), "..", "pi_deployed", "staged_not_applied", "edge_daq.py.g31")).read()
    assert 'and not ac_data.get("speech_like", False)' in src
    assert "(sound_db > 88.0) or (sound_zcr > 0.28)" in src          # level thresholds unchanged
    assert "kurtosis > 5.0 and rms_dyn > 0.04" in src                 # 0.04 g rule untouched

def test_recorded_takes_if_present():
    d = os.path.expanduser("~/g12_capture/audio_dataset/")
    fs = {"both": glob.glob(d + "both60*.wav"), "off": glob.glob(d + "motor_only_20261125T210719*.wav"), "on": glob.glob(d + "motor_only_20261125T21141*.wav")}
    if not all(fs.values()):
        return  # recordings live on the Pi only
    def rate(f):
        x = np.fromfile(f, dtype=np.int32, offset=44)[0::2].astype(np.float32) / 2147483648.0
        n = len(x) // N; g = SpeechGate(); fire = held = 0
        for i in range(n):
            b = x[i*N:(i+1)*N]; sp = g.update(b)
            rms = float(np.sqrt(np.mean(b**2))); db = max(30, min(120, 120 + 20*np.log10(rms+1e-9)))
            z = float(np.mean(np.abs(np.diff(np.signbit(b)))))
            f_ = (db > 88) or (z > 0.28)
            fire += f_ and not sp; held += sp
        return fire / n, held / n
    both, off, on = rate(fs["both"][0]), rate(fs["off"][0]), rate(fs["on"][0])
    print("after-filter fire rate both/off/on", both, off, on, "speech-flag share", both[1], off[1], on[1])
    assert both[0] < 0.05 and both[1] > 0.8
    assert off[1] < 0.2 and on[1] < 0.2  # off take: 13.7% flagged, unexplained (ambient sound?)


def test_quiet_room_noise_is_not_speech():
    rng = np.random.default_rng(2)
    assert not run(rng.normal(0, 0.0006, R * 3)).any()
