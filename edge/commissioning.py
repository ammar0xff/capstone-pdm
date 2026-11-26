"""Commissioning baseline for the Stage-1 SPC gate (Phase I).

What it does: during a short run that the operator says is healthy, the device collects
rms_dyn windows itself, computes mu and sigma, and the SPC gate then uses them instead of
the hard-coded defaults (mu 0.080 g, sigma 0.025 g).

What it does NOT do: it cannot tell that the motor is running or healthy. It records what
the accelerometer saw while the operator said "healthy". The result is always labelled
motor_running_verified = false. The default baseline stays as the fallback until a
commissioned baseline has been accepted. Nothing here touches the 0.04 g kurtosis gate
or any other threshold.

Pure Python (standard library only) so it can be unit-tested off the Pi.
"""
import json
import math
import os
import time

DEFAULT_MU = 0.080
DEFAULT_SIGMA = 0.025
SOURCE_DEFAULT = "default"
SOURCE_COMMISSIONED = "commissioned"

TARGET_S = 600.0            # about 10 minutes
MIN_SAMPLE_GAP_S = 0.7      # one 256-sample window at 400 Hz is 0.64 s: keep windows non-overlapping
MIN_SAMPLES = 200
MIN_VALID_FRACTION = 0.90   # share of windows with valid inputs
MAX_TRIM_FRACTION = 0.10    # points beyond median +/- 4 robust sd allowed before the run is called unstable
MAX_DRIFT_RATIO = 0.5       # |mean(first half) - mean(second half)| / sd
SIGMA_REL_FLOOR = 0.05      # sigma is never below 5% of mu (avoids a zero-width gate)
SIGMA_ABS_FLOOR = 0.0005    # g
NOISE_FLOOR_G = 0.003       # mean rms below this is the sensor noise floor, not a usable signal
MAX_MU_G = DEFAULT_MU + 3 * DEFAULT_SIGMA   # 0.155 g: a baseline above the default fault limit is refused


def default_baseline():
    return {"source": SOURCE_DEFAULT, "mu": DEFAULT_MU, "sigma": DEFAULT_SIGMA}


