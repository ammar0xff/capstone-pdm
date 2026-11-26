import zipfile,io,os,sys,time,numpy as np,pandas as pd
from scipy.signal import butter,sosfiltfilt
FS=50000;DEC=125;W=256;FD=400.0
sos=butter(4,180,btype='low',fs=FS,output='sos');win=np.hanning(W);ws=win.sum()
fr=np.fft.rfftfreq(W,1/FD)
def amp_at(S,f):
    k=int(round(f/(FD/W)));k=min(max(k,1),len(S)-2);return S[:,max(k-1,0):k+2].max(1)
def feats(x,ft):
    w=x[:len(x)//W*W].reshape(-1,W);w=w-w.mean(1,keepdims=True)
    rms=np.sqrt((w**2).mean(1));pk=np.abs(w).max(1);cf=pk/rms;ku=((w**4).mean(1))/((w**2).mean(1)**2)
    S=np.abs(np.fft.rfft(w*win,axis=1))*2/ws;P=S**2
    def be(a,b): m=(fr>=a)&(fr<b);return np.log10(P[:,m].sum(1)+1e-12)
    b=[be(10,25),be(25,50),be(50,100),be(100,180)]
    m=(fr>=8)&(fr<=70);idx=np.argmax(S[:,m],axis=1);f0=fr[m][idx];a0=S[:,m].max(1)
    a2=np.array([amp_at(S[i:i+1],2*f0[i])[0] for i in range(len(f0))]);a3=np.array([amp_at(S[i:i+1],3*f0[i])[0] for i in range(len(f0))])
    at1=amp_at(S,ft) if ft>0 else np.zeros(len(w));at2=amp_at(S,2*ft) if ft>0 else np.zeros(len(w))
    return np.column_stack([rms,pk,cf,ku]+b+[f0,a0,a2,a3,np.full(len(w),ft),at1,at2])
def tach(c):
    c=c-c.min();thr=c.max()*0.5
    up=np.sum((c[1:]>thr)&(c[:-1]<=thr));return up/5.0
if __name__=='__main__':
    z,cls=sys.argv[1],sys.argv[2];maxn=int(sys.argv[3]);t0=time.time()
    Z=zipfile.ZipFile(f'/tmp/mf/{z}.zip');n_done=0
    for n in Z.namelist():
        if not n.endswith('.csv'): continue
        out='/tmp/mf/cache3/'+n.replace('/','__')+'.npz'
        if os.path.exists(out): continue
        if n_done>=maxn or time.time()-t0>80: print('partial',z);sys.exit(3)
        a=pd.read_csv(io.BytesIO(Z.read(n)),header=None,usecols=[0,1,2,3],engine='c').values
        ft=tach(a[:,0]);res={}
        for j,name in enumerate(('axial','radial','tangential')):
            res[name]=feats(sosfiltfilt(sos,a[:,j+1]/0.1)[::DEC],ft)
        np.savez(out,cls=cls,grp=os.path.dirname(n),ft=ft,**res);n_done+=1
    print('done',z);sys.exit(0)
