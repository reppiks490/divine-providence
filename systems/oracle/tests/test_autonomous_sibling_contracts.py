import sys
from pathlib import Path
from oracle.automation import AutonomousResearchLoop
from oracle.engine import OracleEngine
from oracle.hypothesis_factory import Trigger

BASE=Path(__file__).resolve().parents[2]
for p in [
    BASE/'ARGUS-MICROSTRUCTURE-OS_HANDOFF'/'argus-microstructure-os'/'src',
    BASE/'ATHENA-SUPERVISORY-FABRIC_HANDOFF'/'athena-supervisory-fabric'/'src',
    BASE/'DAEDALUS_WITH_BLUEPRINT_AND_INSTRUCTIONS'/'daedalus-research-os'/'src',
    BASE/'ICARUS-AION-MARKET-MEMORY-v0.1'/'icarus-aion',
]: sys.path.insert(0,str(p))

def test_autonomous_fanout_preserves_all_sibling_authority_boundaries(tmp_path:Path):
    loop=AutonomousResearchLoop(OracleEngine(tmp_path/'oracle.db'))
    loop.submit_trigger(Trigger('topology_break',10,'NQ',.9,.9,{'entropy':.2},('a'*64,)),sensors=('VIX',))
    batch=loop.dispatch(11)
    assert len(batch.requests)==6
    by={}
    for req in batch.requests: by.setdefault(req.target_system,[]).append(req)
    assert set(by)=={'NEXUS','AION','ARGUS','ATHENA','DAEDALUS'}
    assert all(req.payload['production_authorized'] is False for req in batch.requests)

    # ATHENA receives its native research contract, never an advisory/risk override.
    from athena.contracts import ResearchRequest
    athena_body=by['ATHENA'][0].payload['payload']
    rr=ResearchRequest(**athena_body['athena_request'])
    assert rr.expected_information_gain>0 and rr.estimated_compute_cost>0

    # ARGUS request remains explicitly candle-proxy context and makes no order-flow truth claim.
    argus_body=by['ARGUS'][0].payload['payload']
    assert argus_body['query']['max_evidence_tier']=='CANDLE_PROXY'
    assert argus_body['query']['truth_claim'] is False

    # AION query is strict as-of/causal; ORACLE does not mutate AION's memory contract here.
    aion_body=by['AION'][0].payload['payload']
    assert aion_body['query']['causal_only'] is True and aion_body['query']['as_of_ns']==11

    # DAEDALUS accepts the autonomous request as a research-only candidate payload.
    from daedalus.bridge import export_candidate
    daedalus_body=by['DAEDALUS'][0].payload['payload']
    out=export_candidate(tmp_path/'candidate.json',daedalus_body)
    raw=out.read_text()
    assert 'RESEARCH_CANDIDATE_ONLY' in raw and '"production_authorized": false' in raw

    # NEXUS is queried for data/research products only, not production decisions.
    for req in by['NEXUS']:
        nexus=req.payload['payload']['nexus_request']
        assert nexus['production_authorized'] is False
        assert set(nexus['payload']['requested_products'])=={'aligned_state','factor_context','topology','source_health'}
