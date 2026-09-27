from pathlib import Path
import pytest
from oracle.contracts import FinancialState,HypothesisStatus,ResearchJob,EvidenceRecord,PromotionEvidence
from oracle.financial import FinancialStateEngine,MetricObservation
from oracle.hypothesis_factory import Trigger
from oracle.engine import OracleEngine
from oracle.counterfactual import standard_attack_suite
from oracle.eventbus import DeterministicEventBus
from oracle.lifecycle import feature_gate


def test_financial_state_is_causal_and_health_weighted():
    e=FinancialStateEngine()
    e.ingest(MetricObservation('risk',1.0,1,2,2,'NEXUS','a',.9,.8,'a'*64))
    e.ingest(MetricObservation('risk',2.0,2,5,5,'NEXUS','b',.8,1.0,'b'*64))
    assert e.build(4).features['risk']==1.0
    s=e.build(5)
    assert s.features['risk']==2.0 and s.confidence>0 and not s.production_authorized


def test_oracle_end_to_end_research_loop(tmp_path:Path):
    o=OracleEngine(tmp_path/'oracle.db')
    h=o.ingest_trigger(Trigger('topology_break',10,'NQ',.9,.9,{'entropy':.2},('a'*64,)))
    j=o.create_research_job(h.hypothesis_id,now_ns=11,task_type='historical_analogue',expected_information_gain=.9,strategic_relevance=.9,evidence_deficit=.8,novelty=.8,estimated_compute_cost=2.0,required_systems=('AION','DAEDALUS'))
    assert o.scheduler.rank(11)[0].job_id==j.job_id
    e=EvidenceRecord('e1',h.hypothesis_id,'AION','historical_analogue',12,{'matches':37},'b'*64,.8,True)
    o.contribute(h.hypothesis_id,e,claim='analogs support follow-up',submitted_ns=12)
    a=o.assess(h.hypothesis_id,assessed_ns=13,robustness_score=.6,regime_fit=.5,data_confidence=.8,ood_risk=.2)
    assert a.support_score>0 and a.evidence_coverage>0 and o.ledger.verify()
    assert o.store.queued_job_ids()==(j.job_id,)


def test_counterfactual_suite_is_falsification_first():
    purposes={x.purpose for x in standard_attack_suite('h',1,('NVDA','VIX'))}
    assert {'sensor_ablation','leakage_attack','null_attack','cost_stress','threshold_stress'}<=purposes


def test_eventbus_is_deterministic_and_idempotent():
    b=DeterministicEventBus(); out=[]
    b.subscribe('x','b',lambda e:out.append('b')); b.subscribe('x','a',lambda e:out.append('a'))
    b.publish('x',1,{'x':1},'a'*64); b.publish('x',1,{'x':1},'a'*64)
    assert out==['a','b']


def test_feature_gate_remains_non_execution():
    ok,reasons=feature_gate(PromotionEvidence(True,True,True,True,False,.1))
    assert ok and not reasons
