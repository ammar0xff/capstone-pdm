"""Offline synthetic test of the AI path (gate -> RF -> response). Synthetic features only; not rig data."""
import sys, math, collections
sys.path.insert(0, '.')
from rf_predictor import PdMClassifier
c = PdMClassifier('model.joblib')
base = dict(rms_dyn=0.03, peak_dyn=0.1, crest_factor=3.0, kurtosis=3.0, temp_c=26.0, temp_slope=0.0,
            sound_rms=0.01, sound_db=50.0, sound_zcr=0.02)
cases = {
 'quiet': {},
 'vib_high': dict(rms_dyn=0.9, peak_dyn=4.0, crest_factor=6.0, kurtosis=9.0),
 'thermal_slope': dict(temp_c=45.0, temp_slope=15.0),
 'acoustic_loud': dict(sound_rms=0.3, sound_db=90.0),
 'sentinel_1023': dict(rms_dyn=1023.75, peak_dyn=1023.75, crest_factor=1.0),
 'kurtosis_nan': dict(kurtosis=float('nan')),
}
res = collections.OrderedDict()
for n, o in cases.items():
    f = dict(base); f.update(o)
    cid, lab, p, adv, g = c.predict(f, return_gate_info=True)
    res[n] = (cid, lab, round(p, 2), g.get('gate_status'), g.get('rf_executed'))
    print(n, res[n])
# invariants
assert res['quiet'][4] is False, 'RF must not run on quiet window'
assert res['vib_high'][4] is True
for n, r in res.items():
    if not r[4]:
        print('NOTE', n, 'RF not run but predicted_class=', r[1], '(misleading if shown alone)')
print('OK')
