"""verify.py - build the .fzz, export it headlessly, audit the export.

One command, one truth chain:

  1. python3 build_fzz.py        -> rebuild PDM_Predictive_Maintenance.fzz
  2. Fritzing -svg fztest        -> exported breadboard SVG (Fritzing's own
                                    renderer is the reference geometry)
  3. python3 check_export.py     -> geometric audit of that SVG

Requires the CD-625 Fritzing bundle and its patched libraries:
    /tmp/opencode/fz625/lib/Fritzing
    /tmp/opencode/fzlibs/usr/lib/x86_64-linux-gnu
"""
import os
import shutil
import subprocess
import sys

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from setup_fz import BASE, find_binary            # noqa: E402

CIRCUIT = os.path.dirname(HERE)
PROJ = "PDM_Predictive_Maintenance"
FZ = BASE                                        # setup_fz.py install root
LIBS = os.path.join(FZ, "usr", "lib", "x86_64-linux-gnu")
WORK = "/tmp/opencode/fztest"

ENV = dict(os.environ,
           LD_LIBRARY_PATH=f"{LIBS}:{FZ}/lib",
           QT_QPA_PLATFORM="offscreen")


def run(cmd, env=ENV, **kw):
    print("$", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, **kw)
    if proc.stdout.strip():
        print(proc.stdout.rstrip())
    if proc.stderr.strip():
        print(proc.stderr.rstrip())
    if proc.returncode:
        print(f"!! exit {proc.returncode}")
        return False
    return True


def main():
    steps = [
        [sys.executable, os.path.join(HERE, "build_fzz.py")],
        None,   # placeholder, replaced below
        [sys.executable, os.path.join(HERE, "check_export.py"),
         os.path.join(WORK, PROJ + "_breadboard.svg")],
    ]

    # fresh export folder
    shutil.rmtree(WORK, ignore_errors=True)
    os.makedirs(WORK)
    shutil.copyfile(os.path.join(CIRCUIT, PROJ + ".fzz"),
                    os.path.join(WORK, PROJ + ".fzz"))
    # call the real Qt binary; Debian's /usr/bin wrapper hard-codes system paths
    binary = find_binary()
    if binary is None:
        run([sys.executable, os.path.join(HERE, "setup_fz.py")])
        binary = find_binary()
    if binary is None:
        print("!! Fritzing binary still missing after setup")
        return 1
    export = [binary, "-svg", WORK]
    parts = os.path.join(FZ, "usr", "share", "fritzing", "parts")
    ok = run(export)
    produced = os.path.join(WORK, PROJ + "_breadboard.svg")
    if not os.path.exists(produced) and os.path.isdir(parts):
        print("retrying with explicit parts library", flush=True)
        ok = run([binary, "--parts", parts, "-svg", WORK])
        if not os.path.exists(produced):
            print("retrying with -f", flush=True)
            ok = run([binary, "-f", os.path.dirname(parts), "-svg", WORK])
    for f in sorted(os.listdir(WORK)):
        if f.endswith(".svg"):
            print(f"   {f}: {os.path.getsize(os.path.join(WORK, f))} bytes")

    ok = True
    for cmd in steps:
        if cmd is None:
            continue
        if not run(cmd):
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
