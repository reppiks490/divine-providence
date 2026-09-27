
import asyncio
from infrastructure_loop import (
    DemoServiceAdapter,
    InfrastructureSupervisoryLoop,
    LoopConfig,
)

def test_shadow_cycle():
    async def _run():
        loop = InfrastructureSupervisoryLoop(
            [DemoServiceAdapter("svc", base_health=0.60)],
            config=LoopConfig(shadow_mode=True, cycle_seconds=0.01),
        )
        result = await loop.cycle()
        assert result["shadow_mode"] is True
        assert result["reports"]
        assert "approved_actions" in result

    asyncio.run(_run())


def test_observer_failure_never_becomes_mutation_evidence():
    from infrastructure_loop import HealthReport, Planner, OutcomeMemory

    report = HealthReport(
        component="broken-observer",
        score=0.10,
        confidence=0.99,
        symptoms=["observer_error:TimeoutError"],
    )
    actions = Planner(OutcomeMemory()).propose([report], [])
    assert actions == []


def test_low_confidence_health_does_not_get_promoted_by_planner():
    from infrastructure_loop import HealthReport, Planner, OutcomeMemory, ActionGuard, GuardPolicy

    report = HealthReport(
        component="uncertain-service",
        score=0.20,
        confidence=0.20,
        symptoms=["weak_signal"],
    )
    actions = Planner(OutcomeMemory()).propose([report], [])
    assert actions, "planner may propose, but guard must reject uncertain evidence"
    guard = ActionGuard(GuardPolicy(min_confidence=0.55, cooldown_seconds=0))
    assert all(guard.approve(a)[0] is False for a in actions)


def test_collector_concurrency_is_bounded():
    import asyncio
    from infrastructure_loop import HealthReport, Signal

    class CountingAdapter:
        active = 0
        peak = 0

        def __init__(self, name):
            self.name = name

        async def collect_signals(self):
            CountingAdapter.active += 1
            CountingAdapter.peak = max(CountingAdapter.peak, CountingAdapter.active)
            await asyncio.sleep(0.02)
            CountingAdapter.active -= 1
            return [Signal(self.name, "x", 1.0)]

        async def health(self):
            return HealthReport(self.name, 1.0, 1.0)

        async def snapshot(self): return {}
        async def execute(self, action): return True, "ok"
        async def rollback(self, snapshot, action): return True, "ok"

    async def _run():
        CountingAdapter.active = 0
        CountingAdapter.peak = 0
        loop = InfrastructureSupervisoryLoop(
            [CountingAdapter(f"svc-{i}") for i in range(8)],
            config=LoopConfig(shadow_mode=True, max_concurrent_collectors=2),
        )
        await loop.cycle()
        assert CountingAdapter.peak <= 2

    asyncio.run(_run())


def test_outcome_memory_cannot_raise_telemetry_confidence():
    from infrastructure_loop import (
        ActionGuard,
        ActionResult,
        GuardPolicy,
        HealthReport,
        OutcomeMemory,
        Planner,
    )

    memory = OutcomeMemory(window=200)
    report = HealthReport(
        component="svc",
        score=0.20,
        confidence=0.20,
        symptoms=["degraded"],
    )
    planner = Planner(memory)
    seed_action = planner.propose([report], [])[0]

    for _ in range(30):
        memory.update(
            ActionResult(
                action=seed_action,
                success=True,
                before_score=0.20,
                after_score=0.30,
                latency_ms=1.0,
            )
        )

    learned_action = planner.propose([report], [])[0]
    assert learned_action.confidence == report.confidence

    guard = ActionGuard(GuardPolicy(min_confidence=0.55, cooldown_seconds=0))
    approved, reason = guard.approve(learned_action)
    assert approved is False
    assert reason == "confidence below policy floor"


def _proposed_action(*, action_class, risk=0.10, confidence=0.90, reversibility=0.90):
    from infrastructure_loop import ProposedAction

    return ProposedAction(
        component="svc",
        action_class=action_class,
        name="test_action",
        payload={},
        expected_gain=0.10,
        estimated_risk=risk,
        reversibility=reversibility,
        confidence=confidence,
        reason="test",
    ).finalize()


def test_guard_denies_action_above_canary_threshold_until_canary_execution_exists():
    from infrastructure_loop import ActionClass, ActionGuard, GuardPolicy

    guard = ActionGuard(
        GuardPolicy(
            max_action_risk=0.35,
            canary_required_above_risk=0.18,
            cooldown_seconds=0,
        )
    )
    action = _proposed_action(action_class=ActionClass.RESTART, risk=0.24)

    approved, reason = guard.approve(action, health_score=0.50)
    assert approved is False
    assert reason == "canary required above risk threshold; canary execution unavailable"


def test_guard_denies_high_impact_mutation_below_critical_health_floor():
    from infrastructure_loop import ActionClass, ActionGuard, GuardPolicy

    guard = ActionGuard(
        GuardPolicy(
            critical_health_floor=0.25,
            canary_required_above_risk=1.0,
            cooldown_seconds=0,
        )
    )
    action = _proposed_action(action_class=ActionClass.REPAIR, risk=0.10)

    approved, reason = guard.approve(action, health_score=0.20)
    assert approved is False
    assert reason == "critical health floor: high-impact autonomous mutation denied"


def test_guard_allows_low_impact_reversible_tune_below_critical_health_floor():
    from infrastructure_loop import ActionClass, ActionGuard, GuardPolicy

    guard = ActionGuard(
        GuardPolicy(
            critical_health_floor=0.25,
            canary_required_above_risk=1.0,
            cooldown_seconds=0,
        )
    )
    action = _proposed_action(action_class=ActionClass.TUNE, risk=0.08)

    approved, reason = guard.approve(action, health_score=0.20)
    assert approved is True
    assert reason == "approved"


def test_guard_requires_health_context_for_high_impact_autonomous_mutation():
    from infrastructure_loop import ActionClass, ActionGuard, GuardPolicy

    guard = ActionGuard(
        GuardPolicy(
            canary_required_above_risk=1.0,
            cooldown_seconds=0,
        )
    )
    action = _proposed_action(action_class=ActionClass.REPAIR, risk=0.10)

    approved, reason = guard.approve(action)
    assert approved is False
    assert reason == "health context required for high-impact autonomous mutation"
