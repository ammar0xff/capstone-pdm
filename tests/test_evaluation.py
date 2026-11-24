"""Checks that the reported ML evidence matches the code that produced it."""

import json
import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ml"))

from train_rf import (  # noqa: E402
    FEATURE_COLS,
    META_FILE,
    assert_disjoint,
    group_holdout_split,
    load_dataset,
    make_cv,
)
from rf_predictor import PdMClassifier  # noqa: E402


class GroupEvaluationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.X, cls.y, cls.groups = load_dataset()

    def test_holdout_is_run_disjoint_and_class_balanced(self):
        train, val, test = group_holdout_split(self.y, self.groups)
        assert_disjoint(self.groups, train, val, test)
        self.assertEqual(len(train) + len(val) + len(test), len(self.y))
        for idx in (train, val, test):
            self.assertEqual(set(self.y[idx]), set(np.unique(self.y)))
        self.assertAlmostEqual(len(train) / len(self.y), 0.70, delta=0.03)

    def test_cv_folds_are_run_disjoint(self):
        fold_test_runs = []
        for train, test in make_cv().split(self.X, self.y, self.groups):
            assert_disjoint(self.groups, train, test)
            fold_test_runs.append(set(self.groups[test]))
        self.assertEqual(len(fold_test_runs), 5)
        for i in range(len(fold_test_runs)):
            for j in range(i + 1, len(fold_test_runs)):
                self.assertFalse(fold_test_runs[i] & fold_test_runs[j])

    def test_holdout_rejects_class_with_too_few_runs(self):
        y = np.array([0, 0, 0, 1, 1])
        groups = np.array(["a", "a", "b", "b", "c"])
        with self.assertRaises(ValueError):
            group_holdout_split(y, groups)

    def test_metadata_reports_the_same_grouping_and_feature_policy(self):
        with open(META_FILE) as f:
            meta = json.load(f)
        self.assertIn("GroupKFold", meta["cv_scheme"])
        self.assertEqual(meta["group_column"], "run_id")
        self.assertEqual(set(meta["gate_only_features"]), {"z_score"})
        self.assertNotIn("z_score", meta["features"])
        train, val, test = group_holdout_split(self.y, self.groups)
        for key, idx in (
            ("train_groups", train),
            ("val_groups", val),
            ("test_groups", test),
        ):
            self.assertEqual(set(meta[key]), set(self.groups[idx]))
        self.assertIn("training host", meta["latency_measured_on"])

    def test_z_score_is_a_gate_metric_derived_from_rms(self):
        clf = PdMClassifier()
        rms = 0.05  # normal band: Stage 1 returns Healthy without waking the RF
        result = clf.predict({"rms_dyn": rms, "temp_c": 26.0}, return_gate_info=True)
        expected = (rms - clf.spc_baseline_rms) / clf.spc_sigma_rms
        self.assertEqual(len(result), 5)
        self.assertAlmostEqual(result[4]["z_score"], round(expected, 2))
        self.assertFalse(result[4]["rf_executed"])


