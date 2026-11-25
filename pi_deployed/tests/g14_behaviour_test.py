"""Behaviour test: executes the REAL decision block cut out of edge_daq.py.g14 (and the live baseline edge_daq.py.new for comparison) with stubbed sensors. Synthetic inputs only."""
import math,textwrap,warnings;warnings.filterwarnings("ignore")
import sys
from rf_predictor import PdMClassifier
def load_block(path):
    src=open(path).read().splitlines()
    a=next(i for i,l in enumerate(src) if "# Stage 1: Coarse Statistical & Thermal Gating" in l)
    b=next(i for i,l in enumerate(src) if "raw_bin_str = f" in l)
    return textwrap.dedent("\n".join(src[a:b]))
class Led:
    def set(self,v):pass
def run(block,model,**kw):
    c=PdMClassifier(model); base=dict(last_temp_c=24.2,temp_slope=-0.2,rms_dyn=0.0078,peak_dyn=0.0247,kurtosis=3.0,crest_factor=3.17,sound_rms=0.0026,sound_db=68.0,sound_zcr=0.04)
    base.update(kw)
    g=dict(base,classifier=c,led=Led(),math=math,now_wall=1.0,ucl_fault=0.155,ucl_warning=0.13,FALLBACK_RESPONSE_PLAN={})
    exec(block,g)
    return g
new=load_block("edge_daq.py.g14"); old=load_block("edge_daq.py.new")
cases=[("normal",{}, "Healthy"),
("kurtosis 5.9 only (RF runs, rms low)",{"kurtosis":5.93},"Healthy"),
("loud sound only, 90 dB",{"sound_db":90.0},"Warning"),
("loud sound only, zcr 0.3",{"sound_zcr":0.3},"Warning"),
("vibration fault, rms 0.2 g",{"rms_dyn":0.2},"Fault"),
("thermal fault 72 C",{"last_temp_c":72.0,"temp_slope":11.0},"Fault"),
("mic NaN",{"sound_db":float("nan")},"Unknown"),
("vibration NaN",{"rms_dyn":float("nan")},"Unknown")]
ok=True
print(f"{'case':38s}{'OLD state':10s}{'NEW state':10s} label (new) | rf_ran proba_src")
for name,kw,exp in cases:
    o=run(old,"model.joblib",**kw); n=run(new,"model.joblib",**kw)
    flag="PASS" if n["state"]==exp else "FAIL"; ok&=n["state"]==exp
    print(f"{name:38s}{o['state']:10s}{n['state']:10s}{n['fault_label'][:52]} | rf_ran={n['rf_ran']} {flag}")
# model unavailable: fallback heuristic must not relabel
o=run(old,"/nonexistent",kurtosis=5.93,rms_dyn=0.05); n=run(new,"/nonexistent",kurtosis=5.93,rms_dyn=0.05)
print("model missing, kurt 5.9 + rms 0.05 (vib warn):  OLD label:",o["fault_label"],"| NEW label:",n["fault_label"])
ok&=("Bearing" not in n["fault_label"]) 
print("ALL PASS" if ok else "SOME FAIL")
