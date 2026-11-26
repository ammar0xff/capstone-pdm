import sys,os,json,numpy as np
sys.argv=['x'];exec(open(os.path.expanduser('~/mf/adx.py')).read().split("res={'test_files'")[0])
from sklearn.ensemble import ExtraTreesClassifier
FD=250.0;W=256;fr=np.fft.rfftfreq(W,1/FD);win=np.hanning(W)
BANDS=[(5,10),(10,15),(15,20),(20,25),(25,35),(35,50),(50,70),(70,100),(100,124)]
def feat(x,rich):
    w=x-x.mean();rms=np.sqrt((w**2).mean())
    if rms<=0:return None
    pk=np.abs(w).max();S=np.abs(np.fft.rfft(w*win))*2/win.sum();P=S**2
    be=[np.log10(P[(fr>=a)&(fr<b)].sum()+1e-12) for a,b in BANDS]
    f=[rms,pk,pk/rms,(w**4).mean()/(w**2).mean()**2]
    if rich:
        m=(fr>=8)&(fr<=100);k=np.argmax(S[m]);tot=P[m].sum()+1e-12
        cen=(fr[m]*P[m]).sum()/tot;f+=be+[fr[m][k],np.log10(S[m][k]+1e-9),cen,np.log10(rms)]
        f+=[be[i]-be[0] for i in range(1,len(be))]
    else: f+=[be[0]*0+np.log10(P[(fr>=a)&(fr<b)].sum()+1e-12) for a,b in [(10,25),(25,50),(50,100),(100,125)]]
    return np.array(f)
def stream(i,j,rng,fsr,gain):
    x=D[i][j].astype(float)*gain;t=np.arange(len(x))/400.0;n=int(t[-1]*fsr)
    tt=np.sort(np.arange(0,t[-1],1/fsr)[:n]+rng.normal(0,0.0003,n))
    xs=np.interp(tt,t,x);xs=np.clip(xs+rng.normal(0,0.003,len(xs)),-16,16);return np.round(xs/0.0039)*0.0039,tt
def wins(i,axes,rng,fsr,gain,rich,step):
    S=[stream(i,j,rng,fsr,gain) for j in axes];out=[]
    for s in range(W,len(S[0][0])+1,step):
        fs=[]
        for xs,tt in S:
            g=tt[s-1]-(W-1-np.arange(W))/FD;f=feat(np.interp(g,tt[s-W:s],xs[s-W:s]),rich)
            if f is None:break
            fs.append(f)
        else:
            if len(fs)>1: fs.sort(key=lambda f:-f[0])
            out.append(np.hstack(fs))
    return out
def build2(ids,axes,rng,reps,gj,rich,step):
    X=[];y=[]
    for r in range(reps):
        for i in ids:
            f=wins(i,axes,rng,float(rng.uniform(235,265)),rng.uniform(.8,1.2) if gj else 1.0,rich,step);X+=f;y+=[lab[cls[i]]]*len(f)
    return np.array(X),np.array(y)
res={}
for name,axes,rich,mdl in [('radial_rich',[1],True,'rf'),('three_rich',[0,1,2],True,'rf'),('three_rich_et',[0,1,2],True,'et')]:
    X,y=build2(tr,axes,np.random.default_rng(5),3,True,rich,64);Xt,yt=build2(te,axes,np.random.default_rng(9),1,False,rich,128)
    C=RandomForestClassifier if mdl=='rf' else ExtraTreesClassifier
    m=C(n_estimators=150,max_depth=12,min_samples_leaf=3,random_state=42,class_weight='balanced_subsample',n_jobs=-1).fit(X,y)
    res[name]=rep(yt,m.predict(Xt));print(name,len(y),len(yt),res[name],flush=True)
json.dump(res,open('/tmp/r250b.json','w'))