class TeamFollowUpTest(unittest.TestCase):
    """Evidence requested in the G12 team discussion (read-only request, no chat writes)."""

    REPORT = os.path.join(ROOT, "ml", "ai_report.md")
    DASHBOARD = os.path.join(ROOT, "public", "index.html")
    EDGE_DAQ = os.path.join(ROOT, "edge", "edge_daq.py")
    PRIORITIES = ["ROUTINE", "SCHEDULE", "URGENT", "CRITICAL"]

    def test_response_plan_is_structured_for_every_class(self):
        clf = PdMClassifier()
        priorities = []
        for class_id in range(4):
            plan = clf.get_response_plan(class_id)
            for key in (
                "class",
                "priority",
                "action",
                "timeframe",
                "owner",
                "rationale",
            ):
                self.assertTrue(plan[key], f"class {class_id}: empty {key}")
            self.assertIn(plan["priority"], self.PRIORITIES)
            priorities.append(plan["priority"])
        self.assertEqual(priorities, self.PRIORITIES)
        for bad_class in (-1, 4, 99, 1.5, "1", None):
            with self.subTest(bad_class=bad_class):
                with self.assertRaises(ValueError):
                    clf.get_response_plan(bad_class)

    def test_predict_exposes_the_post_classification_decision(self):
        clf = PdMClassifier()
        nominal = clf.predict({"rms_dyn": 0.05, "temp_c": 26.0}, return_gate_info=True)
        breach = clf.predict(
            {
                "rms_dyn": 0.20,
                "peak_dyn": 0.55,
                "crest_factor": 5.5,
                "kurtosis": 9.0,
                "temp_c": 72.0,
                "temp_slope": 12.0,
            },
            return_gate_info=True,
        )
        for result in (nominal, breach):
            plan = result[4]["response_plan"]
            self.assertEqual(plan["class"], result[1])
            self.assertTrue(result[3])  # advice text reaches the operator
        self.assertFalse(nominal[4]["rf_executed"])
        self.assertTrue(breach[4]["rf_executed"])

    def test_edge_packet_and_dashboard_carry_the_decision(self):
        with open(self.EDGE_DAQ) as f:
            edge = f.read()
        self.assertIn("predict(feature_dict, return_gate_info=True)", edge)
        self.assertIn('"response_plan": response_plan', edge)

        with open(self.DASHBOARD) as f:
            html = f.read()
        for token in (
            'id="txt-decision-priority"',
            'id="txt-decision-timeframe"',
            "data.ai?.response_plan",
        ):
            self.assertIn(token, html)

    def test_ifelse_baseline_is_weaker_and_documented(self):
        X, y, groups = load_dataset()
        _, _, test = group_holdout_split(y, groups)
        rf = PdMClassifier()
        rules = PdMClassifier()
        rules.model = None  # exercises the documented if/else fallback
        accuracies = {}
        for name, clf in (("rf", rf), ("ifelse", rules)):
            correct = 0
            for idx in test:
                features = {col: float(X[idx, j]) for j, col in enumerate(FEATURE_COLS)}
                correct += int(clf.predict(features)[0] == y[idx])
            accuracies[name] = correct / len(test)
        self.assertGreaterEqual(accuracies["rf"], 0.95)
        self.assertLess(accuracies["ifelse"], accuracies["rf"])
        self.assertAlmostEqual(accuracies["ifelse"], 0.885, delta=0.01)
        with open(self.REPORT) as f:
            report = f.read()
        self.assertIn("Results Register", report)
        self.assertIn("Role of AI", report)
        self.assertIn("88.5%", report)

    def test_dashboard_has_no_simulation_controls(self):
        with open(self.DASHBOARD) as f:
            html = f.read()
        for token in (
            "toggleSimulator",
            "simScenario",
            "sim-tag-btn",
            "Physics Simulator",
            "runSimTick",
            "broadcastToCloud",
            'id="btn-sim"',
        ):
            self.assertNotIn(token, html)


class DocumentationHonestyTest(unittest.TestCase):
    """Docs must not promote unmeasured resource, timing or source claims."""

    DOCS = os.path.join(ROOT, "docs")
    CLAIM_FILES = {
        "README.md": os.path.join(ROOT, "README.md"),
        "CAPSTONE_MASTER_HANDBOOK.md": os.path.join(
            DOCS, "CAPSTONE_MASTER_HANDBOOK.md"
        ),
        "LITERATURE_REFERENCES.md": os.path.join(DOCS, "LITERATURE_REFERENCES.md"),
        "STUDENT_MASTER_GUIDE.md": os.path.join(DOCS, "STUDENT_MASTER_GUIDE.md"),
        "PROJECT_COMPLETE_TUTORIAL.md": os.path.join(
            DOCS, "PROJECT_COMPLETE_TUTORIAL.md"
        ),
        "G12_REQUEST_RESPONSE_REGISTER.md": os.path.join(
            DOCS, "G12_REQUEST_RESPONSE_REGISTER.md"
        ),
        "ai_report.md": os.path.join(ROOT, "ml", "ai_report.md"),
    }
    FORBIDDEN_CLAIMS = (
        ">90%",
        "<8%",
        "3-sigma monitoring",
        "under 1.5 seconds",
        "uses a 2-of-3 rule",
        "in \u2264 5 seconds",
    )

    def test_unverified_resource_and_timing_claims_are_removed(self):
        for name, path in self.CLAIM_FILES.items():
            with self.subTest(file=name):
                with open(path) as f:
                    text = f.read()
                for claim in self.FORBIDDEN_CLAIMS:
                    self.assertNotIn(claim, text, f"{name}: {claim}")

    def test_gate_threshold_is_documented_as_configured_two_sigma(self):
        with open(self.CLAIM_FILES["LITERATURE_REFERENCES.md"]) as f:
            literature = f.read()
        self.assertIn("z-score > 2.0", literature)
        self.assertNotIn("3\u03c3", literature)
        with open(self.CLAIM_FILES["CAPSTONE_MASTER_HANDBOOK.md"]) as f:
            handbook = f.read()
        self.assertIn("configured 2.0-sigma", handbook)

    def test_dataset_range_traceability_exists_and_is_honest(self):
        path = os.path.join(self.DOCS, "DATASET_RANGE_TRACEABILITY.md")
        self.assertTrue(os.path.exists(path), "missing range-to-source register")
        with open(path) as f:
            text = f.read()
        for token in (
            "F_R_NOMINAL",
            "3200 Hz",
            "1800 RPM",
            "[NEED:",
            "SPC baseline mismatch",
        ):
            self.assertIn(token, text)


