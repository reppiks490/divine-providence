import sys
from pathlib import Path
from oracle.adapters import *
from oracle.contracts import FinancialState,Hypothesis,ResearchJob,EvidenceRecord
BASE=Path(__file__).resolve().parents[2]
for p in [BASE/'ARGUS-MICROSTRUCTURE-OS_HANDOFF'/'argus-microstructure-os'/'src',BASE/'ATHENA-SUPERVISORY-FABRIC_HANDOFF'/'athena-supervisory-fabric'/'src',BASE/'DAEDALUS_WITH_BLUEPRINT_AND_INSTRUCTIONS'/'daedalus-research-os'/'src',BASE/'ICARUS-AION-MARKET-MEMORY-v0.1'/'icarus-aion']:
    sys.path.insert(0,str(p))

def state(): return FinancialState('s',1,{'risk':.4},.9,.1)

def test_aion_exact_contract_accepts_oracle_context():
    from aion.contracts import SourceSpec,Observation,validate_source_event
    spec=SourceSpec.from_dict(aion_source_spec(lineage_hash='a'*64))
    env=to_aion_context(record_id='r',event_ns=1,available_ns=2,ingested_ns=2,payload={'x':1},lineage_hash='a'*64)
    obs=Observation.from_dict(env['payload']); validate_source_event(spec,obs)

def test_argus_exact_contract_accepts_proxy_features():
    from argus.contracts import MicrostructureFeature,EvidenceTier
    rows=[MicrostructureFeature(**r) for r in to_argus_proxy_features(state())]
    assert rows and rows[0].evidence_tier==EvidenceTier.CANDLE_PROXY

def test_athena_exact_contract_accepts_request_and_provenance():
    from athena.contracts import ResearchRequest,Provenance,DataPlane
    j=ResearchJob('j','h','topology',1,.8,.9,.7,.5,.4,2.0,('ATHENA',),('stress',))
    r=ResearchRequest(**to_athena_research_request(j)); p=Provenance(**to_athena_provenance(state()))
    assert list(r.required_states)==['stress'] and p.plane is DataPlane.RESEARCH

def test_daedalus_bridge_keeps_candidate_research_only(tmp_path):
    from daedalus.bridge import export_candidate
    h=Hypothesis('h','f','statement','NQ','1h',('fail',),1)
    e=EvidenceRecord('e','h','NEXUS','market_state',1,{},'a'*64,.5,True)
    packet=to_daedalus_candidate(h,[e]); assert packet['production_authorized'] is False
    assert export_candidate(tmp_path/'candidate.json',packet['payload']).exists()
