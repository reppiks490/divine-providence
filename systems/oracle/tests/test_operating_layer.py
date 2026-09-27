from pathlib import Path
from oracle.automation import AutonomousResearchLoop
from oracle.contracts import FinancialState, ThesisAssessment
from oracle.engine import OracleEngine
from oracle.operating import OracleOperatingLayer
from oracle.scheduler import rank_jobs_adaptive
from oracle.thesis import ThesisPolicy
from oracle.trigger_policy import FeatureTriggerSpec, FinancialTriggerPolicy


def state(t:int,*,ood:float=.2,confidence:float=.9,feature:float=1.0,health:float=.9)->FinancialState:
    return FinancialState(f"S{t}",t,{"spread":feature},confidence,ood,{"feed":health})


def test_trigger_hysteresis_and_restart_are_durable(tmp_path:Path):
    db=tmp_path/'oracle.db'
    loop=AutonomousResearchLoop(OracleEngine(db))
    op=OracleOperatingLayer(loop,trigger_policy=FinancialTriggerPolicy(cooldown_ns=100,ood_enter=.8,ood_exit=.6))
    r1=op.ingest_financial_state(state(10,ood=.9))
    assert r1.trigger_types==('financial_state_ood',)
    assert len(r1.hypothesis_ids)==1
    # Still latched: no second OOD hypothesis.
    assert op.ingest_financial_state(state(20,ood=.95)).hypothesis_ids==()

    restarted=AutonomousResearchLoop(OracleEngine(db))
    op2=OracleOperatingLayer(restarted,trigger_policy=FinancialTriggerPolicy(cooldown_ns=100,ood_enter=.8,ood_exit=.6))
    assert op2.ingest_financial_state(state(30,ood=.92)).hypothesis_ids==()
    # Reset hysteresis, but cooldown still blocks until t>=110.
    op2.ingest_financial_state(state(40,ood=.5))
    assert op2.ingest_financial_state(state(80,ood=.9)).hypothesis_ids==()
    op2.ingest_financial_state(state(120,ood=.5))
    assert len(op2.ingest_financial_state(state(121,ood=.9)).hypothesis_ids)==1


def test_feature_trigger_and_view_projection(tmp_path:Path):
    loop=AutonomousResearchLoop(OracleEngine(tmp_path/'o.db'))
    op=OracleOperatingLayer(loop,trigger_policy=FinancialTriggerPolicy(cooldown_ns=0))
    spec=FeatureTriggerSpec('spread','NQ',abs_delta=2.0)
    assert not op.ingest_financial_state(state(1,feature=1),feature_specs=(spec,)).hypothesis_ids
    result=op.ingest_financial_state(state(2,feature=4),feature_specs=(spec,))
    assert result.trigger_types==('feature_dislocation',)
    views=op.views(2)
    assert views.financial.state_id=='S2'
    assert views.research.hypotheses
    assert any(n['kind']=='hypothesis' for n in views.command_graph.nodes)


def test_thesis_decay_surfaces_retest_and_changes_priority(tmp_path:Path):
    loop=AutonomousResearchLoop(OracleEngine(tmp_path/'o.db'))
    op=OracleOperatingLayer(loop,thesis_policy=ThesisPolicy(half_life_ns=10,retest_age_ns=20,drift_threshold=.2,min_effective_health=.4))
    h=loop.submit_trigger(__import__('oracle.hypothesis_factory',fromlist=['Trigger']).Trigger('x',1,'NQ',1,.9,{}))
    a=ThesisAssessment(h.hypothesis_id,5,.9,.05,1,.9,.9,.9,.05,(),())
    loop.engine.store.add_assessment(a); loop.engine.assessments[h.hypothesis_id]=a
    due=op.retest_required(30)
    assert due and due[0].hypothesis_id==h.hypothesis_id
    mult=op.priority_multipliers(30)
    by_system={loop.task_by_job[jid].system:m for jid,m in mult.items()}
    assert by_system['DAEDALUS']>by_system['ARGUS']


def test_adaptive_ranking_preserves_immutable_jobs(tmp_path:Path):
    loop=AutonomousResearchLoop(OracleEngine(tmp_path/'o.db'))
    h=loop.submit_trigger(__import__('oracle.hypothesis_factory',fromlist=['Trigger']).Trigger('x',1,'NQ',1,.9,{}))
    jobs=list(loop.engine.scheduler._jobs.values())
    first=rank_jobs_adaptive(jobs,{j.job_id:(10.0 if loop.task_by_job[j.job_id].system=='NEXUS' else .1) for j in jobs})[0]
    assert loop.task_by_job[first.job_id].system=='NEXUS'
    # Job specifications are unchanged by the operating overlay.
    assert all(j.status=='QUEUED' for j in jobs)


def test_priority_decisions_are_explainable(tmp_path:Path):
    loop=AutonomousResearchLoop(OracleEngine(tmp_path/'o.db'))
    op=OracleOperatingLayer(loop)
    loop.submit_trigger(__import__('oracle.hypothesis_factory',fromlist=['Trigger']).Trigger('x',1,'NQ',1,.9,{}))
    op.ingest_financial_state(state(2,ood=.9,confidence=.4,health=.4))
    decisions=op.priority_decisions(2)
    assert decisions
    assert all(d.reasons for d in decisions)
    nexus=[d for d in decisions if loop.task_by_job[d.job_id].system=='NEXUS']
    assert nexus and 'LOW_STATE_CONFIDENCE_AUDIT' in nexus[0].reasons


def test_action_board_never_self_authorizes_promotion(tmp_path:Path):
    loop=AutonomousResearchLoop(OracleEngine(tmp_path/'o.db'))
    op=OracleOperatingLayer(loop)
    h=loop.submit_trigger(__import__('oracle.hypothesis_factory',fromlist=['Trigger']).Trigger('x',1,'NQ',1,.9,{}))
    # No assessment means evidence collection, not promotion.
    row=op.action_board(2)[0]
    assert row.action=='COLLECT_EVIDENCE'
    assert not row.requires_external_authority
    a=ThesisAssessment(h.hypothesis_id,3,.95,.0,1,.9,.9,.9,.0,(),())
    loop.engine.store.add_assessment(a); loop.engine.assessments[h.hypothesis_id]=a
    # Even excellent internal research only creates an external review request once testing has begun.
    loop.engine.transition_hypothesis(h.hypothesis_id,'TESTING',occurred_ns=3,reason='TEST')
    row=op.action_board(3)[0]
    assert row.action=='EXTERNAL_PROMOTION_REVIEW'
    assert row.requires_external_authority
