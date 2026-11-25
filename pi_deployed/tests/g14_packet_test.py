"""Offline packet checks: strict JSON for NaN input, null probability for rule states. Synthetic only."""
import json,math,re,textwrap,warnings;warnings.filterwarnings("ignore")
import importlib.util
src=open("edge_daq.py.g14").read()
m=re.search(r"def _finite_clean\(o\):.*?\n\n\ndef main",src,re.S)
g={"math":math};exec(m.group(0).rsplit("\n\n\ndef main",1)[0],g)
clean=g["_finite_clean"]
pk={"state":"Unknown","fault_proba":None,"vibration":{"rms_dyn":float("nan"),"k":[1.0,float("inf")]},"acoustic":{"db_spl":float("nan")}}
s=json.dumps(clean(pk),allow_nan=False); d=json.loads(s)
assert d["vibration"]["rms_dyn"] is None and d["vibration"]["k"][1] is None and d["fault_proba"] is None
try: json.dumps(pk,allow_nan=False); raise SystemExit("raw NaN should fail")
except ValueError: pass
# proba expression and CSV cell expression as written in source
assert 'not str(fault_label).startswith("Loud acoustic")' in src and src.count("else None")>=2
assert 'packet["fault_proba"] if packet["fault_proba"] is not None else ""' in src
assert "allow_nan=False" in src and src.count("_finite_clean(packet)")==2
print("PACKET TESTS PASS:", s)
