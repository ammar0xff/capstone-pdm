#!/usr/bin/env python3
"""H1 v2 prototype (NOT deployed). Copies a tmpfs append-log (LIVE) into the durable CSV (DURABLE) by positional writes.
Durable file is only ever extended. Live rows are never deleted by this program. Anything unclear halts and is flagged, never guessed."""
import os, sys, json, time, signal

TAIL_WINDOW = 8 * 1024 * 1024
LIVE_WARN_BYTES = 200 * 1024 * 1024

class Sync:
    def __init__(self, live, durable, state, stats_path=None, log=None):
        self.live, self.durable, self.state, self.stats_path = live, durable, state, stats_path
        self.log = log or (lambda m: print(m, flush=True))
        self.base = None; self.done = 0; self.halted = None
        self.stats = {"synced_bytes": 0, "io_errors": 0, "last_error": None, "halted": None, "last_ok_ts": None,
                      "lag_bytes": 0, "live_bytes": 0, "recovered_from": None, "torn_tail_newline_added": False}
        self.crash_after_pwrite = os.environ.get("H1_TEST_CRASH_AFTER_PWRITE") == "1"
    def _halt(self, why):
        self.halted = why; self.stats["halted"] = why; self.log("[ERROR] sync halted: " + why); self.dump()
    def dump(self):
        if not self.stats_path: return
        try:
            self.stats["ts"] = time.time(); t = self.stats_path + ".tmp"; json.dump(self.stats, open(t, "w")); os.replace(t, self.stats_path)
        except Exception: pass
    def _dsize(self): return os.path.getsize(self.durable) if os.path.exists(self.durable) else 0
    def _save(self):
        t = self.state + ".tmp"; json.dump({"base": self.base, "done": self.done}, open(t, "w")); os.replace(t, self.state)
    def _start(self):
        """Establish (base, done). State file first; else recover from the data; else fresh."""
        D = self._dsize()
        if os.path.exists(self.state):
            try:
                d = json.load(open(self.state)); self.base, self.done = int(d["base"]), int(d["done"])
                self.stats["recovered_from"] = "state"; return True
            except Exception:
                self.log("[WARN] state file unreadable, recovering from data")
        livesize = os.path.getsize(self.live) if os.path.exists(self.live) else 0
        if livesize == 0:
            self._fresh(D); return True
        with open(self.live, "rb") as f: first = f.readline()
        if not first.endswith(b"\n"):  # nothing complete yet: nothing could have been copied
            self._fresh(D); return True
        with open(self.durable, "rb") as f:
            f.seek(max(0, D - TAIL_WINDOW)); tail = f.read(); off0 = max(0, D - TAIL_WINDOW)
        pos = tail.rfind(first)
        if pos < 0:
            needle = first[:5]
            np_ = tail.rfind(needle)
            if len(first) > 6 and np_ >= 0 and (len(tail) - np_) <= os.path.getsize(self.live) + len(first):
                self._halt("state lost and first live row only partly matches durable tail: manual check needed"); return False
            self._fresh(D); return True      # first live row is not in durable: none of live was copied
        start = off0 + pos
        with open(self.live, "rb") as f: lp = f.read(D - start)
        with open(self.durable, "rb") as f:
            f.seek(start); dp = f.read()
        if lp != dp:   # durable tail must be exactly a prefix of live
            self._halt("state lost and durable tail does not match live: manual check needed"); return False
        self.base, self.done = start, len(dp); self.stats["recovered_from"] = "data_match"; self._save(); return True
    def _fresh(self, D):
        if D > 0:
            with open(self.durable, "rb") as f:
                f.seek(D - 1)
                if f.read(1) != b"\n":      # torn last line from an earlier power loss: isolate it, extend only
                    fd = os.open(self.durable, os.O_WRONLY | os.O_APPEND)
                    try: os.write(fd, b"\n"); os.fsync(fd)
                    finally: os.close(fd)
                    D += 1; self.stats["torn_tail_newline_added"] = True
        self.base, self.done = D, 0; self.stats["recovered_from"] = self.stats["recovered_from"] or "fresh"; self._save()
    def step(self):
        if self.halted: return -1
        if self.base is None and not self._start(): return -1
        if not os.path.exists(self.live): return 0
        ls = os.path.getsize(self.live); self.stats["live_bytes"] = ls
        if ls < self.done:
            self._halt("live file shorter than already-copied bytes (replaced or truncated): rows not verified, not touching durable"); return -1
        if ls > LIVE_WARN_BYTES: self.stats["live_over_warn"] = True
        with open(self.live, "rb") as f:
            f.seek(self.done); data = f.read()
        cut = data.rfind(b"\n") + 1
        self.stats["lag_bytes"] = len(data)
        if cut <= 0: self.dump(); return 0
        data = data[:cut]; want = self.base + self.done
        if self._dsize() < want:
            self._halt("durable file shorter than expected (truncated or replaced)"); return -1
        try:
            fd = os.open(self.durable, os.O_WRONLY | os.O_CREAT)
            try:
                n = 0
                while n < len(data):
                    n += os.pwrite(fd, data[n:], want + n)   # short writes continue at the right offset
                if self.crash_after_pwrite: os._exit(9)     # test hook: die before saving state
                os.fsync(fd)
            finally: os.close(fd)
        except Exception as e:
            self.stats["io_errors"] += 1; self.stats["last_error"] = repr(e)[:200]; self.dump(); return 0
        self.done += len(data); self._save()
        self.stats["synced_bytes"] += len(data); self.stats["lag_bytes"] = 0; self.stats["last_ok_ts"] = time.time(); self.dump(); return len(data)

def main():
    live, durable, state, stats = sys.argv[1:5]; interval = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
    s = Sync(live, durable, state, stats); stop = {"v": False}
    signal.signal(signal.SIGTERM, lambda *a: stop.__setitem__("v", True))
    while not stop["v"]:
        s.step(); time.sleep(interval)
    t0 = time.time()                         # bounded final drain after daq stopped
    while time.time() - t0 < 20 and s.step() > 0: pass
    s.dump()
if __name__ == "__main__": main()
