import glob,json,hashlib,os,numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import balanced_accuracy_score,f1_score
CL=['normal','imbalance','horiz','vert','bearing'];ci={c:i for i,c in enumerate(CL)}
fs=sorted(glob.glob('/tmp/mf/cache3/*.npz'));R=[dict(np.load(f,allow_pickle=True)) for f in fs]
cls=np.array([str(d['cls']) for d in R]);grp=np.array([str(d['grp']) for d in R])
for k,i in enumerate(np.where(cls=='normal')[0]): grp[i]='normal_%d'%(k%5)
held=set()
for c in CL:
    gs=sorted({grp[i] for i in range(len(R)) if cls[i]==c},key=lambda g:hashlib.md5(g.encode()).hexdigest())
    held|=set(gs[:max(1,round(len(gs)*0.25))])
tr=[i for i in range(len(R)) if grp[i] not in held];te=[i for i in range(len(R)) if grp[i] in held]
SETS={'time4':[0,1,2,3],'time+bands8':list(range(8)),'+peaks12':list(range(12)),'+tach15_oracle':list(range(15))}
def mk(idx,axes,cols,keep):
    X=[];y=[];g=[]
    for i in idx:
        if cls[i] not in keep: continue
        f=np.hstack([R[i][a][:,cols] for a in axes]);X.append(f);y+=[keep.index(cls[i])]*len(f);g+=[grp[i]]*len(f)
    return np.vstack(X),np.array(y),np.array(g)
rf=lambda:RandomForestClassifier(n_estimators=150,max_depth=10,random_state=42,class_weight='balanced_subsample',n_jobs=-1)
res={'files':len(R),'heldout_groups':len(held),'test_files':len(te)}
for kn,keep in(('5class',CL),('3class',['normal','imbalance','horiz'])):
  for ax_n,axes in(('three',['axial','radial','tangential']),('radial',['radial'])):
    for sn,cols in SETS.items():
        X,y,g=mk(tr,axes,cols,keep);Xt,yt,_=mk(te,axes,cols,keep)
        if kn=='3class':
            pass
        m=rf().fit(X,y);p=m.predict(Xt)
        r={'balanced_acc':round(float(balanced_accuracy_score(yt,p)),4),'macro_f1':round(float(f1_score(yt,p,average='macro')),4),'acc':round(float((yt==p).mean()),4)}
        res[f'{kn}|{ax_n}|{sn}']=r;print(kn,ax_n,sn,r,flush=True)
json.dump(res,open('/tmp/mf_train3_res.json','w'),indent=1)
