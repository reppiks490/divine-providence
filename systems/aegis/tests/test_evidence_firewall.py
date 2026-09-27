import unittest
from challenger_forge.evidence_firewall import EvidenceNode,detect_cycles,independent_evidence
class FirewallTests(unittest.TestCase):
    def test_duplicate_observation_not_double_counted(self):
        a=EvidenceNode("a","obs1","s1")
        b=EvidenceNode("b","obs1","s2")
        r=independent_evidence([a,b])
        self.assertTrue(r["passed"]); self.assertEqual(len(r["independent"]),1); self.assertEqual(r["duplicates"],["b"])
    def test_cycle_is_rejected(self):
        a=EvidenceNode("a","o1","s1",["b"]); b=EvidenceNode("b","o2","s2",["a"])
        r=independent_evidence([a,b])
        self.assertFalse(r["passed"]); self.assertEqual(r["reason"],"circular_evidence")
