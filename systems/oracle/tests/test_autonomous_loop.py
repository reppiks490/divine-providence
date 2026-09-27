from pathlib import Path
import pytest
from oracle.automation import AutonomousResearchLoop
from oracle.budget import ResearchBudget
from oracle.contracts import EvidenceRecord, HypothesisStatus
from oracle.engine import OracleEngine
from oracle.hypothesis_factory import Trigger
from oracle.journal import LoopJournal
from oracle.outbox import ResearchOutbox
from oracle.runtime import RetryPolicy


def trigger(t: int = 100, magnitude: float = .8):
    return Trigger("topology_break", t, "NQ", magnitude, .9, {"entropy": .2}, ("a" * 64,))


def test_autonomous_plan_creates_bounded_cross_system_research(tmp_path: Path):
    loop = AutonomousResearchLoop(OracleEngine(tmp_path / "oracle.db"))
    h = loop.submit_trigger(trigger(), sensors=("NVDA", "VIX"))
    plan = loop.plans[h.hypothesis_id]
    assert len(plan.tasks) == 6
    assert {t.system for t in plan.tasks} == {"NEXUS", "AION", "ARGUS", "ATHENA", "DAEDALUS"}
    assert {x.purpose for x in plan.attack_suite} >= {"sensor_ablation", "leakage_attack", "null_attack", "cost_stress", "threshold_stress"}
    assert loop.engine.status[h.hypothesis_id] is HypothesisStatus.QUEUED
    qid = loop.engine.question_by_hypothesis[h.hypothesis_id]
    assert set(loop.engine.exchange.questions[qid].requested_kinds) == set(plan.required_evidence_kinds)


def test_structural_dedup_prevents_runaway_research(tmp_path: Path):
    loop = AutonomousResearchLoop(OracleEngine(tmp_path / "oracle.db"), dedup_cooldown_ns=1_000)
    a = loop.submit_trigger(trigger(100, .8))
    jobs = len(loop.engine.scheduler._jobs)
    b = loop.submit_trigger(trigger(101, .95))
    assert b.hypothesis_id == a.hypothesis_id
    assert len(loop.engine.scheduler._jobs) == jobs


def test_durable_outbox_persists_before_sibling_send(tmp_path: Path):
    db = tmp_path / "oracle.db"
    loop = AutonomousResearchLoop(OracleEngine(db))
    loop.submit_trigger(trigger())
    batch = loop.dispatch(101, max_requests=1)
    assert len(batch.requests) == 1
    packet = loop.outbox.pending()[0]
    assert packet.job_id == batch.requests[0].job_id
    reloaded = ResearchOutbox(db)
    assert [p.packet_id for p in reloaded.pending()] == [packet.packet_id]
    assert reloaded.dispatches[packet.packet_id][0].dispatched_ns == 101


def test_evidence_fan_in_completes_job_and_acks_packet_idempotently(tmp_path: Path):
    loop = AutonomousResearchLoop(OracleEngine(tmp_path / "oracle.db"))
    loop.submit_trigger(trigger())
    req = loop.dispatch(101, max_requests=1).requests[0]
    task = loop.task_by_job[req.job_id]
    e = EvidenceRecord("E1", req.hypothesis_id, req.target_system, task.evidence_kind, 102, {"ok": True}, "b" * 64, .8, True)
    got = loop.ingest_evidence(req.job_id, e, claim="evidence received", received_ns=103)
    assert got.immutable_hash == e.immutable_hash
    assert req.job_id in loop.runtime.completed
    assert all(loop.outbox.is_acked(p.packet_id) for p in loop.outbox.packets_for_job(req.job_id))
    # at-least-once sibling delivery is safe when the immutable evidence is identical
    assert loop.ingest_evidence(req.job_id, e, claim="duplicate", received_ns=104).immutable_hash == e.immutable_hash