def compute_baseline(samples):
    """samples: list of rms_dyn values (g), one per non-overlapping window.
    Returns (ok, result_or_None, message)."""
    xs = [float(x) for x in samples if x is not None and math.isfinite(float(x))]
    n = len(xs)
    if n < MIN_SAMPLES:
        return False, None, "too few windows (%d, need %d)" % (n, MIN_SAMPLES)
    mean = sum(xs) / n
    sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / (n - 1))
    if mean < NOISE_FLOOR_G:
        return False, None, "mean rms %.4f g is at the sensor noise floor; no usable vibration signal" % mean
    # robust outlier test (median/MAD): a plain 3-sd test is masked by the outliers it should catch
    srt = sorted(xs)
    med = srt[n // 2] if n % 2 else 0.5 * (srt[n // 2 - 1] + srt[n // 2])
    dev = sorted(abs(x - med) for x in xs)
    mad = dev[n // 2] if n % 2 else 0.5 * (dev[n // 2 - 1] + dev[n // 2])
    spread = max(1.4826 * mad, SIGMA_ABS_FLOOR)
    lo, hi = med - 4 * spread, med + 4 * spread
    kept = [x for x in xs if lo <= x <= hi]
    trimmed = n - len(kept)
    if trimmed / n > MAX_TRIM_FRACTION:
        return False, None, "run not stable: %d of %d windows were outliers" % (trimmed, n)
    m2 = sum(kept) / len(kept)
    s2 = math.sqrt(sum((x - m2) ** 2 for x in kept) / (len(kept) - 1)) if len(kept) > 1 else 0.0
    half = len(xs) // 2
    first, second = xs[:half], xs[half:]
    drift = abs(sum(first) / len(first) - sum(second) / len(second))
    if s2 > 0 and drift / s2 > MAX_DRIFT_RATIO and drift > 0.1 * m2:
        return False, None, "run not stable: level drifted by %.4f g between first and second half" % drift
    sigma = max(s2, SIGMA_REL_FLOOR * m2, SIGMA_ABS_FLOOR)
    if m2 > MAX_MU_G:
        return False, None, "mean rms %.4f g is above the default fault limit %.3f g; not accepted" % (m2, MAX_MU_G)
    return True, {
        "source": SOURCE_COMMISSIONED, "mu": round(m2, 5), "sigma": round(sigma, 5),
        "n_windows": n, "n_trimmed": trimmed, "raw_sd": round(sd, 5),
    }, "accepted"


def limits(baseline):
    mu, sg = baseline["mu"], baseline["sigma"]
    return {"ucl_warning": mu + 2 * sg, "ucl_fault": mu + 3 * sg}


def _valid_baseline(d):
    try:
        return (d.get("source") == SOURCE_COMMISSIONED and math.isfinite(d["mu"]) and math.isfinite(d["sigma"])
                and 0 < d["mu"] <= MAX_MU_G and d["sigma"] > 0)
    except Exception:
        return False


class Commissioner:
    def __init__(self, baseline_path, clock=time.time):
        self.path = baseline_path
        self.clock = clock
        self.state = "idle"          # idle | running | done | failed
        self.message = ""
        self.samples = []
        self.windows_seen = 0
        self.windows_invalid = 0
        self.started = None
        self.last_sample_t = None
        self.target_s = TARGET_S
        self.baseline = default_baseline()
        self.load()

    # persistence: written once when a run is accepted (no per-sample SD-card writes)
    def load(self):
        try:
            with open(self.path) as f:
                d = json.load(f)
            if _valid_baseline(d):
                self.baseline = d
                return True
        except Exception:
            pass
        self.baseline = default_baseline()
        return False

    def _save(self, d):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(d, f, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)

    def start(self):
        if self.state == "running":
            return False
        self.state, self.message = "running", "collecting; operator reports the machine is healthy"
        self.samples, self.windows_seen, self.windows_invalid = [], 0, 0
        self.started, self.last_sample_t = self.clock(), None
        return True

    def cancel(self):
        if self.state == "running":
            self.state, self.message = "idle", "cancelled; baseline unchanged"
            self.samples = []
            return True
        return False

    def reset(self):
        """Back to the default baseline. The old file is kept under a dated name, not deleted."""
        if self.state == "running":
            self.cancel()
        if os.path.exists(self.path):
            os.replace(self.path, "%s.reset-%d" % (self.path, int(self.clock())))
        self.baseline = default_baseline()
        self.state, self.message = "idle", "reset to default baseline"
        return True

    def feed(self, rms_dyn, valid=True):
        """Call once per DAQ loop. Returns True when a run just finished (accepted or failed)."""
        if self.state != "running":
            return False
        now = self.clock()
        if self.last_sample_t is None or now - self.last_sample_t >= MIN_SAMPLE_GAP_S:
            self.last_sample_t = now
            self.windows_seen += 1
            if valid and rms_dyn is not None and math.isfinite(rms_dyn):
                self.samples.append(float(rms_dyn))
            else:
                self.windows_invalid += 1
        if now - self.started >= self.target_s:
            return self._finish()
        return False

    def _finish(self):
        frac = 1.0 - (self.windows_invalid / self.windows_seen) if self.windows_seen else 0.0
        if frac < MIN_VALID_FRACTION:
            ok, res, msg = False, None, "too many invalid windows (%.0f%% valid)" % (100 * frac)
        else:
            ok, res, msg = compute_baseline(self.samples)
        if ok:
            res.update({
                "started_at": self.started, "finished_at": self.clock(),
                "duration_s": round(self.clock() - self.started, 1),
                "motor_running_verified": False,
                "note": "Collected while the operator reported a healthy run; motor state was not measured.",
            })
            self._save(res)
            self.baseline, self.state, self.message = res, "done", "baseline accepted"
        else:
            self.state, self.message = "failed", msg + "; default baseline kept"
        self.samples = []
        return True

    def status(self):
        prog = 0.0
        if self.state == "running" and self.started is not None:
            prog = min(self.target_s, self.clock() - self.started)
        b = self.baseline
        return {
            "state": self.state, "message": self.message,
            "progress_s": round(prog, 1), "target_s": self.target_s,
            "windows": self.windows_seen, "invalid_windows": self.windows_invalid,
            "baseline_source": b["source"], "mu": b["mu"], "sigma": b["sigma"],
            "motor_running_verified": False,
        }
