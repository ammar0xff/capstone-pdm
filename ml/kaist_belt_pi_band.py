import sys,json,os,numpy as np
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from kaist_tdms import read_vib
from scipy.signal import butter,sosfiltfilt
from scipy.stats import kurtosis
from sklearn.ensemble import RandomForestClassifier
D="/tmp/hv/Belt Looseness Fault Simulation in an HVAC Testbed/HVAC/Vib/Vib_D%d.tdms"
FS=25600; DEC=64; W=256
def feats(w):
    w=w-w.mean(axis=1,keepdims=True)
    rms=np.sqrt((w**2).mean(1)); pk=np.abs(w).max(1)
    k=((w**4).mean(1))/((w**2).mean(1)**2)
    return np.c_[rms,pk,pk/rms,k]
def windows(x,w):
    n=len(x)//w; return x[:n*w].reshape(n,w)
sos=butter(4,180,btype='low',fs=FS,output='sos')
data={}
for d in range(5):
    ch=read_vib(D%d)
    for c in range(2):
        x=ch[c]
        xl=sosfiltfilt(sos,x)[::DEC]            # 400 Hz stream, 180 Hz low-pass
        data[(d,c,'pi')]=feats(windows(xl,W))    # 256 samples at 400 Hz = 0.64 s
        data[(d,c,'full')]=feats(windows(x,16384))  # full band 25.6 kHz, 0.64 s windows
    print('cond',d,'windows pi',len(data[(d,0,'pi')]),flush=True)
def build(mode,chs):
    X=[];y=[];g=[];t=[]
    for d in range(5):
        for c in chs:
            f=data[(d,c,mode)]; n=len(f)
            X.append(f);y+= [d]*n;g+=[c]*n;t+=list(np.arange(n)*5//n)
    return np.vstack(X),np.array(y),np.array(g),np.array(t)
def rf(): return RandomForestClassifier(n_estimators=100,max_depth=8,random_state=42,class_weight='balanced',n_jobs=-1)
res={}
for mode in('pi','full'):
    X,y,g,t=build(mode,[0,1])
    for task,yy in(('5class',y),('normal_vs_loose',(y>0).astype(int))):
        # time-blocked 5-fold: whole 60 s block (all conditions, both channels) held out; train blocks adjacent to the test block dropped (gap)
        accs=[];maj=[]
        for b in range(5):
            te=t==b; tr=(np.abs(t-b)>1)
            if tr.sum()==0: continue
            m=rf().fit(X[tr],yy[tr]); accs.append(float((m.predict(X[te])==yy[te]).mean()))
            maj.append(float((yy[te]==np.bincount(yy[tr]).argmax()).mean()))
        # leave-one-channel-out: train on one axis, test on the other
        lco=[]
        for c in(0,1):
            m=rf().fit(X[g!=c],yy[g!=c]); lco.append(float((m.predict(X[g==c])==yy[g==c]).mean()))
        res[f'{mode}|{task}']={'time_block_cv_acc':round(float(np.mean(accs)),4),'folds':[round(a,4) for a in accs],'majority_baseline':round(float(np.mean(maj)),4),'train_x_test_y_acc':round(lco[0],4),'train_y_test_x_acc':round(lco[1],4),'n_windows':int(len(yy))}
        print(mode,task,res[f'{mode}|{task}'],flush=True)
# feature means per condition (pi mode) for context
res['pi_feature_means_by_condition']={f'd{d}':[round(float(v),5) for v in np.mean([data[(d,c,'pi')].mean(0) for c in(0,1)],axis=0)] for d in range(5)}
res['feature_order']=['rms_dyn_g','peak_dyn_g','crest','kurtosis']
json.dump(res,open('/tmp/kaist_res.json','w'),indent=1)
print(json.dumps(res['pi_feature_means_by_condition']))
