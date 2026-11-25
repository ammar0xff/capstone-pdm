import os, shutil, subprocess, unittest

HERE = os.path.dirname(os.path.abspath(__file__))


class DashboardBehaviourTest(unittest.TestCase):
    def test_node_behaviour_checks(self):
        node = shutil.which("node") or os.path.expanduser("~/.nvm/versions/node/v22.23.5/bin/node")
        if not os.path.exists(node):
            self.skipTest("node not available")
        r = subprocess.run([node, os.path.join(HERE, "dashboard_behavior.js")], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
