import sys, os, re, io, glob, types, threading, subprocess
import numpy as np
sys.path.insert(0, os.path.expanduser('~/pdm/edge'))
import edge_daq
SRC = open(os.path.expanduser('~/pdm/edge/edge_daq.py')).read()
line = re.search(r'is_sound_fault = (.+)', SRC).group(1)   # the deployed rule, verbatim
print('deployed rule:', line)
R=48000; N=2400
class FakeProc:
    def __init__(self, data, worker, log):
        self.data=data; self.pos=0; self.worker=worker; self.log=log
        self.stdout=self
    def read(self, n):
        if self.pos+n>len(self.data):
            self.worker.running=False; return b''
        m=self.worker.get_metrics()   # metrics produced from the previous chunk
        if self.pos>0: self.log.append(m)
        b=self.data[self.pos:self.pos+n]; self.pos+=n; return b
    def terminate(self): pass
    def wait(self, timeout=None): pass
def run_stream(mono):
    st=np.zeros((len(mono),2),dtype=np.int32)
    st[:,0]=np.clip(mono*2147483648.0,-2147483648,2147483647).astype(np.int32)
    data=st.tobytes()
    w=edge_daq.AcousticWorker()
    log=[]
    orig=subprocess.Popen
    edge_daq.subprocess.Popen=lambda *a,**k: FakeProc(data,w,log)
    edge_daq.time.sleep=lambda s: None
    w.run()
    edge_daq.subprocess.Popen=orig
    return log
def evaluate(log):
    fire=0; sp=0
    for m in log:
        ac_data=m; sound_db=m['db_spl']; sound_zcr=m['zcr']
        if eval(line): fire+=1
        raw=(sound_db>88.0) or (sound_zcr>0.28)
        sp+= bool(m.get('speech_like'))
    return len(log), fire, sum(((m['db_spl']>88.0) or (m['zcr']>0.28)) for m in log), sp
def show(name, mono):
    n,fire,raw,sp=evaluate(run_stream(mono))
    print('%-34s chunks=%d  rule-would-fire-without-gate=%d (%.1f%%)  Warning-with-gate=%d (%.1f%%)  speech_like=%d (%.1f%%)'%(name,n,raw,100*raw/n,fire,100*fire/n,sp,100*sp/n))
D=os.path.expanduser('~/g12_capture/audio_dataset/')
def wav(p): return np.fromfile(p,dtype=np.int32,offset=44)[0::2].astype(np.float32)/2147483648.0
show('REAL motor+talk take (60 s)', wav(glob.glob(D+'both60*.wav')[0]))
show('REAL motor-on take (60 s)', wav(glob.glob(D+'motor_only_20261125T21141*.wav')[0]))
show('REAL 23:07 take (60 s)', wav(glob.glob(D+'motor_only_20261125T210719*.wav')[0]))
rng=np.random.default_rng(7); t=np.arange(R*10)/R
# synthetic loud speech-like: 130 Hz voiced source with formants 500/1500/2500 Hz, 4 Hz syllable envelope
src=sum(np.sin(2*np.pi*130*k*t)/k for k in range(1,25))
form=sum(np.sin(2*np.pi*f*t+k)*a for k,(f,a) in enumerate([(500,1),(1500,.6),(2500,.3)]))
sp=(src*0.5+form)*(0.6+0.4*np.sin(2*np.pi*4*t)); sp=sp/np.sqrt(np.mean(sp**2))*0.06   # rms 0.06 -> ~105 dB
show('SYNTH loud speech-like (105 dB)', sp.astype(np.float32))
# loud non-speech: 120 Hz thump bursts, and white-noise burst, each 1 s loud inside 5 s quiet hum
hum=0.004*np.sin(2*np.pi*50*np.arange(R*5)/R)
def burst(sig): 
    o=hum.copy(); o[R*2:R*3]=sig[:R]; return o.astype(np.float32)
tt=np.arange(R)/R
show('SYNTH loud 120 Hz thump (1 s of 5 s)', burst(0.2*np.sin(2*np.pi*120*tt)))
show('SYNTH loud white-noise burst (1 s of 5)', burst(rng.normal(0,0.1,R)))
show('SYNTH loud speech burst (1 s of 5)', burst(sp[:R]*1.0))
show('SYNTH quiet hum only (5 s)', hum.astype(np.float32))
