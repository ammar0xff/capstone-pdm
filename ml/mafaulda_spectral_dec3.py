import zipfile,io,os,sys,time,numpy as np,pandas as pd
from scipy.signal import butter,sosfiltfilt
sos=butter(4,180,btype='low',fs=50000,output='sos')
z=sys.argv[1];t0=time.time();Z=zipfile.ZipFile(f'/tmp/mf/{z}.zip')
for n in Z.namelist():
    if not n.endswith('.csv'): continue
    out='/tmp/mf/dec/'+n.replace('/','__')+'.npy'
    if os.path.exists(out): continue
    if time.time()-t0>80: sys.exit(3)
    a=pd.read_csv(io.BytesIO(Z.read(n)),header=None,usecols=[1,2,3],engine='c').values/0.1
    np.save(out,np.stack([sosfiltfilt(sos,a[:,j])[::125] for j in range(3)]).astype(np.float32))
