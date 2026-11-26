"""The hosted dashboard shows only packet values, labels what is unvalidated, and carries no invented claims."""

import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = open(os.path.join(ROOT, "public", "index.html"), encoding="utf-8").read()


def text_for(element_id):
    m = re.search(r'id="%s"[^>]*>(.*?)</' % re.escape(element_id), HTML, re.S)
    if not m:
        raise AssertionError(f"missing element id={element_id}")
    return " ".join(re.sub(r"<[^>]+>", "", m.group(1)).split())


class DashboardTruthTest(unittest.TestCase):
    def test_initial_cells_hold_no_numbers(self):
        for i in ["val-rms", "val-peak", "val-kurt", "val-cf", "val-temp", "val-slope",
                  "val-sound-db", "val-sound-zcr", "val-sound-rms", "val-tc", "val-open", "val-mic", "badge-age"]:
            self.assertEqual(text_for(i), "NO DATA", i)
        self.assertEqual(text_for("txt-cloud-status"), "AWAITING DATA")
        self.assertEqual(text_for("status-title"), "Awaiting telemetry")

    def test_removed_claims_are_absent(self):
        for token in ["ISO 10816", "Zone A", "Severity Zone", "badge-ai-conf", "AI Confidence", "calc-rms",
                      "val-spc-z", "0.080", "0.025", "Severe Rubbing", "Runaway Threshold", "Blok ODE",
                      "CRITICAL FAULT", "trip risk", "Calibrated industrial", "CWRU induction motor",
                      "C-MAPSS FD001", "FMCG induction motor", "XJTU-SY</span>", "1.000", "val-res", "val-coldj",
                      "data.proba", "fault_proba", "3-Phase AC Induction"]:
            self.assertNotIn(token, HTML, token)

    def test_no_numeric_defaults_or_em_dashes(self):
        for token in ["|| 0", "?? 0", "Math.random", "\u2014", "&mdash;"]:
            self.assertNotIn(token, HTML, token)
        self.assertIn('if (value === null) return "NO DATA";', HTML)

    def test_states_are_labelled(self):
        for token in ["No live data", "That is old", "has not been tested on real faults",
                      "NOT OUR MOTOR", "EXPLORATORY", "not demonstrated on a whole motor", "no validated RUL exists"]:
            self.assertIn(token, HTML, token)

    def test_benchmark_numbers_match_recorded_result(self):
        for token in ["99.86%", "about 41%", "84.3%", "15.7%", "cbv7jyx4p9", "PMC10327369", "CC BY 4.0"]:
            self.assertIn(token, HTML, token)

    def test_state_comes_from_packet_only(self):
        self.assertIn('["Healthy", "Warning", "Fault"].includes(state)', HTML)
        self.assertIn("firstFinite(data.ts)", HTML)

    def test_page_is_not_overwide_on_phones(self):
        self.assertIn("minmax(0, 1fr)", HTML)


if __name__ == "__main__":
    unittest.main()


class GuideTruthTest(unittest.TestCase):
    def test_guide_has_no_withdrawn_benchmark_claims(self):
        g = open(os.path.join(ROOT, "public", "guide.html"), encoding="utf-8").read()
        for token in ["C-MAPSS", "CWRU", "FMCG", "XJTU", "PRONOSTIA", "94.0%", "67.7%", "1.000 (100.0%)"]:
            self.assertNotIn(token, g, token)
        for token in ["99.86%", "about 41%", "Remaining life not demonstrated"]:
            self.assertIn(token, g, token)
