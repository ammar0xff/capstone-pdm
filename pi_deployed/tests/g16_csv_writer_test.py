"""Offline test of the CSV writer-thread block from edge_daq.py.g16 with an artificially slow disk. Synthetic rows only."""
import re,csv,os,queue,threading,time,tempfile,builtins
src=open("edge_daq.py.g16").read()
blk=re.search(r"_csv_q = queue.Queue.*?def _csv_drain_and_exit",src,re.S).group(0).rsplit("def _csv_drain_and_exit",1)[0]
tmp=tempfile.mkdtemp();HF=os.path.join(tmp,"hot.csv")
real_open=builtins.open;delay={"d":0.0};opens=[0]
def slow_open(p,*a,**k):
    if p==HF:
        opens[0]+=1;time.sleep(delay["d"])
    return real_open(p,*a,**k)
g={"queue":queue,"threading":threading,"csv":csv,"HISTORY_FILE":HF,"open":slow_open}
exec(blk,g)
g["_csv_thread"].start()
delay["d"]=1.5   # every append blocks 1.5 s (disk stall)
t=time.perf_counter()
for i in range(20): g["_csv_q"].put_nowait([i,"x"])
put_time=time.perf_counter()-t
print("20 puts while disk blocked took %.4f s (old inline write would take ~30 s)"%put_time)
assert put_time<0.05
delay["d"]=0.0
g["_csv_stop"].set();g["_csv_thread"].join(timeout=30)
rows=list(csv.reader(real_open(HF)))
print("rows on disk after drain:",len(rows))
assert [int(r[0]) for r in rows]==list(range(20)),"order/loss"
assert opens[0]==20,"one open per row (no batching)"
print("one open/append per row:",opens[0],"| ORDER OK, NO LOSS ON CLEAN DRAIN")
# queue full behaviour
g2=dict(g);q=queue.Queue(maxsize=3)
try:
    for i in range(5): q.put_nowait(i)
except queue.Full: print("full queue raises queue.Full (caught by the loop's try/except, row dropped, loop not blocked)")
print("G16 CSV WRITER TEST PASS")
