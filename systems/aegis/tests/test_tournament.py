import unittest
from challenger_forge.tournament import TournamentEvidence, decide_candidate

class TournamentTests(unittest.TestCase):
    def test_crossing_zero_cannot_promote(self):
        e=TournamentEvidence('x',100,4,4,3.0,-1.0,7.0,0.01)
        self.assertEqual(decide_candidate(e)['decision'],'QUARANTINE')
    def test_strong_candidate_can_promote_shadow(self):
        e=TournamentEvidence('x',120,4,4,5.0,1.5,8.0,0.01)
        self.assertEqual(decide_candidate(e)['decision'],'PROMOTE_SHADOW')
    def test_specialist_requires_same_rigor(self):
        e=TournamentEvidence('x',71,3,4,2.1,-19.3,27.4,1.0,specialist_scope='NORMAL')
        self.assertEqual(decide_candidate(e)['decision'],'QUARANTINE')
