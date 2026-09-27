from oracle.nexus_ingest import metric_observations_from_nexus_bundle
from oracle.financial import FinancialStateEngine

def test_nexus_bundle_becomes_financial_state_without_invented_fields():
    b={'decision_ns':100,'frame_hash':'a'*64,'factors':{'risk':.2},'topology':{'entropy':.7},'quality':{'coverage':.9},'ood':{'score':.3},'source_health':{'fleet_health':.8}}
    rows=metric_observations_from_nexus_bundle(b,ingested_ns=101)
    assert len(rows)==4
    e=FinancialStateEngine(); [e.ingest(x) for x in rows]; s=e.build(100,ood_score=.3)
    assert s.features['factors.risk']==.2 and s.source_health
