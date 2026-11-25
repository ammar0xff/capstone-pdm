"""Offline contract tests of the Pi classifier path (rf_predictor.py + the rule layer read from edge_daq.py).
Synthetic inputs, nothing live, no faults induced. Run: python3 contract_tests.py"""
import warnings;warnings.filterwarnings("ignore")
from rf_predictor import PdMClassifier
c=PdMClassifier("model.joblib");nm=PdMClassifier("/nonexistent.joblib")
base=dict(rms_dyn=0.0078,peak_dyn=0.0247,crest_factor=3.17,kurtosis=3.0,temp_c=24.2,temp_slope=-0.2,sound_rms=0.0026,sound_db=68,sound_zcr=0.04)
def edge_rules(f):  # copy of the thresholds in edge_daq.py lines ~500-516 (ucl_warning 0.13, ucl_fault 0.155)
    fault=(f["temp_c"]>70 or f["temp_slope"]>10) or (f["rms_dyn"]>0.155 or (f["kurtosis"]>7 and f["rms_dyn"]>0.03) or f["peak_dyn"]>0.40) or (f["sound_db"]>88 or f["sound_zcr"]>0.28)
    warn=(f["temp_c"]>50 or f["temp_slope"]>5) or (f["rms_dyn"]>0.13 or (f["kurtosis"]>5 and f["rms_dyn"]>0.03) or f["peak_dyn"]>0.25)
    return "Fault" if fault else "Warning" if warn else "Healthy"
cases={"normal":base,"live kurtosis 5.9 only":{**base,"kurtosis":5.93},"loud speech: sound_db 90, rest normal":{**base,"sound_db":90},
"vib fault level rms 0.2 g":{**base,"rms_dyn":0.2},"thermal 72 C":{**base,"temp_c":72,"temp_slope":11},"mic NaN":{**base,"sound_db":float("nan")}}
for k,f in cases.items():
    r=c.predict(f,return_gate_info=True)
    print(f"{k:42s} edge state={edge_rules(f):8s} rf_executed={r[4]['rf_executed']} rf_class={r[0]} rf_proba={r[2]}")
print("model file missing, kurtosis 5.9 only ->",nm.predict({**base,"kurtosis":5.93},return_gate_info=True)[1:3],"(heuristic fallback, not a probability)")
