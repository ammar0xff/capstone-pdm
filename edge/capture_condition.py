#!/usr/bin/env python3
"""Record one labelled WAV for the speech-filter joint test.

    python3 capture_condition.py motor_only 60
    python3 capture_condition.py speech_only 60 --pause-service
    python3 capture_condition.py both 60 --pause-service

Writes audio_dataset/<label>_<UTC timestamp>.wav (48 kHz, S32_LE, stereo, the
same format the live service uses) and a .json sidecar with what was recorded.

The microphone has one reader. If pdm-daq holds it, the script stops and says
so. With --pause-service it stops pdm-daq, records, and starts pdm-daq again in
a finally block, even on error or Ctrl-C. Nothing is changed otherwise. It restarts the service only if it was active before.
Use ARECORD and SYSTEMCTL env vars to substitute test doubles.
"""
import argparse, json, os, signal, subprocess, sys, time
from datetime import datetime, timezone

DEVICE = "plughw:1,0"
RATE = 48000
LABELS = ("motor_only", "speech_only", "both", "noise_only")


def mic_busy(fuser="fuser"):
    r = subprocess.run([fuser, "/dev/snd/pcmC1D0c"], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() != ""


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("label", choices=LABELS)
    p.add_argument("seconds", type=int)
    p.add_argument("--pause-service", action="store_true")
    p.add_argument("--outdir", default="audio_dataset")
    p.add_argument("--note", default="")
    a = p.parse_args(argv)
    if not 10 <= a.seconds <= 300:
        p.error("seconds must be 10..300")
    arecord = os.environ.get("ARECORD", "arecord")
    systemctl = os.environ.get("SYSTEMCTL", "systemctl")
    fuser = os.environ.get("FUSER", "fuser")
    os.makedirs(a.outdir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = os.path.join(a.outdir, "%s_%s.wav" % (a.label, stamp))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))  # run the finally block
    paused = False
    was_active = subprocess.run([systemctl, "is-active", "pdm-daq"], capture_output=True, text=True).stdout.strip() == "active"
    try:
        if a.pause_service and was_active:
            subprocess.run(["sudo", systemctl, "stop", "pdm-daq"], check=True)
            paused = True
            time.sleep(1.0)
        if mic_busy(fuser):
            print("Microphone is busy (another reader holds it). Not recording. Use --pause-service.")
            return 2
        if os.path.exists(path):
            print("Refusing to overwrite", path)
            return 3
        cmd = [arecord, "-D", DEVICE, "-c", "2", "-r", str(RATE), "-f", "S32_LE",
               "-d", str(a.seconds), "-t", "wav", path]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            out, err = proc.communicate()
        finally:
            # On SIGTERM/SIGINT/SystemExit the child must not keep the mic.
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()

        class _R:  # keep the later code simple
            returncode = proc.returncode
            stderr = err or ""
        r = _R
        if r.returncode != 0:
            print("arecord failed:", r.stderr.strip())
            return 1
        with open(path[:-4] + ".json", "w") as f:
            json.dump({"label": a.label, "seconds": a.seconds, "rate": RATE, "format": "S32_LE",
                       "channels": 2, "utc": stamp, "service_paused": paused, "service_was_active": was_active, "note": a.note,
                       "arecord_stderr": r.stderr.strip()}, f, indent=2)
        print("saved", path)
        return 0
    finally:
        # Restore only what we changed: start it again only if it was active before.
        # Enabled state and drop-ins are never touched.
        if paused:
            subprocess.run(["sudo", systemctl, "start", "pdm-daq"])
            print("pdm-daq start requested (it was active before); verify with: systemctl is-active pdm-daq")


if __name__ == "__main__":
    sys.exit(main())
