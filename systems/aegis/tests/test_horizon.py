import unittest
from challenger_forge.horizon import HorizonSignal,reconcile_horizons
class HorizonTests(unittest.TestCase):
    def test_conflict_forces_abstention(self):
        r=reconcile_horizons([HorizonSignal("1h",1,.8),HorizonSignal("4h",-1,.9)])
        self.assertTrue(r["abstain"]); self.assertEqual(r["reason"],"horizon_disagreement")
    def test_consensus_passes(self):
        r=reconcile_horizons([HorizonSignal("1h",1,.8),HorizonSignal("4h",1,.7)])
        self.assertFalse(r["abstain"]); self.assertEqual(r["direction"],1)
