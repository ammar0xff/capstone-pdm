import csv, os, sys, tempfile, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "edge"))
import history_log as h


class T(unittest.TestCase):
    def mk(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, h.LEGACY_NAME)
        with open(p, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(h.COLUMNS_V1)
            w.writerow([1, 1, 0.4, 0.01, 3.0, 0.03, 23.0, 0.1, "Healthy", "Normal", 0.9])
            w.writerow([2, 2, 0.4, 0.01, 3.0, 2.5, 0.03, 23.0, 0.1, 60.0, 0.01, "Healthy", "Normal", 0.9])
            w.writerow(["broken", 1, 2])
        return d, p

    def test_legacy_header_goes_to_v2_and_raw_untouched(self):
        d, p = self.mk()
        before = open(p, "rb").read()
        self.assertTrue(h.resolve_history_path(d).endswith(h.V2_NAME))
        h.ensure_header(h.resolve_history_path(d))
        self.assertEqual(open(p, "rb").read(), before)

    def test_matching_or_missing_uses_legacy_name(self):
        d = tempfile.mkdtemp()
        self.assertTrue(h.resolve_history_path(d).endswith(h.LEGACY_NAME))
        h.ensure_header(os.path.join(d, h.LEGACY_NAME))
        self.assertTrue(h.resolve_history_path(d).endswith(h.LEGACY_NAME))

    def test_read_rows_maps_by_width_and_skips_broken(self):
        d, _ = self.mk()
        rows = h.read_rows(d)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["state"], "Healthy"); self.assertEqual(rows[1]["temp_c"], "23.0")
        self.assertEqual(rows[1]["sound_db"], "60.0")


if __name__ == "__main__":
    unittest.main()
