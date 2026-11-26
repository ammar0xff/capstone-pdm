import json, os, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__))
import shutil
STAGED = os.path.join(HERE, "..", "pi_deployed", "staged_not_applied")
_tmp = tempfile.mkdtemp()
shutil.copy(os.path.join(STAGED, "dashboard.py.g28"), os.path.join(_tmp, "dashboard.py"))
sys.path.insert(0, _tmp)
try:
    import flask  # noqa: F401
except ImportError:
    flask = None


@unittest.skipIf(flask is None, "flask not installed")
class TestEndpoint(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        os.environ["G12_STATE_DIR"] = self.d
        sys.modules.pop("dashboard", None)
        sys.modules.setdefault("history_log", type(sys)("history_log")).read_rows = lambda b: []
        import dashboard
        self.m = dashboard
        self.cmdf = os.path.join(self.d, "commission_cmd.json")
        self.cl = dashboard.app.test_client()

    def post(self, body, addr="127.0.0.1", ctype="application/json"):
        data = json.dumps(body) if ctype == "application/json" else body
        return self.cl.post("/api/commissioning", data=data, content_type=ctype, environ_overrides={"REMOTE_ADDR": addr})

    def test_start_queues_command(self):
        r = self.post({"cmd": "start", "confirm": True})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(json.load(open(self.cmdf))["cmd"], "start")

    def test_requires_confirm_and_valid_cmd(self):
        for b in ({"cmd": "start"}, {"cmd": "start", "confirm": "yes"}, {"cmd": "set_mu", "confirm": True}, {}):
            self.assertEqual(self.post(b).status_code, 400)
        self.assertFalse(os.path.exists(self.cmdf))

    def test_form_post_rejected(self):
        self.assertEqual(self.post("cmd=start&confirm=true", ctype="application/x-www-form-urlencoded").status_code, 400)
        self.assertFalse(os.path.exists(self.cmdf))

    def test_public_address_rejected(self):
        self.assertEqual(self.post({"cmd": "start", "confirm": True}, addr="8.8.8.8").status_code, 403)
        self.assertFalse(os.path.exists(self.cmdf))

    def test_tailscale_and_lan_allowed(self):
        for a in ("100.126.244.75", "192.168.1.20", "10.1.2.3"):
            self.assertEqual(self.post({"cmd": "cancel", "confirm": True}, addr=a).status_code, 200, a)

    def test_cannot_set_thresholds(self):
        r = self.post({"cmd": "start", "confirm": True, "mu": 5, "sigma": 0.0001})
        self.assertEqual(json.load(open(self.cmdf)), {"cmd": "start", "ts": json.load(open(self.cmdf))["ts"]})


if __name__ == "__main__":
    unittest.main()
