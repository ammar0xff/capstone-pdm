import re,struct,time,sys,types
def load(path):
    s=open(path).read(); a=s.index("class ADXL345Driver"); b=s.index("class AcousticWorker")
    return s[a:b]
class State: live=0; opened=0; fail=True
class FakeBus:
    def __init__(self,n):
        State.opened+=1; State.live+=1; self.closed=False
    def close(self):
        if not self.closed: State.live-=1; self.closed=True
    def read_byte_data(self,a,r):
        if State.fail: raise OSError(121,"Remote I/O error")
        return 0xE5
    def write_byte_data(self,*a): pass
    def read_i2c_block_data(self,a,r,n):
        if State.fail: raise OSError(5,"Input/output error")
        return list(struct.pack("<hhh",1,2,3))
class FakeSpi:
    def __init__(self): State.opened+=1; State.live+=1; self.c=False
    def open(self,b,d): 
        if State.fail: raise OSError(5,"spi")
    def close(self):
        if not self.c: State.live-=1; self.c=True
    def readbytes(self,n): return [0x0C,0x80]
def run(path,secs=2.0):
    State.live=State.opened=0; State.fail=True
    g=dict(smbus2=types.SimpleNamespace(SMBus=FakeBus),spidev=types.SimpleNamespace(SpiDev=FakeSpi),struct=struct,time=time)
    exec(load(path),g)
    a=g["ADXL345Driver"](); t=g["MAX6675Driver"]()
    t0=time.time(); n=0
    while time.time()-t0<secs: a.read_raw(); t.read_temp(); n+=1
    return State.opened,State.live,n,a,t,g
for path in ("edge_daq.py.g19","edge_daq.py.g20"):
    try: o,l,n,a,t,g=run(path)
    except Exception as e: print(path,"ERR",e); continue
    print(f"{path}: failing sensors for 2 s -> opens={o} still-open handles={l} loop calls={n}")
o,l,n,a,t,g=run("edge_daq.py.g20")
assert l<=2 and o<=2*(2+3)+4, (o,l); print("g20: bounded opens and handles: PASS")
State.fail=False; time.sleep(1.1)
assert a.read_raw()==(1,2,3); assert t.read_temp()[0] is not None; print("g20: recovers after sensor returns (after <=1 s backoff): PASS")
assert State.live<=2; print("g20: handles after recovery:",State.live)
