"""Runs the REAL main() loop of edge_daq with fake hardware (synthetic, no Pi). Scenarios: ADXL dead from start / healthy / dies later."""
import sys,os,types,time,json,threading,importlib.util,tempfile,struct,shutil
path=sys.argv[1]; scenario=sys.argv[2]; secs=float(sys.argv[3])
d=tempfile.mkdtemp(); os.environ["G12_STATE_DIR"]=d
shutil.copy("model.joblib",d) if os.path.exists("model.joblib") else None
class S: adxl_ok=(scenario!="dead"); t0=time.time(); opened=0; live=0
class Bus:
    def __init__(s,n): S.opened+=1; S.live+=1; s.c=False
    def close(s):
        if not s.c: S.live-=1; s.c=True
    def _ok(s):
        if scenario=="dead": return False
        if scenario=="dies": return time.time()-S.t0<float(sys.argv[4])
        return True
    def read_byte_data(s,a,r):
        if not s._ok(): raise OSError(121,"Remote I/O error")
        return 0xE5
    def write_byte_data(s,*a): pass
    def read_i2c_block_data(s,a,r,n):
        if not s._ok(): raise OSError(5,"Input/output error")
        import random
        return list(struct.pack("<hhh",random.randint(-3,3),random.randint(-3,3),256+random.randint(-3,3)))
class Spi:
    def open(s,b,dv): pass
    def close(s): pass
    max_speed_hz=0; mode=0
    def readbytes(s,n): return [0x03,0x20]
sys.modules["smbus2"]=types.SimpleNamespace(SMBus=Bus); sys.modules["spidev"]=types.SimpleNamespace(SpiDev=Spi)
import importlib.machinery
ld=importlib.machinery.SourceFileLoader("edge",path); spec=importlib.util.spec_from_loader("edge",ld); m=importlib.util.module_from_spec(spec); ld.exec_module(m)
th=threading.Thread(target=m.main,daemon=True); th.start()
f=os.path.join(d,"latest_state.json"); log=[]; t0=time.time()
while time.time()-t0<secs:
    try:
        raw=open(f).read(); p=json.loads(raw); import re; BAD=globals().get("BAD",0)+bool(re.search(r"\b(NaN|Infinity)\b",raw)); globals()["BAD"]=BAD; globals()["LAST"]=p; log.append((round(time.time()-t0,1),p["seq"],p["state"],p["input_valid"],p["fault_label"][:40],p["vibration"]["rms_dyn"]))
    except Exception: pass
    time.sleep(0.5)
seqs=[x[1] for x in log]
print(scenario,"| packets seen:",len(set(seqs)),"| seq advancing:",len(seqs)>1 and seqs[-1]>seqs[0],"| states:",sorted({(x[2],x[3]) for x in log}),"| labels:",sorted({x[4] for x in log}))
print("   last:",log[-1] if log else None,"| bus opens",S.opened,"live",S.live)

print("   raw packets with NaN/Infinity tokens:",globals().get("BAD"),"| last vibration:",{k:globals()["LAST"]["vibration"].get(k) for k in ("rms_dyn","kurtosis","peak_dyn","g_total")},"| rf_executed",globals()["LAST"].get("rf_executed"),"proba",globals()["LAST"].get("fault_proba"),"src",globals()["LAST"].get("fault_proba_source"),"adxl_ok",globals()["LAST"].get("adxl_ok"),"| ai",{k:globals()["LAST"]["ai"].get(k) for k in ("gate_status","predicted_class")})
