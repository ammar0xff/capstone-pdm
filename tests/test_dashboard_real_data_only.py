"""The hosted dashboard must show real telemetry only, never invented readings."""

import os
import re
import unittest
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD = os.path.join(ROOT, "public", "index.html")


class ElementTextParser(HTMLParser):
    """Collect the visible text of the first element with a given id."""

    def __init__(self, element_id):
        super().__init__(convert_charrefs=True)
        self.element_id = element_id
        self.depth = 0
        self.found = False
        self.done = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        if dict(attrs).get("id") == self.element_id and not self.found:
            self.found = True
            self.depth = 1
        elif self.found:
            self.depth += 1

    def handle_endtag(self, tag):
        if not self.found or self.done:
            return
        self.depth -= 1
        if self.depth == 0:
            self.done = True

    def handle_data(self, data):
        if self.found and not self.done:
            self.parts.append(data)

    @property
    def text(self):
        return " ".join(" ".join(self.parts).split())


def text_for(html, element_id):
    parser = ElementTextParser(element_id)
    parser.feed(html)
    if not parser.found:
        raise AssertionError(f"missing element id={element_id}")
    return parser.text


class HostedDashboardRealDataOnlyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DASHBOARD, encoding="utf-8") as handle:
            cls.html = handle.read()

    def test_initial_metric_cells_contain_no_fabricated_numbers(self):
        metric_ids = (
            "badge-ai-conf",
            "badge-gate-status",
            "badge-seq",
            "badge-uptime",
            "val-rms",
            "val-peak",
            "val-kurt",
            "val-cf",
            "val-temp",
            "val-slope",
            "val-coldj",
            "val-res",
            "val-sound-db",
            "val-sound-zcr",
            "val-spc-z",
            "val-sound-status",
            "txt-iso-zone",
            "txt-thermal-zone",
            "txt-sound-zone",
        )
        for element_id in metric_ids:
            with self.subTest(element_id=element_id):
                text = text_for(self.html, element_id)
                self.assertIsNone(
                    re.search(r"\d", text),
                    f"{element_id} shows an invented reading: {text!r}",
                )
                self.assertTrue(
                    any(
                        marker in text.upper()
                        for marker in ("NO DATA", "AWAITING", "NOT REPORTED")
                    ),
                    f"{element_id} must show an explicit unavailable state: {text!r}",
                )

    def test_initial_status_and_decision_text_waits_for_telemetry(self):
        self.assertEqual(text_for(self.html, "txt-cloud-status"), "AWAITING DATA")
        self.assertEqual(text_for(self.html, "status-title"), "Awaiting telemetry")
        for element_id in ("status-sub", "txt-advice", "txt-decision-timeframe"):
            with self.subTest(element_id=element_id):
                self.assertIsNone(re.search(r"\d", text_for(self.html, element_id)))
        self.assertEqual(text_for(self.html, "txt-decision-priority"), "AWAITING DATA")
        for element_id in ("txt-decision-owner",):
            self.assertNotRegex(text_for(self.html, element_id), r"\d")

    def test_initial_worked_equations_are_not_fake_results(self):
        for element_id in (
            "calc-rms",
            "calc-kurt",
            "calc-cf",
            "calc-spc",
            "calc-slope",
            "calc-sound",
        ):
            with self.subTest(element_id=element_id):
                text = text_for(self.html, element_id)
                self.assertIn("AWAITING", text.upper())
                self.assertIsNone(re.search(r"\d", text))

    def test_initial_severity_pointers_are_hidden(self):
        for element_id in ("iso-pointer", "temp-pointer", "sound-pointer"):
            with self.subTest(element_id=element_id):
                match = re.search(
                    rf'<[^>]+id="{element_id}"[^>]*>', self.html, re.DOTALL
                )
                self.assertIsNotNone(match, f"missing pointer {element_id}")
                self.assertIn("is-unavailable", match.group(0))
                self.assertNotRegex(match.group(0), r"left:\s*\d")

    def test_fallback_readers_do_not_invent_values(self):
        for token in (
            'data.state || "Healthy"',
            'data.fault || data.fault_label || "Normal Operation"',
            "data.fault_proba || 0.05",
            "data.vibration?.rms_dyn || 0.0094",
            "data.vibration?.peak_dyn || 0.028",
            "data.vibration?.kurtosis || 3.0",
            "data.vibration?.crest_factor || 2.0",
            "data.temperature?.temp_c || 24.25",
            "data.acoustic?.db_spl || 65.0",
            "data.acoustic?.zcr || 0.01",
            '"Machine operating within nominal limits."',
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, self.html)
        for helper in (
            "function readFinite",
            "function firstFinite",
            "function formatValue",
        ):
            with self.subTest(helper=helper):
                self.assertIn(helper, self.html)

    def test_telemetry_fields_are_read_without_numeric_defaults(self):
        for token in (
            "firstFinite(data.proba,",
            "firstFinite(data.rms,",
            "firstFinite(data.peak,",
            "firstFinite(data.kurt,",
            "firstFinite(data.cf,",
            "firstFinite(data.temp,",
            "firstFinite(data.slope,",
            "firstFinite(data.sound_db,",
            "firstFinite(data.zcr,",
            "firstFinite(data.ts)",
            "firstFinite(data.seq)",
            "firstFinite(data.uptime_s)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.html)

    def test_unavailable_metric_cells_drop_their_units(self):
        for element_id in (
            "val-rms",
            "val-peak",
            "val-kurt",
            "val-cf",
            "val-temp",
            "val-slope",
            "val-res",
            "val-sound-db",
            "val-sound-zcr",
            "val-spc-z",
        ):
            with self.subTest(element_id=element_id):
                self.assertEqual(text_for(self.html, element_id), "NO DATA")

    def test_reset_loops_use_arrays_not_comma_operator_strings(self):
        self.assertNotRegex(self.html, r"for \(const \w+ of \(")
        self.assertRegex(self.html, r'for \(const id of \[\s*"val-rms"')
        self.assertRegex(self.html, r'for \(const id of \["calc-rms"')

    def test_missing_values_render_as_unavailable(self):
        self.assertIn("NO DATA", self.html)
        self.assertIn("AWAITING DATA", self.html)
        self.assertIn("is-unavailable", self.html)
        self.assertNotIn("&mdash;", self.html)
        self.assertNotIn("\u2014", self.html)
        self.assertNotIn(r"\u2014", self.html)
        self.assertIn('if (value === null) return "NO DATA";', self.html)

    def test_presentation_only_and_decision_contract_are_preserved(self):
        for token in (
            "toggleSimulator",
            "simScenario",
            "broadcastToCloud",
            'id="btn-sim"',
            "/api/cal",
        ):
            with self.subTest(token=token):
                self.assertNotIn(token, self.html)
        for token in (
            'id="txt-decision-priority"',
            'id="txt-decision-timeframe"',
            "data.ai?.response_plan",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.html)


if __name__ == "__main__":
    unittest.main()
