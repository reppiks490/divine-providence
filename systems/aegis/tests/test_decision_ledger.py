import unittest
from challenger_forge.decision_ledger import LedgerEntry,DecisionLedger
class LedgerTests(unittest.TestCase):
    def test_tombstone_and_revive_are_reversible(self):
        l=DecisionLedger(); l.record(LedgerEntry("x","1","ACTIVE")); self.assertTrue(l.is_active("x"))
        l.tombstone("x","2","failed validation"); self.assertFalse(l.is_active("x"))
        l.revive("x","3","new independent evidence","2"); self.assertTrue(l.is_active("x"))
