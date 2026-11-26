import sys,os,json,numpy as np
sys.argv=['x'];exec(open(os.path.expanduser('~/mf/adx.py')).read().split("res={'test_files'")[0])
sys.path.insert(0,'/tmp/g26');import vib3
J=json.load(open('/tmp/mafaulda3_trainonly.json'))
rng=np.random.default_rng(3);Y=[];Pp=[]
for i in te:
    x=D[i][1].astype(float);t=np.arange(len(x))/400.0
    for fsr in (249.0,):
        tt=np.arange(0,t[-1],1/fsr)+rng.normal(0,0.0003,int(t[-1]*fsr)+1)[:len(np.arange(0,t[-1],1/fsr))]
        tt=np.sort(tt);xs=np.interp(tt,t,x)
        xs=np.clip(xs+rng.normal(0,0.003,len(xs)),-16,16);xs=np.round(xs/0.0039)*0.0039
        for s in range(256,len(xs)-1,128):
            r=vib3.predict(J,vib3.resample_400(xs[s-256:s],tt[s-256:s])) if tt[s-1]-tt[s-256]>=0.64 else None
            if r: Y.append(lab[cls[i]]);Pp.append(r['class_id'])
Y=np.array(Y);Pp=np.array(Pp);print(len(Y),rep(Y,Pp))
