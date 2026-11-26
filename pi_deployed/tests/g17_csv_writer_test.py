"""Offline tests of the g17 CSV writer block. Synthetic rows, temp dirs only."""
import io,re,csv,os,queue,threading,time,tempfile,builtins,json,sys
src=open("edge_daq.py.g17").read()
blk=src[src.index("_csv_q = queue.Queue"):src.index("def _finite_clean")]
def fresh(**kw):
    tmp=tempfile.mkdtemp();HF=os.path.join(tmp,"hot.csv")
    real=builtins.open;st={"d":0.0,"fail":0,"opens":0}
    def op(p,*a,**k):
        if p==HF:
            st["opens"]+=1;time.sleep(st["d"])
            if st["fail"]>0: st["fail"]-=1; raise OSError("EIO sim")
            if st.get("partial",0)>0:
                st["partial"]-=1;h=real(p,*a,**k);ow=h.write
                def bad(x): ow(x[:len(x)//2]);h.flush();raise OSError("EIO mid-write")
                h.write=bad;return h
        return real(p,*a,**k)
    g={"queue":queue,"io":io,"threading":threading,"csv":csv,"time":time,"os":os,"json":json,"HISTORY_FILE":HF,"open":op}
    b=blk.replace("/dev/shm/pdm",tmp).replace("_CSV_DRAIN_DEADLINE_S = 8.0","_CSV_DRAIN_DEADLINE_S = %s"%kw.get("deadline",8.0)).replace("os._exit(0)","pass")
    exec(b,g);return g,st,HF,real,tmp
rd=lambda real,HF:[int(r[0]) for r in csv.reader(real(HF))]
# 1 slow disk: enqueue never blocks, order kept, one open per row
g,st,HF,real,_=fresh();g["_csv_start_thread"]();st["d"]=1.0
t=time.perf_counter()
for i in range(10): g["_csv_enqueue"]([i])
assert time.perf_counter()-t<0.05;st["d"]=0
g["_csv_stop"].set();g["_csv_thread"].join(30)
assert rd(real,HF)==list(range(10)) and st["opens"]==10;print("1 slow disk, order, no batching: PASS")
# 2 transient write errors are retried, same row, order kept, counted
g,st,HF,real,_=fresh();g["_csv_start_thread"]();st["fail"]=2
for i in range(3): g["_csv_enqueue"]([i])
time.sleep(4);g["_csv_stop"].set();g["_csv_thread"].join(30)
assert rd(real,HF)==[0,1,2] and g["_csv_stats"]["write_errors"]==2;print("2 write errors retried + counted:",g["_csv_stats"]["write_errors"],"PASS")
# 3 thread death is detected and restarted
g,st,HF,real,_=fresh();g["_csv_start_thread"]();g["_csv_stop"].set();g["_csv_thread"].join(5);g["_csv_stop"].clear()
g["_csv_enqueue"]([0]);assert g["_csv_stats"]["writer_restarts"]==1
time.sleep(1);g["_csv_stop"].set();g["_csv_thread"].join(10);assert rd(real,HF)==[0];print("3 dead writer restarted: PASS")
# 4 full queue: counted drop, never blocks
g,st,HF,real,_=fresh();g["_csv_q"]=queue.Queue(maxsize=3);g["_csv_start_thread"]();g["_csv_stop"].set();g["_csv_thread"].join(5);g["_csv_stop"].clear()
g["_csv_thread"]=threading.Thread(target=lambda:time.sleep(60),daemon=True);g["_csv_thread"].start()
for i in range(5): g["_csv_enqueue"]([i])
assert g["_csv_stats"]["dropped_queue_full"]==2;print("4 full queue drop counted (2 of 5):PASS")
# 5 bounded shutdown: leftover rows go to a separate spill file, nothing auto-merged
g,st,HF,real,tmp=fresh(deadline=1.5);g["_CSV_SPILL_FILE"]=os.path.join(tmp,"hot.csv.unflushed_T");g["_csv_start_thread"]();st["d"]=1.0
for i in range(8): g["_csv_enqueue"]([i])
time.sleep(0.2);g["_csv_drain_and_exit"]()
sp=[int(r[0]) for r in csv.reader(real(g["_CSV_SPILL_FILE"]))];time.sleep(1.2);on=rd(real,HF)
print("5 shutdown: on disk",on,"spill file",sp);assert sorted(set(on)|set(sp))==list(range(8)) and g["_csv_stats"]["spilled_on_shutdown"]==len(sp)
# 6 partial write: not retried (no duplicate), counted ambiguous, later rows fine
g,st,HF,real,_=fresh();g["_csv_start_thread"]();st["partial"]=1
for i in range(3): g["_csv_enqueue"]([i,"payload"])
time.sleep(1);g["_csv_stop"].set();g["_csv_thread"].join(10)
txt=real(HF).read();print("6 partial-write file:",repr(txt));assert g["_csv_stats"]["ambiguous_rows"]==1 and txt.endswith("\n1,payload\n2,payload\n") and txt.count("2,payload")==1
# 7 single writer: start twice -> one thread
g,st,HF,real,_=fresh();g["_csv_start_thread"]();t1=g["_csv_thread"];g["_csv_start_thread"]();assert g["_csv_thread"] is t1
assert sum(1 for x in threading.enumerate() if x.name=="csv-writer")==1;g["_csv_stop"].set();g["_csv_thread"].join(5);print("7 never two writers: PASS")
# 8 in-flight row spilled first (can be on both disk and spill: seq lets it be de-duplicated manually)
g,st,HF,real,tmp=fresh(deadline=0.5);g["_CSV_SPILL_FILE"]=os.path.join(tmp,"s");g["_csv_start_thread"]();st["d"]=2.0
for i in range(4): g["_csv_enqueue"]([i])
time.sleep(0.3);g["_csv_drain_and_exit"]()
sp=[int(r[0]) for r in csv.reader(real(g["_CSV_SPILL_FILE"]))];print("8 spill:",sp);assert sp==[0,1,2,3]
time.sleep(2.5);print("   disk after in-flight finished:",rd(real,HF),"(row 0 in both: duplicate of <=1 row)")
# 9 startup never reads/writes spill files (no blocking, no merge)
g,st,HF,real,tmp=fresh()
with real(HF+".unflushed_X","w") as f: f.write("1\n")
g["HISTORY_FILE"]=HF
assert "_csv_recover_spill" not in g and "_csv_note_existing_spills" in g;g["_csv_note_existing_spills"]();assert not os.path.exists(HF);print("9 startup only warns about leftover spill; CSV untouched: PASS")
print("G17 TESTS PASS")
