
import unittest
from challenger_forge.robustness import (
    bootstrap_mean_ci, sign_flip_pvalue, purged_walk_forward_splits,
    MultipleTestingRecord, build_multiple_testing_ledger
)

class RobustnessTests(unittest.TestCase):
    def test_walk_forward_never_touches_holdout(self):
        folds=purged_walk_forward_splits(6314,2000,700,700,24,24,5051)
        self.assertEqual(len(folds),4)
        self.assertTrue(all(f["embargo"][1] <= 5051 for f in folds))

    def test_bootstrap_ci_contains_mean(self):
        x=[-2,-1,0,1,2,3,4]
        ci=bootstrap_mean_ci(x,n_bootstrap=1000,seed=1)
        self.assertLessEqual(ci["low"],ci["mean"])
        self.assertGreaterEqual(ci["high"],ci["mean"])

    def test_sign_flip_reasonable(self):
        p=sign_flip_pvalue([10,11,9,12,8,13],n_perm=1000,seed=1)
        self.assertLess(p,0.05)

    def test_multiple_testing_adjusts_upward(self):
        rec=[
            MultipleTestingRecord("a","x","e",0.01,"mean","c"),
            MultipleTestingRecord("b","x","e",0.04,"mean","c")
        ]
        led=build_multiple_testing_ledger(rec)
        self.assertGreaterEqual(led[0]["bonferroni_p"],led[0]["raw_p"])
        self.assertGreaterEqual(led[1]["bh_fdr_p"],led[1]["raw_p"])
