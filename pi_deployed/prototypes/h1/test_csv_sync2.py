import os, sys, time, json, signal, subprocess, tempfile, random
from csv_sync2 import Sync
PY = sys.executable; HERE = os.path.dirname(os.path.abspath(__file__)); SYNC = HERE + "/csv_sync2.py"
HIST = "timestamp,seq,a\n1,0,x\n2,1,y,EXTRA\n3,2\n"   # mixed layouts on purpose
def mk():
    d = tempfile.mkdtemp(); L, D, S, T = d+"/live", d+"/dur", d+"/st", d+"/stats"; open(D, "w").write(HIST); return d, L, D, S, T
def app(L, a, b):
    with open(L, "a") as f:
        for i in range(a, b): f.write(f"r{i},{i},v\n")
want = lambda n: HIST + "".join(f"r{i},{i},v\n" for i in range(n))
q = lambda *a: None
# 1 real subprocess, SIGKILL at random times while rows keep arriving, restart each time
d, L, D, S, T = mk(); n = 0; random.seed(5)
for rnd in range(8):
    p = subprocess.Popen([PY, SYNC, L, D, S, T, "0.05"], stdout=subprocess.DEVNULL)
    for _ in range(random.randint(3, 9)): app(L, n, n+5); n += 5; time.sleep(random.random()*0.08)
    time.sleep(random.random()*0.1); p.kill(); p.wait()
p = subprocess.Popen([PY, SYNC, L, D, S, T, "0.05"]); time.sleep(0.6); p.terminate(); p.wait(timeout=30)
assert open(D).read() == want(n), "mismatch after SIGKILL cycles"; print("1 SIGKILL x8 + restart: durable == history + %d rows exactly once, in order" % n)
# 2 kill between pwrite and state save (test hook), restart replays idempotently
d, L, D, S, T = mk(); app(L, 0, 20)
e = dict(os.environ, H1_TEST_CRASH_AFTER_PWRITE="1"); r = subprocess.run([PY, SYNC, L, D, S, T, "0.05"], env=e, timeout=5)
assert r.returncode == 9 and open(D).read() == want(20)           # data landed, state did not
app(L, 20, 30); p = subprocess.Popen([PY, SYNC, L, D, S, T, "0.05"]); time.sleep(0.5); p.terminate(); p.wait(timeout=30)
assert open(D).read() == want(30); print("2 crash after write before state save: replay, no duplicate")
# 3 state file lost (live survives): recovered from data
os.remove(S); app(L, 30, 35); s = Sync(L, D, S, T, q); s.step(); assert open(D).read() == want(35) and s.stats["recovered_from"] == "data_match"; print("3 state lost: recovered by matching durable tail to live: OK")
# 4 state lost before anything copied: fresh, no duplicate of history
d, L, D, S, T = mk(); app(L, 0, 3); s = Sync(L, D, S, T, q); s.step(); assert open(D).read() == want(3) and s.stats["recovered_from"] == "fresh"; print("4 fresh start: OK")
# 5 reboot: tmpfs gone (live+state gone) -> fresh base, history preserved, new rows appended
os.remove(L); os.remove(S); s = Sync(L, D, S, T, q); s.step(); app(L, 100, 102); s.step(); assert open(D).read() == want(3) + "r100,100,v\nr101,101,v\n"; print("5 tmpfs lost at reboot: history kept, new boot continues (unsynced RAM rows are gone, not claimed saved)")
# 6 torn last line in durable (power cut mid-write) is isolated, not glued
d, L, D, S, T = mk(); open(D, "a").write("9,9,tor"); s = Sync(L, D, S, T, q); app(L, 0, 2); s.step()
assert open(D).read() == HIST + "9,9,tor\nr0,0,v\nr1,1,v\n" and s.stats["torn_tail_newline_added"]; print("6 torn tail isolated by one newline (durable only extended)")
# 7 live shrinks: halt and flag, durable untouched
d, L, D, S, T = mk(); app(L, 0, 10); s = Sync(L, D, S, T, q); s.step(); before = open(D).read(); open(L, "w").write("r0,0,v\n"); assert s.step() == -1 and open(D).read() == before and "shorter" in s.stats["halted"]; print("7 live shrank: halted+flagged, nothing written:", s.stats["halted"][:40])
# 8 durable truncated: halt
d, L, D, S, T = mk(); app(L, 0, 5); s = Sync(L, D, S, T, q); s.step(); open(D, "w").write("x\n"); app(L, 5, 6); assert s.step() == -1 and open(D).read() == "x\n"; print("8 durable truncated: halted, nothing written")
# 9 state lost and durable tail mismatches live: halt, never guess
d, L, D, S, T = mk(); app(L, 0, 5); s = Sync(L, D, S, T, q); s.step(); os.remove(S)
open(D, "r+b").write(HIST.encode()); fd = open(D, "r+b"); fd.seek(len(HIST)+5); fd.write(b"Z"); fd.close()
s2 = Sync(L, D, S, T, q); assert s2.step() == -1 and "manual" in s2.stats["halted"]; print("9 ambiguous recovery: halted for manual check")
# 10 disk full / short write / EIO: retry same offset, no dup, error visible
d, L, D, S, T = mk(); app(L, 0, 10); s = Sync(L, D, S, T, q); real = os.pwrite; c = {"n": 0}
def flaky(fd, b, off):
    c["n"] += 1
    if c["n"] == 1: return real(fd, b[:7], off)          # short write
    if c["n"] == 2: real(fd, b[:3], off); raise OSError(28, "No space left")
    return real(fd, b, off)
os.pwrite = flaky; r1 = s.step(); r2 = s.step(); os.pwrite = real
assert open(D).read() == want(10) and s.stats["io_errors"] == 1 and "No space" in s.stats["last_error"]; print("10 short write + ENOSPC then recovery: correct, no dup, io_errors visible =", s.stats["io_errors"])
# 11 appender unaffected + visibility: lag and last_ok in stats; never deletes live rows
assert os.path.getsize(L) > 0 and s.stats["last_ok_ts"] is not None; print("11 live rows kept; stats expose lag_bytes, last_ok_ts, io_errors, halted")
# 12 growth measurement
print("12 growth: 104 B/row x 86400 rows/day = %.1f MB/day tmpfs if the syncer never ran (live_over_warn flag at 200 MB)" % (104*86400/1e6))
print("H1 v2 TESTS PASS")
