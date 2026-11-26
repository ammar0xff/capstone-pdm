import glob,json,hashlib,os,numpy as np,sys
sys.path.insert(0,os.path.expanduser('~/mf'))
from feat3 import feats
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import balanced_accuracy_score,f1_score
CL=['normal','imbalance','horiz','vert','bearing']
fs=sorted(glob.glob('/tmp/mf/cache3/*.npz'));names=[os.path.basename(f)[:-4] for f in fs]
R=[{'cls':str(d['cls']),'grp':str(d['grp'])} for d in (np.load(f,allow_pickle=True) for f in fs)]
cls=np.array([d['cls'] for d in R]);grp=np.array([d['grp'] for d in R])
for k,i in enumerate(np.where(cls=='normal')[0]): grp[i]='normal_%d'%(k%5)
held=set()
for c in CL:
    gs=sorted({grp[i] for i in range(len(R)) if cls[i]==c},key=lambda g:hashlib.md5(g.encode()).hexdigest())
    held|=set(gs[:max(1,round(len(gs)*0.25))])
keep=['normal','imbalance','horiz','vert'];lab={'normal':0,'imbalance':1,'horiz':2,'vert':2}
idx=[i for i in range(len(R)) if cls[i] in keep]
tr=[i for i in idx if grp[i] not in held];te=[i for i in idx if grp[i] in held]
D={i:np.load('/tmp/mf/dec/'+names[i]+'.npy') for i in idx}
def adxl(x,rng,lim,noise=0.003):
    x=x+rng.normal(0,noise,x.shape);x=np.clip(x,-lim,lim);return np.round(x/0.0039)*0.0039
AX={'three':[0,1,2],'radial':[1]}
def F(i,ax,mode,rng,lim=16,gain=1.0):
    out=[]
    for j in AX[ax]:
        x=D[i][j]*gain
        if mode=='adxl': x=adxl(x,rng,lim)
        out.append(feats(x,0)[:,:8])
    return np.hstack(out)
def build(ids,ax,mode,rng,lim=16,reps=1,gj=False):
    X=[];y=[]
    for r in range(reps):
        for i in ids:
            f=F(i,ax,mode,rng,lim,rng.uniform(.8,1.2) if gj else 1.0);X.append(f);y+=[lab[cls[i]]]*len(f)
    return np.vstack(X),np.array(y)
rf=lambda:RandomForestClassifier(n_estimators=150,max_depth=10,random_state=42,class_weight='balanced_subsample',n_jobs=-1)
def rep(y,p): return {'balanced_acc':round(float(balanced_accuracy_score(y,p)),4),'macro_f1':round(float(f1_score(y,p,average='macro')),4),'acc':round(float((y==p).mean()),4)}
res={'test_files':len(te),'train_files':len(tr),'note':'REAL MAFAULDA held-out recordings; train-time noise/gain augmentation is SIMULATED; eval front end (noise 3 mg, 3.9 mg/LSB, clip) is SIMULATED ADXL345'}
for ax in AX:
    rng=np.random.default_rng(1)
    Xc,yc=build(tr,ax,'clean',rng)
    Xa,ya=build(tr,ax,'adxl',rng,16,reps=2,gj=True)
    models={'clean_train':rf().fit(Xc,yc),'clean+augmented_train':rf().fit(np.vstack([Xc,Xa]),np.concatenate([yc,ya]))}
    for ev,(mode,lim) in {'eval_clean':('clean',16),'eval_adxl_pm16g':('adxl',16),'eval_adxl_pm4g':('adxl',4)}.items():
        Xt,yt=build(te,ax,mode,np.random.default_rng(7),lim)
        for mn,m in models.items():
            res[f'{ax}|{mn}|{ev}']=rep(yt,m.predict(Xt));print(ax,mn,ev,res[f'{ax}|{mn}|{ev}'],flush=True)
json.dump(res,open('/tmp/mf_adxl3_res.json','w'),indent=1)
