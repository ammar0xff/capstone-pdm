import sys,os,json,numpy as np
sys.argv=['x'];exec(open(os.path.expanduser('~/mf/adx.py')).read().split("res={'test_files'")[0])
FD=250.0;W=256;fr=np.fft.rfftfreq(W,1/FD);win=np.hanning(W)
def feat(x):
    w=x-x.mean();rms=np.sqrt((w**2).mean())
    if rms<=0:return None
    pk=np.abs(w).max();S=np.abs(np.fft.rfft(w*win))*2/win.sum();P=S**2
    be=lambda a,b:np.log10(P[(fr>=a)&(fr<b)].sum()+1e-12)
    return np.array([rms,pk,pk/rms,(w**4).mean()/(w**2).mean()**2,be(10,25),be(25,50),be(50,100),be(100,125)])
def stream(i,rng,jit=True,fsr=250.0,gain=1.0):
    x=D[i][1].astype(float)*gain;t=np.arange(len(x))/400.0
    tt=np.sort(np.arange(0,t[-1],1/fsr)[:int(t[-1]*fsr)]+(rng.normal(0,0.0003,int(t[-1]*fsr)) if jit else 0))[:int(t[-1]*fsr)]
    xs=np.interp(tt,t,x);xs=np.clip(xs+rng.normal(0,0.003,len(xs)),-16,16);return np.round(xs/0.0039)*0.0039,tt
def wins(xs,tt):
    out=[]
    for s in range(W,len(xs)+1,128):
        g=tt[s-1]-(W-1-np.arange(W))/FD;f=feat(np.interp(g,tt[s-W:s],xs[s-W:s]))
        if f is not None: out.append(f)
    return out
def build2(ids,rng,reps,gj):
    X=[];y=[]
    for r in range(reps):
        for i in ids:
            f=wins(*stream(i,rng,True,float(rng.uniform(235,265)),rng.uniform(.8,1.2) if gj else 1.0));X+=f;y+=[lab[cls[i]]]*len(f)
    return np.array(X),np.array(y)
rng=np.random.default_rng(5)
X,y=build2(tr,rng,3,True)
m=RandomForestClassifier(n_estimators=80,max_depth=10,min_samples_leaf=3,random_state=42,class_weight='balanced_subsample',n_jobs=-1).fit(X,y)
Xt,yt=build2(te,np.random.default_rng(9),1,False)
print('heldout REAL @~250Hz front end',len(yt),rep(yt,m.predict(Xt)),flush=True)
