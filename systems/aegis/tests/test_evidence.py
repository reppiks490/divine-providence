
import unittest
from challenger_forge.evidence import EvidenceRecord, grade_evidence

class EvidenceTests(unittest.TestCase):
    def test_review_cannot_be_direct_performance_evidence(self):
        r=EvidenceRecord("x","review","academic",True,review_article=True,citation_count=500)
        self.assertEqual(grade_evidence(r)["grade"],"TAXONOMY_REVIEW")

    def test_no_oos_caps_grade(self):
        r=EvidenceRecord("x","weak","academic",True,out_of_sample=False,transaction_costs=True,long_sample=True,citation_count=100)
        self.assertNotIn(grade_evidence(r)["grade"],{"A","B"})

    def test_strong_oos_costed_evidence_can_reach_A(self):
        r=EvidenceRecord("x","strong","academic",True,out_of_sample=True,transaction_costs=True,
                         trading_delays_or_latency=True,survivor_bias_control=True,long_sample=True,
                         cross_market_or_multi_market=True,time_series_cv=True,citation_count=100)
        self.assertEqual(grade_evidence(r)["grade"],"A")
