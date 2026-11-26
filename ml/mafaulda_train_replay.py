import glob,io,json,zipfile,hashlib,os,sys,numpy as np,pandas as pd,joblib
from scipy.signal import butter,sosfiltfilt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import balanced_accuracy_score,f1_score,confusion_matrix
CL=['normal','imbalance','horiz','vert','bearing'];ci={c:i for i,c in enumerate(CL)}
fs=sorted(glob.glob('/tmp/mf/cache/*.npz'));R=[dict(np.load(f,allow_pickle=True)) for f in fs]
names=[os.path.basename(f)[:-4].replace('__','/') for f in fs]   # original member path
cls=np.array([str(d['cls']) for d in R]);grp=np.array([str(d['grp']) for d in R])
nidx=np.where(cls=='normal')[0]
for k,i in enumerate(nidx): grp[i]='normal_%d'%(k%5)
ug=sorted(set(grp)); held=set()
for c in CL:
    gs=sorted({grp[i] for i in range(len(R)) if cls[i]==c},key=lambda g:hashlib.md5(g.encode()).hexdigest())
    held|=set(gs[:max(1,round(len(gs)*0.25))])
tr_f=[i for i in range(len(R)) if grp[i] not in held]; te_f=[i for i in range(len(R)) if grp[i] in held]
print('groups',len(ug),'held-out groups',len(held),'train files',len(tr_f),'test files',len(te_f),flush=True)
def mk(idx,axes):
    X=[];y=[];g=[];fid=[]
    for i in idx:
        f=np.hstack([R[i][a] for a in axes]);X.append(f);y+=[ci[cls[i]]]*len(f);g+=[grp[i]]*len(f);fid+=[i]*len(f)
    return np.vstack(X),np.array(y),np.array(g),np.array(fid)
def rf(): return RandomForestClassifier(n_estimators=150,max_depth=10,random_state=42,class_weight='balanced_subsample',n_jobs=-1)
def rep(y,p): return {'acc':round(float((y==p).mean()),4),'balanced_acc':round(float(balanced_accuracy_score(y,p)),4),'macro_f1':round(float(f1_score(y,p,average='macro')),4)}
res={'classes':CL,'held_out_groups':sorted(held),'n_files_train':len(tr_f),'n_files_test':len(te_f)}
models={}
for tag,axes in(('radial',['radial']),('three_axis',['axial','radial','tangential'])):
    X,y,g,fid=mk(tr_f,axes);Xt,yt,gt,ft=mk(te_f,axes)
    cv=[];
    for tr,te in GroupKFold(5).split(X,y,g):
        m=rf().fit(X[tr],y[tr]);cv.append(rep(y[te],m.predict(X[te])))
    m=rf().fit(X,y);p=m.predict(Xt)
    res[tag]={'train_windows':int(len(y)),'test_windows':int(len(yt)),'train_class_counts':np.bincount(y,minlength=5).tolist(),'test_class_counts':np.bincount(yt,minlength=5).tolist(),
      'group_cv_on_train':{k:round(float(np.mean([c[k] for c in cv])),4) for k in cv[0]},'group_cv_folds_balanced_acc':[c['balanced_acc'] for c in cv],
      'heldout_groups_test':rep(yt,p),'majority_baseline_acc':round(float((yt==np.bincount(y).argmax()).mean()),4),'chance_balanced_acc':0.2,
      'confusion_rows_true_cols_pred':confusion_matrix(yt,p,labels=range(5)).tolist()}
    models[tag]=(m,axes);print(tag,json.dumps(res[tag]),flush=True)
# replay with a simulated ADXL345 front end (noise 3 mg rms, 4 mg/LSB, range clip), raw CSV -> filter -> decimate -> windows -> features -> model
sos=butter(4,180,btype='low',fs=50000,output='sos')
def feats(w):
    w=w-w.mean(axis=1,keepdims=True);rms=np.sqrt((w**2).mean(1));pk=np.abs(w).max(1)
    return np.c_[rms,pk,pk/rms,((w**4).mean(1))/((w**2).mean(1)**2)]
import pickle
DEC_PATH='/tmp/mf_dec.pkl'
zs={z:zipfile.ZipFile(f'/tmp/mf/{z}.zip') for z in('normal','imbalance','horizontal-misalignment','vertical-misalignment','underhang','overhang')}
rng=np.random.default_rng(0)
out={}
if os.path.exists(DEC_PATH): DEC=pickle.load(open(DEC_PATH,'rb'))
else:
    DEC={}
    for i in te_f:
        n=names[i];z=n.split('/')[0];a=pd.read_csv(io.BytesIO(zs[z].read(n)),header=None,usecols=[1,2,3]).values/0.1
        DEC[i]=[sosfiltfilt(sos,a[:,j])[::125] for j in range(3)]
    pickle.dump(DEC,open(DEC_PATH,'wb'))
print('decimated cache ready',len(DEC),flush=True)
for rngname,lim in(('ideal',None),('pm16g',16.0),('pm4g',4.0)):
    for tag,(m,axes) in models.items():
        P=[];T=[];clipfrac=[]
        for i in te_f:
            F=[]
            for j,ax in enumerate(('axial','radial','tangential')):
                if ax not in axes: continue
                x=DEC[i][j].copy()
                if lim is not None:
                    x=x-0+rng.normal(0,0.003,len(x)); c=np.abs(x+0)>lim; clipfrac.append(c.mean()); x=np.clip(x,-lim,lim); x=np.round(x/0.004)*0.004
                F.append(feats(x[:len(x)//256*256].reshape(-1,256)))
            F=np.hstack(F);pr=m.predict(F);P.append(np.bincount(pr,minlength=5).argmax());T.append(ci[cls[i]])
            out.setdefault((rngname,tag,'win'),[]).append((np.full(len(pr),ci[cls[i]]),pr))
        P=np.array(P);T=np.array(T)
        wy=np.concatenate([a for a,b in out[(rngname,tag,'win')]]);wp=np.concatenate([b for a,b in out[(rngname,tag,'win')]])
        res.setdefault('replay',{})[f'{tag}|{rngname}']={'recording_vote':rep(T,P),'window':rep(wy,wp),'n_recordings':int(len(T)),'frac_windows_beyond_range':round(float(np.mean(clipfrac)),4) if clipfrac else 0.0}
        print(rngname,tag,json.dumps(res['replay'][f'{tag}|{rngname}']),flush=True)
json.dump(res,open('/tmp/mf_train_res.json','w'),indent=1)
for tag,(m,axes) in models.items(): joblib.dump({'model':m,'axes':axes,'classes':CL},f'/tmp/mf_model_{tag}.joblib',compress=3)