class G12ResponseRegisterTest(unittest.TestCase):
    """The 13 forwarded G12 requests are answered without inventing measurements."""

    REGISTER = os.path.join(ROOT, "docs", "G12_REQUEST_RESPONSE_REGISTER.md")
    TUTORIAL = os.path.join(ROOT, "docs", "PROJECT_COMPLETE_TUTORIAL.md")
    HANDBOOK = os.path.join(ROOT, "docs", "CAPSTONE_MASTER_HANDBOOK.md")
    GENERATOR = os.path.join(ROOT, "ml", "dataset_generator.py")
    SERVICE = os.path.join(ROOT, "edge", "pdm-daq.service")

    @classmethod
    def setUpClass(cls):
        for name in ("REGISTER", "TUTORIAL", "HANDBOOK", "GENERATOR", "SERVICE"):
            with open(getattr(cls, name)) as f:
                setattr(cls, name.lower() + "_text", f.read())

    def test_all_thirteen_requests_and_statuses_are_present(self):
        for number in range(1, 14):
            with self.subTest(request=number):
                self.assertIn(f"| {number} |", self.register_text)
        for status in ("✅ تم", "◐", "⛔ متوقف", "لا ينطبق"):
            self.assertIn(status, self.register_text)

    def test_register_contains_direct_answers_and_evidence(self):
        for token in (
            "ml/dataset_generator.py:58-72",
            "edge/edge_daq.py:405-406",
            "rf_executed=False",
            "pdm-daq.service",
            "ليس كل ملف يُرفع يعمل",
            "Results Register",
            "[NEED: run-to-failure series",
            "MathWorks",
            "crossings/sample",
            "9 features",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.register_text)

    def test_register_does_not_promote_unmeasured_results(self):
        for token in (
            "100% on real motor",
            "measured CPU savings",
            "actual cost measured",
            "remaining runtime forecast",
        ):
            self.assertNotIn(token, self.register_text)

    def test_traceability_line_references_match_generator(self):
        with open(self.GENERATOR) as f:
            lines = f.readlines()
        self.assertIn("F_R_NOMINAL = 30.0", lines[57])  # 1-based line 58
        self.assertIn("FS_VIB = 3200.0", lines[58])  # 1-based line 59
        self.assertIn("spc_mu_0 = 0.038", lines[228])  # 1-based line 229

    def test_equation_and_unit_fixes_are_visible_in_docs_and_code(self):
        self.assertIn("9 Dimensions", self.handbook_text)
        self.assertIn("crossings/sample", self.handbook_text)
        self.assertIn("does NOT integrate that ODE", self.generator_text)
        self.assertNotIn("3-sigma screening gating", self.generator_text)
        self.assertNotIn("<8%", self.tutorial_text)
        self.assertIn("RestartSec=3", self.tutorial_text)
        self.assertNotIn("RestartSec=5", self.tutorial_text)
        self.assertIn("Restart=always", self.service_text)


if __name__ == "__main__":
    unittest.main()
