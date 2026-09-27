import asyncio
from evidence_provider import (
    EvidenceRequest, InMemoryEvidenceProvider, MutationEvent,
    ReadOnlyEvidenceCollector, TelemetryPoint,
)


def _telemetry():
    return {"svc": (
        TelemetryPoint(1,.2,.9), TelemetryPoint(2,.2,.9),
        TelemetryPoint(4,.6,.9), TelemetryPoint(5,.6,.9),
    )}


def _req(intervention_id="iv-own"):
    return EvidenceRequest(component="svc", action_fingerprint="same-action", intervention_ts=3,
                           intervention_id=intervention_id, pre_start=0, post_end=6)


def test_exact_intervention_identity_excludes_only_own_mutation_event():
    async def run():
        p=InMemoryEvidenceProvider(telemetry=_telemetry(), mutations=(
            MutationEvent(3,"svc","evt-own",(),"iv-own"),
            MutationEvent(3,"svc","evt-other",(),"iv-other"),
        ))
        obs=await ReadOnlyEvidenceCollector(p).collect(_req())
        assert obs.mutation_events == ("evt-own","evt-other")
    asyncio.run(run())


def test_same_action_fingerprint_never_counts_as_intervention_identity():
    async def run():
        p=InMemoryEvidenceProvider(telemetry=_telemetry(), mutations=(
            MutationEvent(3,"svc","same-action",()),
        ))
        obs=await ReadOnlyEvidenceCollector(p).collect(_req())
        assert obs.mutation_events == ("same-action",)
    asyncio.run(run())


def test_missing_intervention_identity_filters_nothing():
    async def run():
        p=InMemoryEvidenceProvider(telemetry=_telemetry(), mutations=(
            MutationEvent(3,"svc","evt-own",(),"iv-own"),
        ))
        obs=await ReadOnlyEvidenceCollector(p).collect(_req(None))
        assert obs.mutation_events == ("evt-own",)
    asyncio.run(run())


def test_repeated_identical_actions_can_be_disambiguated_by_intervention_identity():
    async def run():
        p=InMemoryEvidenceProvider(telemetry=_telemetry(), mutations=(
            MutationEvent(3,"svc","evt-a",(),"iv-a"),
            MutationEvent(3,"svc","evt-b",(),"iv-b"),
        ))
        c=ReadOnlyEvidenceCollector(p)
        a=await c.collect(_req("iv-a")); b=await c.collect(_req("iv-b"))
        assert a.mutation_events == ("evt-a","evt-b")
        assert b.mutation_events == ("evt-a","evt-b")
    asyncio.run(run())