def test_evidence_kind_and_source_are_enforced(tmp_path: Path):
    loop = AutonomousResearchLoop(OracleEngine(tmp_path / "oracle.db"))
    loop.submit_trigger(trigger())
    req = loop.dispatch(101, max_requests=1).requests[0]
    wrong = EvidenceRecord("E1", req.hypothesis_id, req.target_system, "wrong_kind", 102, {}, "b" * 64, .5, True)
    with pytest.raises(ValueError, match="evidence kind mismatch"):
        loop.ingest_evidence(req.job_id, wrong, claim="bad", received_ns=103)
    wrong_source = EvidenceRecord("E2", req.hypothesis_id, "AION" if req.target_system != "AION" else "NEXUS", loop.task_by_job[req.job_id].evidence_kind, 102, {}, "c" * 64, .5, True)
    with pytest.raises(ValueError, match="source"):
        loop.ingest_evidence(req.job_id, wrong_source, claim="bad", received_ns=103)


def test_retry_is_bounded_and_creates_new_idempotent_packet(tmp_path: Path):
    loop = AutonomousResearchLoop(OracleEngine(tmp_path / "oracle.db"), retry_policy=RetryPolicy(max_attempts=2, base_backoff_ns=10))
    loop.submit_trigger(trigger())
    first = loop.dispatch(101, max_requests=1).requests[0]
    # isolate retry behavior from the other planned jobs
    for jid in loop.engine.scheduler._jobs:
        if jid != first.job_id:
            loop.runtime.dead_letter[jid] = "TEST_ISOLATION"
    assert loop.fail_job(first.job_id, failed_ns=102, error_code="TRANSIENT") == "RETRY_SCHEDULED"
    assert not loop.dispatch(111, max_requests=1).requests
    second = loop.dispatch(112, max_requests=1).requests[0]
    assert second.job_id == first.job_id and second.request_id != first.request_id
    assert loop.fail_job(second.job_id, failed_ns=113, error_code="TRANSIENT") == "DEAD_LETTER"
    assert first.job_id in loop.runtime.dead_letter


def test_compute_budget_blocks_runaway_dispatch(tmp_path: Path):
    loop = AutonomousResearchLoop(OracleEngine(tmp_path / "oracle.db"), budget=ResearchBudget(.5))
    loop.submit_trigger(trigger())
    batch = loop.dispatch(101)
    assert not batch.requests
    assert batch.blocked and all(reason == "COMPUTE_BUDGET_EXHAUSTED" for _, reason in batch.blocked)


def test_command_journal_is_durable_and_deterministically_replayable(tmp_path: Path):
    p = tmp_path / "loop.jsonl"
    loop = AutonomousResearchLoop(OracleEngine(tmp_path / "a.db"), retry_policy=RetryPolicy(max_attempts=2, base_backoff_ns=10), journal_path=p)
    loop.submit_trigger(trigger(), sensors=("VIX",))
    req = loop.dispatch(101, max_requests=1).requests[0]
    loop.fail_job(req.job_id, failed_ns=102, error_code="TRANSIENT")
    assert loop.journal.verify() and p.exists()
    loaded = LoopJournal(p)
    assert loaded.verify() and loaded.head_hash == loop.journal.head_hash
    other = AutonomousResearchLoop(OracleEngine(tmp_path / "b.db"), retry_policy=RetryPolicy(max_attempts=2, base_backoff_ns=10))
    hashes = loop.replay_into(other)
    assert len(hashes) == len(loop.journal.records())
    assert other.engine.ledger.verify()


def test_failed_packet_is_terminal_and_retry_supersedes_it(tmp_path: Path):
    loop = AutonomousResearchLoop(OracleEngine(tmp_path / "oracle.db"), retry_policy=RetryPolicy(max_attempts=2, base_backoff_ns=10))
    loop.submit_trigger(trigger())
    first = loop.dispatch(101, max_requests=1).requests[0]
    first_packet = loop.outbox.packets_for_job(first.job_id)[-1]
    for jid in loop.engine.scheduler._jobs:
        if jid != first.job_id:
            loop.runtime.dead_letter[jid] = "TEST_ISOLATION"
    loop.fail_job(first.job_id, failed_ns=102, error_code="TRANSIENT")
    assert first_packet.packet_id in loop.outbox.failed
    assert first_packet.packet_id not in {p.packet_id for p in loop.outbox.pending()}
    second = loop.dispatch(112, max_requests=1).requests[0]
    second_packet = loop.outbox.packets_for_job(second.job_id)[-1]
    assert second_packet.packet_id != first_packet.packet_id
    assert second_packet.packet_id in {p.packet_id for p in loop.outbox.pending()}


