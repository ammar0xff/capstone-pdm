"""Checks that the reported ML evidence matches the code that produced it."""

import json
import os
import sys
import unittest

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ml"))

from train_rf import (  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
