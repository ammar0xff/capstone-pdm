"""Guards the device-only telemetry rule: no simulator can write to RTDB."""

import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDGE = os.path.join(ROOT, "edge")
PUBLIC = os.path.join(ROOT, "public")
HOSTED_PAGES = ("index.html", "guide.html", "calibration.html")
LOCAL_TEMPLATE = os.path.join(EDGE, "templates", "index.html")

SIMULATOR_TOKENS = (
    "toggleSimulator",
    "simScenario",
    "sim-tag-btn",
    "Physics Simulator",
    "runSimTick",
    "broadcastToCloud",
    'id="btn-sim"',
)
STREAM_TOKENS = (
    "firebaseio.com",
    "urllib",
    "random.",
    "--scenario",
    "healthy",
    "imbalance",
    "bearing",
    "thermal",
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


class DeviceOnlyTelemetryTest(unittest.TestCase):
    def test_stream_live_is_retired_without_network_or_random_frames(self):
        text = read(os.path.join(EDGE, "stream_live.py"))
        self.assertIn("SIMULATOR REMOVED", text)
        for token in STREAM_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(token, text)

    def test_stream_live_refuses_to_run_without_uploading(self):
        path = os.path.join(EDGE, "stream_live.py")
        result = subprocess.run(
            [sys.executable, path, "--scenario", "bearing"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("SIMULATOR REMOVED", result.stderr)
        self.assertNotIn("http", result.stderr)

    def test_only_cloud_mirror_can_put_to_rtdb(self):
        writers = []
        for name in sorted(os.listdir(EDGE)):
            if not name.endswith(".py"):
                continue
            path = os.path.join(EDGE, name)
            if 'method="PUT"' in read(path) or "method='PUT'" in read(path):
                writers.append(name)
        self.assertEqual(writers, ["firebase_mirror.py"])

    def test_no_simulator_controls_on_hosted_pages_or_local_template(self):
        paths = [os.path.join(PUBLIC, name) for name in HOSTED_PAGES]
        paths.append(LOCAL_TEMPLATE)
        for path in paths:
            text = read(path)
            for token in SIMULATOR_TOKENS:
                with self.subTest(path=os.path.basename(path), token=token):
                    self.assertNotIn(token, text)

    def test_hosted_dashboard_states_device_only_source(self):
        text = read(os.path.join(PUBLIC, "index.html"))
        self.assertIn("DEVICE TELEMETRY ONLY", text)
        self.assertIn('id="badge-seq">NO DATA', text)


if __name__ == "__main__":
    unittest.main()
