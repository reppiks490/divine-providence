import asyncio

from infrastructure_loop import (
    ActionClass, ActionGuard, GuardPolicy, HealthReport, ProposedAction,
    VerificationPolicy, InfrastructureSupervisoryLoop, LoopConfig,
)
from canary_executor import StagedCanaryExecutor, CanaryStatus


def action(risk=0.24):
    return ProposedAction(
        component='svc', action_class=ActionClass.RESTART, name='restart', payload={},
        expected_gain=.2, estimated_risk=risk, reversibility=.9, confidence=.9, reason='test'
    ).finalize()


def test_guard_only_allows_above_threshold_when_genuine_canary_is_available():
    guard = ActionGuard(GuardPolicy(canary_required_above_risk=.18, cooldown_seconds=0))
    a = action()
    assert guard.approve(a, health_score=.5, canary_available=False)[0] is False
    assert guard.approve(a, health_score=.5, canary_available=True) == (True, 'approved via staged canary requirement')


class CanaryAdapter:
    name = 'svc'
    def __init__(self, after=.65):
        self.score = .5
        self.after = after
        self.events = []
    async def collect_signals(self): return []
    async def health(self): return HealthReport(self.name, self.score, .95)
    async def snapshot(self): return {'score': self.score}
    async def execute(self, action): raise AssertionError('full execute must not precede canary promotion')
    async def rollback(self, snapshot, action): self.score=snapshot['score']; self.events.append('rollback'); return True,'ok'
    async def stage_canary(self, action, snapshot): self.events.append('stage'); self.score=self.after; return True, {'id':'c1'}, 'staged'
    async def promote_canary(self, token, action): self.events.append('promote'); return True, 'promoted'
    async def abort_canary(self, token, snapshot, action): self.events.append('abort'); self.score=snapshot['score']; return True, 'aborted'


def test_staged_canary_promotes_only_after_independent_health_verification():
    async def run():
        adapter=CanaryAdapter(after=.65)
        ex=StagedCanaryExecutor(VerificationPolicy(settle_seconds=0, min_improvement=-.015, rollback_below_score=.30))
        result=await ex.execute(adapter, action(), HealthReport('svc', .5, .95), cycle_id=7)
        assert result.status is CanaryStatus.PROMOTED
        assert adapter.events == ['stage','promote']
        assert result.proof.proof_hash
        assert result.proof.cycle_id == 7
        assert result.proof.before_score == .5 and result.proof.observed_score == .65
    asyncio.run(run())


def test_staged_canary_aborts_on_regression_and_never_promotes():
    async def run():
        adapter=CanaryAdapter(after=.20)
        ex=StagedCanaryExecutor(VerificationPolicy(settle_seconds=0, min_improvement=-.015, rollback_below_score=.30))
        result=await ex.execute(adapter, action(), HealthReport('svc', .5, .95), cycle_id=8)
        assert result.status is CanaryStatus.ABORTED
        assert adapter.events == ['stage','abort']
        assert result.proof.promotion_authorized is False
    asyncio.run(run())


def test_loop_does_not_treat_plain_adapter_as_canary_capable():
    class Plain(CanaryAdapter):
        stage_canary = None
        promote_canary = None
        abort_canary = None
    loop=InfrastructureSupervisoryLoop([Plain()], config=LoopConfig(shadow_mode=True), canary_executor=StagedCanaryExecutor(VerificationPolicy(settle_seconds=0)))
    assert loop._canary_available('svc') is False

def test_live_loop_routes_above_threshold_action_through_canary_and_journals_proof(tmp_path):
    async def run():
        class Live(CanaryAdapter):
            def __init__(self):
                super().__init__(after=.65)
                self.score=.30
            async def execute(self, action):
                self.events.append('execute:'+action.name)
                return True, 'ok'

        adapter=Live()
        ex=StagedCanaryExecutor(VerificationPolicy(settle_seconds=0, min_improvement=-.015, rollback_below_score=.25))
        loop=InfrastructureSupervisoryLoop(
            [adapter],
            config=LoopConfig(shadow_mode=False, journal_path=str(tmp_path/'journal.jsonl')),
            guard_policy=GuardPolicy(cooldown_seconds=0, max_mutations_per_cycle=3, critical_health_floor=.25),
            verification_policy=VerificationPolicy(settle_seconds=0, rollback_below_score=.25),
            canary_executor=ex,
        )
        summary=await loop.cycle()
        assert 'stage' in adapter.events and 'promote' in adapter.events
        restart=[r for r in summary['executed_results'] if r['action']['name']=='graceful_restart'][0]
        assert restart['success'] is True
        journal=(tmp_path/'journal.jsonl').read_text()
        assert '"type": "canary_proof"' in journal
        assert '"promotion_authorized": true' in journal
    asyncio.run(run())

