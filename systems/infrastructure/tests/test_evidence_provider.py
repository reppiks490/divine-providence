import asyncio
from evidence_provider import (
    EvidencePolicy, EvidenceRequest, InMemoryEvidenceProvider,
    ReadOnlyEvidenceCollector, TelemetryPoint, MutationEvent,
)


def run(coro): return asyncio.run(coro)

def p(t, score, conf=.9): return TelemetryPoint(t, score, conf)


def test_collector_builds_explicit_control_observation_only_when_bound():
    provider=InMemoryEvidenceProvider(
        telemetry={
            'svc': (p(1,.4),p(2,.4),p(11,.7),p(12,.7)),
            'ctrl': (p(1,.4),p(2,.4),p(11,.41),p(12,.41)),
        }
    )
    req=EvidenceRequest('svc','fp',10,pre_start=0,post_end=13,control_component='ctrl')
    obs=run(ReadOnlyEvidenceCollector(provider).collect(req))
    assert obs.control_component == 'ctrl'
    assert len(obs.treated_pre)==2 and len(obs.treated_post)==2
    assert len(obs.control_pre)==2 and len(obs.control_post)==2


def test_collector_never_auto_selects_control():
    provider=InMemoryEvidenceProvider(telemetry={'svc':(p(1,.4),p(2,.4),p(11,.7),p(12,.7)), 'tempting':(p(1,.4),p(2,.4),p(11,.4),p(12,.4))})
    req=EvidenceRequest('svc','fp',10,0,13)
    obs=run(ReadOnlyEvidenceCollector(provider).collect(req))
    assert obs.control_component is None and obs.control_pre == () and obs.control_post == ()


def test_overlapping_mutation_and_scope_events_are_carried_into_observation():
    provider=InMemoryEvidenceProvider(
        telemetry={'svc':(p(1,.4),p(2,.4),p(11,.7),p(12,.7))},
        mutations=(MutationEvent(10.5,'other','m-1',('fd:a',)),)
    )
    req=EvidenceRequest('svc','fp',10,0,13,protected_scopes=('fd:a',))
    obs=run(ReadOnlyEvidenceCollector(provider).collect(req))
    assert obs.mutation_events == ('m-1',)
    assert obs.protected_scope_events == ('m-1:fd:a',)


def test_provider_exception_fails_closed_to_empty_evidence_not_raise():
    class Broken:
        async def telemetry(self,*a,**k): raise RuntimeError('down')
        async def mutation_events(self,*a,**k): raise RuntimeError('down')
    obs=run(ReadOnlyEvidenceCollector(Broken()).collect(EvidenceRequest('svc','fp',10,0,13)))
    assert obs.proof_valid is False
    assert obs.treated_pre == () and obs.treated_post == ()


def test_out_of_window_points_are_excluded():
    provider=InMemoryEvidenceProvider(telemetry={'svc':(p(-1,.1),p(1,.4),p(2,.4),p(11,.7),p(12,.7),p(20,.9))})
    obs=run(ReadOnlyEvidenceCollector(provider).collect(EvidenceRequest('svc','fp',10,0,13)))
    assert [x.timestamp for x in obs.treated_pre] == [1,2]
    assert [x.timestamp for x in obs.treated_post] == [11,12]


def test_read_only_provider_exposes_no_mutation_method():
    assert not hasattr(ReadOnlyEvidenceCollector, 'execute')
    assert not hasattr(ReadOnlyEvidenceCollector, 'mutate')

def test_action_fingerprint_does_not_suppress_same_named_mutation_event():
    provider=InMemoryEvidenceProvider(
        telemetry={'svc':(p(1,.4),p(2,.4),p(11,.7),p(12,.7))},
        mutations=(MutationEvent(10.5,'svc','fp',()),)
    )
    obs=run(ReadOnlyEvidenceCollector(provider).collect(EvidenceRequest('svc','fp',10,0,13)))
    assert obs.mutation_events == ('fp',)
