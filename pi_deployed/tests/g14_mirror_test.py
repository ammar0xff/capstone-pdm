"""Consumer mapping test: build the REAL payload block from firebase_mirror.py.g15 for synthetic edge packets; check fields and strict JSON."""
import json,re,textwrap,time
src=open("firebase_mirror.py.g15").read().splitlines()
a=next(i for i,l in enumerate(src) if l.strip().startswith("payload = {"))
b=next(i for i,l in enumerate(src) if "if LIGHT_PAYLOAD" in l)
blk=textwrap.dedent("\n".join(src[a:b]))
def build(data):
    g={"data":data,"time":time}; exec(blk,g); return g["payload"]
base={"timestamp":1.0,"seq":5,"state":"Healthy","fault_label":"Normal Operation","fault_proba":None,"fault_proba_source":"rule_derived_no_probability","input_valid":True,"rf_executed":True,"ai":{"gate_status":"Rule layer: no alarm; RF ran (unvalidated)","confidence":None},"vibration":{},"temperature":{},"acoustic":{}}
cases={"healthy":base,"unknown":dict(base,state="Unknown",input_valid=False,rf_executed=False,fault_label="Input invalid (sensor value not finite)"),
"warn_sound":dict(base,state="Warning",fault_label="Loud acoustic level (uncalibrated), not a fault diagnosis"),
"model_fault":dict(base,state="Fault",fault_proba=0.91,fault_proba_source="model"),
"old_pi":{k:v for k,v in base.items() if k not in("fault_proba","fault_proba_source","input_valid","rf_executed")}}
for n,d in cases.items():
    p=build(d); s=json.dumps(p,allow_nan=False); q=json.loads(s)
    print(n,{k:q.get(k) for k in("state","proba","proba_source","input_valid","rf_executed")})
    assert q["proba"] is None or d.get("fault_proba_source")=="model"
    if n=="old_pi": assert q["input_valid"] is None and q["rf_executed"] is None and q["proba"] is None
    if n=="unknown": assert q["input_valid"] is False and q["rf_executed"] is False
    if n=="model_fault": assert q["proba"]==0.91 and q["proba_source"]=="model"
print("MIRROR MAPPING PASS")