def test_canary_verification_exception_aborts_instead_of_leaving_stage_live():
    async def run():
        class Broken(CanaryAdapter):
            async def health(self):
                if 'stage' in self.events:
                    raise RuntimeError('telemetry lost')
                return HealthReport(self.name, self.score, .95)
        adapter=Broken(after=.65)
        ex=StagedCanaryExecutor(VerificationPolicy(settle_seconds=0))
        result=await ex.execute(adapter, action(), HealthReport('svc', .5, .95), cycle_id=9)
        assert result.status is CanaryStatus.ABORTED
        assert adapter.events == ['stage','abort']
        assert result.proof.promotion_authorized is False
        assert 'verification exception' in result.message
    asyncio.run(run())


def test_canary_proof_detects_tampering():
    import dataclasses
    from canary_executor import CanaryProof
    proof = CanaryProof(
        cycle_id=1, component='svc', action_fingerprint='abc', staged_at=1.0,
        verified_at=2.0, before_score=.4, observed_score=.6,
        verification_reason='ok', promotion_authorized=True, status='promoted'
    ).finalized()
    assert proof.verify_integrity() is True
    assert dataclasses.replace(proof, observed_score=.1).verify_integrity() is False


def test_outcome_memory_does_not_credit_uncorroborated_success():
    from infrastructure_loop import OutcomeMemory, ActionResult
    a = action(risk=.1)
    m = OutcomeMemory()
    m.update(ActionResult(a, True, .4, .8, 1.0, causal_eligible=False))
    assert m.prior(a) == (0.0, 0.0)


def test_outcome_memory_credits_verified_causal_success():
    from infrastructure_loop import OutcomeMemory, ActionResult
    a = action(risk=.1)
    m = OutcomeMemory()
    m.update(ActionResult(a, True, .4, .8, 1.0, causal_eligible=True, evidence_hash='proof', attribution_eligible=True, attribution_hash='attr'))
    mean, conf = m.prior(a)
    assert mean == .4
    assert conf > 0


def test_promoted_canary_marks_result_causal_only_for_positive_verified_delta(tmp_path):
    async def run():
        class Live(CanaryAdapter):
            def __init__(self):
                super().__init__(after=.65)
                self.score=.30
        adapter=Live()
        ex=StagedCanaryExecutor(VerificationPolicy(settle_seconds=0, min_improvement=-.015, rollback_below_score=.25))
        loop=InfrastructureSupervisoryLoop(
            [adapter], config=LoopConfig(shadow_mode=False, journal_path=str(tmp_path/'journal.jsonl')),
            guard_policy=GuardPolicy(cooldown_seconds=0, max_mutations_per_cycle=3, critical_health_floor=.25),
            verification_policy=VerificationPolicy(settle_seconds=0, rollback_below_score=.25), canary_executor=ex,
        )
        summary=await loop.cycle()
        restart=[r for r in summary['executed_results'] if r['action']['name']=='graceful_restart'][0]
        assert restart['causal_eligible'] is True
        assert restart['evidence_hash']
    asyncio.run(run())


def test_promoted_canary_with_nonpositive_delta_is_not_causal_credit(tmp_path):
    async def run():
        class Flat(CanaryAdapter):
            def __init__(self):
                super().__init__(after=.50)
                self.score=.50
        adapter=Flat()
        ex=StagedCanaryExecutor(VerificationPolicy(settle_seconds=0, min_improvement=-.015, rollback_below_score=.25))
        result=await ex.execute(adapter, action(), HealthReport('svc', .50, .95), cycle_id=10)
        assert result.status is CanaryStatus.PROMOTED
        # Protocol promotion and causal-learning eligibility are intentionally distinct.
        from infrastructure_loop import ActionResult, OutcomeMemory
        r=ActionResult(action(), True, .50, result.proof.observed_score, 0.0,
                       causal_eligible=(result.proof.verify_integrity() and result.proof.observed_score-result.proof.before_score > 0),
                       evidence_hash=result.proof.proof_hash if result.proof.observed_score-result.proof.before_score > 0 else '')
        m=OutcomeMemory(); m.update(r)
        assert r.causal_eligible is False
        assert m.prior(r.action) == (0.0, 0.0)
    asyncio.run(run())
