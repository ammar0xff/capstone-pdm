import struct,numpy as np,os
def read_vib(path,nch=2):
    sz=os.path.getsize(path); out=[[] for _ in range(nch)]
    with open(path,'rb') as f:
        pos=0
        while pos+28<=sz:
            f.seek(pos); h=f.read(28)
            if h[:4]!=b'TDSm': break
            toc,ver,nxt,raw=struct.unpack('<IIQQ',h[4:28])
            end=sz if nxt==0xFFFFFFFFFFFFFFFF else pos+28+nxt
            end=min(end,sz)
            n=(end-(pos+28+raw))//(8*nch)
            if n>0 and (toc&8):
                f.seek(pos+28+raw); a=np.frombuffer(f.read(n*8*nch),dtype='<f8')
                if toc&0x20: a=a.reshape(n,nch).T
                else: a=a.reshape(nch,n)
                for c in range(nch): out[c].append(a[c])
            pos=end
    return [np.concatenate(o) for o in out]
if __name__=='__main__':
    import sys
    x=read_vib(sys.argv[1]);print([len(c) for c in x],[ (float(c.mean()),float(c.std()),float(c.min()),float(c.max())) for c in x])
