
import unittest
from challenger_forge.core import ComponentContext
from challenger_forge.pivot import ConfirmedPivotAdapter, LeakyBackdatedPivotAdapter
from challenger_forge.causality import audit_prefix_invariance

class CausalityTests(unittest.TestCase):
    def setUp(self):
        # Multiple obvious extrema with future confirmation required.
        high = [10,11,13,12,11,12,15,14,13,14,16,15,14,13,15]
        low  = [ 8, 9,10, 9, 8, 9,11,10, 9,10,12,11,10, 9,10]
        close=[ 9,10,12,10, 9,11,14,12,10,13,15,13,11,10,14]
        self.ctx = ComponentContext(
            corpus_ids=["SYNTH-CAUSALITY-001"],
            timestamps=list(range(len(high))),
            series={"high":high,"low":low,"close":close}
        )

    def test_confirmed_pivot_is_prefix_invariant(self):
        audit = audit_prefix_invariance(ConfirmedPivotAdapter(left=2,right=2), self.ctx)
        self.assertTrue(audit.passed, audit.violations)

    def test_backdated_pivot_is_detected(self):
        audit = audit_prefix_invariance(LeakyBackdatedPivotAdapter(left=2,right=2), self.ctx)
        self.assertFalse(audit.passed)
        self.assertGreater(len(audit.violations), 0)
        self.assertTrue(any(v.full_value is not None and v.prefix_value is None for v in audit.violations))
