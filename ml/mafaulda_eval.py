import glob,json,numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold
fs=sorted(glob.glob('/tmp/mf/cache/*.npz'))
recs=[]
for i,f in enumerate(fs):
    d=np.load(f,allow_pickle=True);recs.append(d)
cls=np.array([str(d['cls']) for d in recs]);grp=np.array([str(d['grp']) for d in recs])
nidx=np.where(cls=='normal')[0]
for k,i in enumerate(nidx): grp[i]='normal_%d'%(k%5)
names={'normal':0,'imbalance':1,'horiz':2}
res={}
def rf(): return RandomForestClassifier(n_estimators=100,max_depth=8,random_state=42,class_weight='balanced',n_jobs=-1)
for ch in('radial','axial','tangential'):
    X=[];y=[];fid=[];g=[]
    for i,d in enumerate(recs):
        f=d[ch];X.append(f);y+=[names[cls[i]]]*len(f);fid+=[i]*len(f);g+=[grp[i]]*len(f)
    X=np.vstack(X);y=np.array(y);fid=np.array(fid);g=np.array(g)
    for task,yy in(('3class',y),('normal_vs_fault',(y>0).astype(int))):
        out={}
        for split,key in(('by_file',fid),('by_severity_group',g)):
            accs=[];maj=[]
            for tr,te in GroupKFold(5).split(X,yy,key):
                m=rf().fit(X[tr],yy[tr]);accs.append(float((m.predict(X[te])==yy[te]).mean()));maj.append(float((yy[te]==np.bincount(yy[tr]).argmax()).mean()))
            out[split]={'acc':round(float(np.mean(accs)),4),'folds':[round(a,3) for a in accs],'majority_baseline':round(float(np.mean(maj)),4)}
        out['n_windows']=int(len(yy));out['class_counts']=np.bincount(yy).tolist()
        res[f'{ch}|{task}']=out;print(ch,task,json.dumps(out),flush=True)
lv={}
for ch in('radial','axial','tangential'):
    for c in names:
        idx=[i for i in range(len(recs)) if cls[i]==c]
        lv[f'{ch}|{c}']={'full_band_rms_g_median':round(float(np.median([recs[i][ch+'_full_rms'][0] for i in idx])),5),'pi_band_rms_g_median':round(float(np.median([recs[i][ch+'_pi_rms'][0] for i in idx])),5),'pi_band_rms_g_min':round(float(np.min([recs[i][ch+'_pi_rms'][0] for i in idx])),5),'n_files':len(idx)}
res['signal_level_g']=lv
for k,v in lv.items(): print(k,v)
json.dump(res,open('/tmp/mafaulda_res.json','w'),indent=1)
