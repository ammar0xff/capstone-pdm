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


class Edge(unittest.TestCase):
    def test_nul_partial_glued_and_nonnumeric_lines_skipped(self):
        d = tempfile.mkdtemp()
        good = "1.5,1,0.4,0.01,3.0,2.5,0.03,23.0,0.1,60.0,0.01,Healthy,Normal,0.9"
        with open(os.path.join(d, h.LEGACY_NAME), "wb") as f:
            f.write((",".join(h.COLUMNS_V1) + "\n").encode())
            f.write((good + "\n").encode())
            f.write(b"2,2,0.4,0.01,3.0,2.5,0.03,2\x00\x00\x00,0.1,60.0,0.01,Healthy,Normal,0.9\n")  # NUL
            f.write((good + "," + good + "\n").encode())  # glued: 28 fields
            f.write(b"abc,2,1,2\n")  # junk
            f.write(b"\xff\xfe,1,2\n")  # undecodable
            f.write(good.replace("1.5", "9.5").encode())  # unterminated last line
        rows = h.read_rows(d)
        self.assertEqual(len(rows), 1); self.assertEqual(rows[0]["timestamp"], "1.5")
        self.assertEqual(rows[0]["sound_db"], "60.0")

    def test_restart_does_not_duplicate_header(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, h.LEGACY_NAME)
        h.ensure_header(p); h.ensure_header(p)
        self.assertEqual(open(p).read().count("timestamp"), 1)

    def test_path_independent_of_cwd(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, h.LEGACY_NAME), "w") as f:
            f.write(",".join(h.COLUMNS_V1) + "\n")
        old = os.getcwd()
        try:
            os.chdir(tempfile.gettempdir())
            rel = os.path.relpath(d)
            self.assertEqual(h.resolve_history_path(rel), os.path.join(d, h.V2_NAME))
        finally:
            os.chdir(old)

    def test_v2_after_restart_reuses_v2(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, h.LEGACY_NAME), "w") as f:
            f.write(",".join(h.COLUMNS_V1) + "\n")
        v2 = h.resolve_history_path(d); h.ensure_header(v2); h.ensure_header(h.resolve_history_path(d))
        self.assertEqual(open(v2).read().count("timestamp"), 1)


if __name__ == "__main__":
    unittest.main()
