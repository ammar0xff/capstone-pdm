import os, stat, subprocess, sys, tempfile, unittest
EDGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "edge")
SCRIPT = os.path.join(EDGE, "capture_condition.py")


def fake(d, name, body):
    p = os.path.join(d, name)
    open(p, "w").write("#!/bin/sh\n" + body + "\n")
    os.chmod(p, 0o755)
    return p


class T(unittest.TestCase):
    def run_script(self, args, busy, fail=False, inactive=False):
        d = tempfile.mkdtemp()
        log = os.path.join(d, "log")
        env = dict(os.environ,
                   ARECORD=fake(d, "arecord", ("echo oops >&2; exit 1" if fail else 'for a; do last=$a; done; echo RIFF > "$last"; echo arecord >> %s' % log)),
                   SYSTEMCTL=fake(d, "systemctl", 'echo "$@" >> %s; [ "$1" = is-active ] && echo %s' % (log, "inactive" if inactive else "active")),
                   FUSER=fake(d, "fuser", ('echo 123; exit 0' if busy else 'exit 1')))
        # sudo shim: run the rest as is
        fake(d, "sudo", '"$@"')
        env["PATH"] = d + os.pathsep + env["PATH"]
        r = subprocess.run([sys.executable, SCRIPT] + args + ["--outdir", os.path.join(d, "a")], env=env, capture_output=True, text=True)
        return r, (open(log).read() if os.path.exists(log) else ""), d

    def test_busy_mic_refuses(self):
        r, log, _ = self.run_script(["motor_only", "10"], busy=True)
        self.assertEqual(r.returncode, 2); self.assertNotIn("arecord", log)

    def test_pause_records_and_restarts(self):
        r, log, d = self.run_script(["both", "10", "--pause-service"], busy=False)
        self.assertEqual(r.returncode, 0)
        self.assertIn("stop pdm-daq", log); self.assertIn("start pdm-daq", log)
        self.assertTrue(any(f.endswith(".json") for f in os.listdir(os.path.join(d, "a"))))

    def test_inactive_service_not_started(self):
        r, log, _ = self.run_script(["both", "10", "--pause-service"], busy=False, inactive=True)
        self.assertEqual(r.returncode, 0); self.assertNotIn("start pdm-daq", log); self.assertNotIn("stop pdm-daq", log)

    def test_failure_still_restarts(self):
        r, log, _ = self.run_script(["both", "10", "--pause-service"], busy=False, fail=True)
        self.assertEqual(r.returncode, 1); self.assertIn("start pdm-daq", log)


if __name__ == "__main__":
    unittest.main()
