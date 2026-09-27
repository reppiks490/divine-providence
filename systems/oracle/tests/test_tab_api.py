from pathlib import Path
from oracle.automation import AutonomousResearchLoop
from oracle.contracts import FinancialState
from oracle.engine import OracleEngine
from oracle.operating import OracleOperatingLayer
from oracle.tab_api import OracleTabAPI
from oracle.trigger_policy import FinancialTriggerPolicy


def fs(t:int,ood:float)->FinancialState:
    return FinancialState(f'S{t}',t,{'nq':100+t},.9,ood,{'feed':.95})


def test_snapshot_is_stable_and_restart_reproducible(tmp_path:Path):
    db=tmp_path/'o.db'
    loop=AutonomousResearchLoop(OracleEngine(db)); op=OracleOperatingLayer(loop,trigger_policy=FinancialTriggerPolicy(cooldown_ns=0))
    op.ingest_financial_state(fs(1,.9))
    s1=OracleTabAPI(op).snapshot(1)
    assert not s1.production_authorized
    assert s1.snapshot_hash==OracleTabAPI(op).snapshot(1).snapshot_hash
    loop2=AutonomousResearchLoop(OracleEngine(db)); op2=OracleOperatingLayer(loop2,trigger_policy=FinancialTriggerPolicy(cooldown_ns=0))
    s2=OracleTabAPI(op2).snapshot(1)
    assert s2.snapshot_hash==s1.snapshot_hash


def test_tab_delta_identifies_financial_and_research_changes(tmp_path:Path):
    loop=AutonomousResearchLoop(OracleEngine(tmp_path/'o.db')); op=OracleOperatingLayer(loop,trigger_policy=FinancialTriggerPolicy(cooldown_ns=0))
    api=OracleTabAPI(op)
    op.ingest_financial_state(fs(1,.2)); a=api.snapshot(1)
    op.ingest_financial_state(fs(2,.9)); b=api.snapshot(2)
    d=api.delta(a,b)
    assert d.financial_changed
    assert d.changed_hypotheses
    assert d.from_hash!=d.to_hash
