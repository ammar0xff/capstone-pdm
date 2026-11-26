import zipfile,io,os,sys,time,numpy as np,pandas as pd
from scipy.signal import butter,sosfiltfilt
FS=50000;DEC=125;W=256
sos=butter(4,180,btype='low',fs=FS,output='sos')
def feats(w):
    w=w-w.mean(axis=1,keepdims=True)
    rms=np.sqrt((w**2).mean(1));pk=np.abs(w).max(1)
    return np.c_[rms,pk,pk/rms,((w**4).mean(1))/((w**2).mean(1)**2)]
t0=time.time()
for z,cls in(('vertical-misalignment','vert'),('underhang','bearing'),('overhang','bearing')):
    Z=zipfile.ZipFile(f'/tmp/mf/{z}.zip')
    for n in Z.namelist():
        if not n.endswith('.csv'): continue
        out='/tmp/mf/cache/'+n.replace('/','__')+'.npz'
        if os.path.exists(out): continue
        if time.time()-t0>95: print('partial');sys.exit(0)
        a=pd.read_csv(io.BytesIO(Z.read(n)),header=None,usecols=[1,2,3],engine='c').values/0.1  # V -> g at 100 mV/g (assumed)
        res={}
        for j,name in enumerate(('axial','radial','tangential')):
            x=a[:,j]; xl=sosfiltfilt(sos,x)[::DEC]
            res[name]=feats(xl[:len(xl)//W*W].reshape(-1,W))
            res[name+'_full_rms']=np.array([(x-x.mean()).std()])
            res[name+'_pi_rms']=np.array([(xl-xl.mean()).std()])
        np.savez(out,cls=cls,grp=os.path.dirname(n),**res)
print('done',len(os.listdir('/tmp/mf/cache')))