def test_required_evidence_completion_auto_assesses_without_optional_argus(tmp_path: Path):
    loop = AutonomousResearchLoop(OracleEngine(tmp_path / "oracle.db"))
    h = loop.submit_trigger(trigger())
    batch = loop.dispatch(101)
    assert len(batch.requests) == 6
    # Complete every required task but deliberately omit optional ARGUS.
    now = 110
    for req in batch.requests:
        task = loop.task_by_job[req.job_id]
        if not task.required:
            continue
        payload = {"ok": True}
        if req.target_system == "DAEDALUS": payload["robustness_score"] = .8
        if req.target_system == "ATHENA": payload.update({"regime_fit": .7, "ood_risk": .2})
        e = EvidenceRecord(f"ev-{req.job_id}", h.hypothesis_id, req.target_system, task.evidence_kind, now, payload, "d" * 64, .8, True)
        loop.ingest_evidence(req.job_id, e, claim="required evidence", received_ns=now)
        now += 1
    a = loop.engine.assessments[h.hypothesis_id]
    assert a.evidence_coverage == 1.0
    assert a.robustness_score == .8 and a.regime_fit == .7 and a.ood_risk == .2
    assert loop.engine.status[h.hypothesis_id] is HypothesisStatus.TESTING


def test_process_restart_recovers_runtime_budget_dedup_and_outbox(tmp_path: Path):
    journal=tmp_path/'loop.jsonl'; db=tmp_path/'oracle.db'
    policy=RetryPolicy(max_attempts=2,base_backoff_ns=10)
    first=AutonomousResearchLoop(OracleEngine(db),retry_policy=policy,journal_path=journal)
    h=first.submit_trigger(trigger(),sensors=('VIX',))
    req=first.dispatch(101,max_requests=1).requests[0]
    for jid in first.engine.scheduler._jobs:
        if jid!=req.job_id: first.runtime.dead_letter[jid]='TEST_ISOLATION'
    first.fail_job(req.job_id,failed_ns=102,error_code='TRANSIENT')
    consumed=first.budget.consumed_compute
    head=first.journal.head_hash

    recovered=AutonomousResearchLoop.recover_from_journal(OracleEngine(db),journal,retry_policy=policy)
    assert recovered.journal.head_hash==head
    assert recovered.budget.consumed_compute==consumed
    assert recovered.runtime.next_eligible_ns[req.job_id]==112
    assert set(recovered.outbox.packets)==set(first.outbox.packets)
    # dedup state was rebuilt by replay rather than guessed from the database
    again=recovered.submit_trigger(trigger(103,.95),_record=False)
    assert again.hypothesis_id==h.hypothesis_id


def test_external_promotion_evidence_advances_research_lifecycle_but_not_execution(tmp_path: Path):
    from oracle.contracts import PromotionEvidence
    loop=AutonomousResearchLoop(OracleEngine(tmp_path/'oracle.db'))
    h=loop.submit_trigger(trigger())
    loop.dispatch(101,max_requests=1)
    evidence=PromotionEvidence(True,True,True,True,False,.2,())
    transitions,reasons=loop.apply_promotion_evidence(h.hypothesis_id,evidence,occurred_ns=200,evidence_ids=('proof',))
    assert not reasons
    assert [t.to_status for t in transitions]==['VALIDATED','STRESS_TESTED','SHADOW','APPROVED_FEATURE']
    assert loop.engine.status[h.hypothesis_id] is HypothesisStatus.APPROVED_FEATURE
    assert loop.engine.hypotheses[h.hypothesis_id].production_authorized is False


def test_promotion_stops_at_first_missing_external_gate(tmp_path: Path):
    from oracle.contracts import PromotionEvidence
    loop=AutonomousResearchLoop(OracleEngine(tmp_path/'oracle.db'))
    h=loop.submit_trigger(trigger()); loop.dispatch(101,max_requests=1)
    transitions,reasons=loop.apply_promotion_evidence(h.hypothesis_id,PromotionEvidence(True,True,False,False,False,.2,()),occurred_ns=200)
    assert [t.to_status for t in transitions]==['VALIDATED']
    assert 'STRESS_NOT_PASSED' in reasons
    assert loop.engine.status[h.hypothesis_id] is HypothesisStatus.VALIDATED
