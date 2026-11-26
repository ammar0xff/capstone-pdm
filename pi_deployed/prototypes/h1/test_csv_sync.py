import os, tempfile, time, threading, csv, builtins
from csv_sync import Sync
d = tempfile.mkdtemp(); L = d + "/live.csv"; D = d + "/dur.csv"; S = d + "/st.json"
open(D, "w").write("hdr\n0\n1\n")                     # pre-existing history
def app(rows):
    with open(L, "a") as f:
        for r in rows: f.write(f"{r}\n")
s = Sync(L, D, S, log=lambda *a: None)
app(range(2, 7)); assert s.step() > 0
assert open(D).read() == "hdr\n" + "".join(f"{i}\n" for i in range(7)); print("1 normal sync, history preserved, order OK")
# 2 partial line is not copied
open(L, "a").write("7,par"); s.step(); assert open(D).read().endswith("6\n"); open(L, "a").write("tial\n"); s.step(); assert open(D).read().endswith("6\n7,partial\n"); print("2 only whole lines copied: OK")
# 3 failed pwrite then retry => no duplicate
real = os.pwrite; calls = {"n": 0}
def bad(fd, data, off):
    calls["n"] += 1
    if calls["n"] == 1:
        real(fd, data[:len(data)//2], off); raise OSError("EIO half")
    return real(fd, data, off)
os.pwrite = bad; app([8, 9]); assert s.step() == 0 and s.stats["errors"] == 1; s.step(); os.pwrite = real
txt = open(D).read(); assert txt.endswith("7,partial\n8\n9\n") and txt.count("8\n") == 1; print("3 partial pwrite then retry: no duplicate, no gap: OK")
# 4 syncer restart recovers from state file
s2 = Sync(L, D, S, log=lambda *a: None); app([10]); s2.step(); assert open(D).read().endswith("9\n10\n"); print("4 restart resumes from state: OK")
# 5 durable truncated externally => halt, no write
open(D, "w").write("x\n"); app([11]); assert s2.step() == -1 and open(D).read() == "x\n"; print("5 truncated durable file: halted, nothing written: OK")
# 6 appender never blocks when durable write is slow
d2 = tempfile.mkdtemp(); L2 = d2 + "/l"; D2 = d2 + "/d"; open(D2, "w").write("h\n"); s3 = Sync(L2, D2, d2 + "/s", log=lambda *a: None)
def slow(fd, data, off): time.sleep(1.5); return real(fd, data, off)
os.pwrite = slow; app2 = lambda i: open(L2, "a").write(f"{i}\n")
app2(0); th = threading.Thread(target=s3.step); th.start(); time.sleep(0.2)
t = time.perf_counter()
for i in range(1, 50): app2(i)
dt = time.perf_counter() - t; th.join(); os.pwrite = real; s3.step()
print("6 50 appends while durable write blocked 1.5 s took %.4f s" % dt); assert dt < 0.2
assert [int(x) for x in open(D2).read().split()[1:]] == list(range(50)); print("   final durable complete and ordered: OK")
print("H1 SYNC TESTS PASS")
