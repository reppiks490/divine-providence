import time
from infrastructure_loop import ActionClass, ProposedAction
from topology_governor import (
    BlastRadiusGovernor,
    ComponentTopology,
    MutationLeaseManager,
    TopologyModel,
)


def action(component='api', cls=ActionClass.RESTART, risk=0.10):
    return ProposedAction(component, cls, 'x', {}, 0.1, risk, 0.9, 0.9, 'test').finalize()


def test_external_authority_is_observation_only():
    model = TopologyModel([ComponentTopology('api', authority='sibling:execution')])
    d = BlastRadiusGovernor(model).evaluate(action())
    assert not d.approved
    assert d.reason == 'component authority is external: sibling:execution'


def test_high_impact_unknown_topology_fails_closed():
    d = BlastRadiusGovernor(TopologyModel([])).evaluate(action(component='unknown'))
    assert not d.approved
    assert d.reason == 'unknown topology for high-impact mutation'


def test_low_impact_unknown_topology_can_remain_eligible():
    d = BlastRadiusGovernor(TopologyModel([])).evaluate(action(component='unknown', cls=ActionClass.TUNE))
    assert d.approved


def test_transitive_critical_downstream_blocks_high_impact_action():
    model = TopologyModel([
        ComponentTopology('store'),
        ComponentTopology('worker', depends_on=('store',), critical=True),
        ComponentTopology('executor', depends_on=('worker',), critical=True),
    ])
    d = BlastRadiusGovernor(model).evaluate(action(component='store'))
    assert not d.approved
    assert set(d.impacted_components) == {'store', 'worker', 'executor'}
    assert 'critical downstream' in d.reason


def test_redundancy_budget_blocks_consuming_last_healthy_member():
    model = TopologyModel([
        ComponentTopology('api-a', redundancy_group='api', min_healthy=2),
        ComponentTopology('api-b', redundancy_group='api', min_healthy=2),
        ComponentTopology('api-c', redundancy_group='api', min_healthy=2),
    ])
    health = {'api-a': 0.9, 'api-b': 0.9, 'api-c': 0.1}
    d = BlastRadiusGovernor(model).evaluate(action(component='api-a'), health_scores=health)
    assert not d.approved
    assert d.reason == 'redundancy budget would fall below minimum healthy members'


def test_mutation_lease_conflicts_and_expires():
    leases = MutationLeaseManager()
    assert leases.acquire('one', ('component:api',), ttl_seconds=0.05, now=10.0)
    assert not leases.acquire('two', ('component:api',), ttl_seconds=0.05, now=10.01)
    assert leases.acquire('two', ('component:api',), ttl_seconds=0.05, now=10.06)


def test_failure_domain_scope_prevents_correlated_mutation():
    model = TopologyModel([
        ComponentTopology('a', failure_domain='rack-1'),
        ComponentTopology('b', failure_domain='rack-1'),
    ])
    gov = BlastRadiusGovernor(model)
    da = gov.evaluate(action(component='a'))
    db = gov.evaluate(action(component='b'))
    assert 'failure-domain:rack-1' in da.lease_scopes
    assert 'failure-domain:rack-1' in db.lease_scopes


def test_loop_denies_external_authority_even_for_low_risk_tune(tmp_path):
    import asyncio
    from infrastructure_loop import DemoServiceAdapter, InfrastructureSupervisoryLoop, LoopConfig

    async def _run():
        model = TopologyModel([ComponentTopology('svc', authority='sibling:execution')])
        loop = InfrastructureSupervisoryLoop(
            [DemoServiceAdapter('svc', base_health=0.60)],
            config=LoopConfig(shadow_mode=True, journal_path=str(tmp_path / 'j.jsonl')),
            topology_model=model,
        )
        result = await loop.cycle()
        assert result['candidate_actions'] >= 1
        assert result['approved_actions'] == []
        assert any(d['reason'].startswith('component authority is external') for d in result['topology_decisions'])
    asyncio.run(_run())


def test_loop_lease_blocks_correlated_same_domain_shadow_mutations(tmp_path):
    import asyncio
    from infrastructure_loop import DemoServiceAdapter, InfrastructureSupervisoryLoop, LoopConfig

    async def _run():
        model = TopologyModel([
            ComponentTopology('a', failure_domain='rack-1'),
            ComponentTopology('b', failure_domain='rack-1'),
        ])
        loop = InfrastructureSupervisoryLoop(
            [DemoServiceAdapter('a', base_health=0.60), DemoServiceAdapter('b', base_health=0.60)],
            config=LoopConfig(shadow_mode=True, journal_path=str(tmp_path / 'j.jsonl')),
            topology_model=model,
        )
        result = await loop.cycle()
        approved_components = {a['component'] for a in result['approved_actions']}
        assert len(approved_components) == 1
        assert any(d['reason'] == 'mutation lease conflict' for d in result['topology_decisions'])
    asyncio.run(_run())
