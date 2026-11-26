"""H1 prototype (NOT deployed): copies a fast tmpfs append-log to the durable CSV with positional writes.
pwrite at a deterministic offset => a retried copy rewrites the same bytes at the same place: no duplicates, no skipped rows.
Only whole lines (up to the last newline) are copied. The durable file is never truncated or rewritten, only extended."""
import os, json, time

class Sync:
    def __init__(self, live, durable, state, log=print):
        self.live, self.durable, self.state, self.log = live, durable, state, log
        self.stats = {"synced_bytes": 0, "errors": 0, "mismatch_halts": 0, "last_error": None}
        self.base = None   # durable size when live offset 0 was mapped
        self.done = 0      # live bytes already placed in durable
    def _load(self):
        if os.path.exists(self.state):
            d = json.load(open(self.state)); self.base, self.done = d["base"], d["done"]
        else:
            self.base = os.path.getsize(self.durable) if os.path.exists(self.durable) else 0; self.done = 0
            self._save()
    def _save(self):
        tmp = self.state + ".tmp"; json.dump({"base": self.base, "done": self.done}, open(tmp, "w")); os.replace(tmp, self.state)
    def step(self):
        if self.base is None: self._load()
        if not os.path.exists(self.live): return 0
        with open(self.live, "rb") as f:
            f.seek(self.done); data = f.read()
        cut = data.rfind(b"\n") + 1
        if cut <= 0: return 0
        data = data[:cut]
        dsize = os.path.getsize(self.durable) if os.path.exists(self.durable) else 0
        want = self.base + self.done
        if dsize < want:  # durable shorter than we believe (truncated/replaced externally): refuse to guess
            self.stats["mismatch_halts"] += 1; self.log("[ERROR] durable file shorter than expected, halting sync"); return -1
        try:
            fd = os.open(self.durable, os.O_WRONLY | os.O_CREAT)
            try:
                os.pwrite(fd, data, want)   # same offset on retry: idempotent
            finally:
                os.close(fd)
        except Exception as e:
            self.stats["errors"] += 1; self.stats["last_error"] = repr(e)[:200]; return 0
        self.done += len(data); self._save(); self.stats["synced_bytes"] += len(data); return len(data)
