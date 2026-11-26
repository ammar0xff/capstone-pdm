import json,time,os,urllib.request,threading,subprocess,sys
dur=int(sys.argv[1]);out=open("/tmp/paired.log","w")
t0=time.time()
def log(*a): out.write(f"{time.time():.2f} "+" ".join(str(x) for x in a)+"\n");out.flush()
def src():
    last=None
    while time.time()-t0<dur:
        try:
            d=json.load(open("/dev/shm/pdm/latest_state.json"))
            if d["seq"]!=last: last=d["seq"];log("SRC",d["seq"],d["timestamp"])
        except Exception: pass
        time.sleep(0.05)
def net():
    while time.time()-t0<dur:
        a=time.time()
        try:
            r=urllib.request.urlopen("https://castpone2026-default-rtdb.firebaseio.com/motor1/seq.json",timeout=10).read().decode()
            log("GET",round(time.time()-a,3),r.strip())
        except Exception as e: log("GETERR",round(time.time()-a,2),str(e)[:40])
        time.sleep(1.0)
def jr():
    p=subprocess.Popen(["journalctl","-u","pdm-cloud","-f","-o","short-unix","-n","0","--no-pager"],stdout=subprocess.PIPE,text=True)
    while time.time()-t0<dur:
        l=p.stdout.readline()
        if "Synced" in l: log("MIR",l.split("seq=")[1].split()[0])
    p.kill()
for f in (src,net,jr): threading.Thread(target=f,daemon=True).start()
time.sleep(dur+2)
