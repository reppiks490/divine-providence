from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence, Tuple

from attribution import AttributionObservation, Sample


@dataclass(frozen=True)
class TelemetryPoint:
    timestamp: float
    score: float
    confidence: float = 1.0


@dataclass(frozen=True)
class MutationEvent:
    timestamp: float
    component: str
    event_id: str
    protected_scopes: Tuple[str, ...] = ()
    intervention_id: str | None = None
    mutation_receipt_hash: str | None = None


@dataclass(frozen=True)
class EvidenceRequest:
    component: str
    action_fingerprint: str
    intervention_ts: float
    pre_start: float
    post_end: float
    intervention_id: str | None = None
    mutation_receipt_hash: str | None = None
    control_component: str | None = None
    protected_scopes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class EvidencePolicy:
    include_intervention_in_event_window: bool = True


class EvidenceProvider(Protocol):
    """Read-only evidence source. It deliberately defines no mutation method."""
    async def telemetry(self, component: str, start: float, end: float) -> Sequence[TelemetryPoint]: ...
    async def mutation_events(self, start: float, end: float) -> Sequence[MutationEvent]: ...


class ReadOnlyEvidenceCollector:
    """Builds attribution observations from explicitly requested evidence only.

    It never chooses a control. Provider failure yields unusable evidence rather
    than raising into the supervisory mutation path.
    """
    def __init__(self, provider: EvidenceProvider, policy: EvidencePolicy = EvidencePolicy()):
        self.provider = provider
        self.policy = policy

    @staticmethod
    def _samples(points: Sequence[TelemetryPoint], *, before: float | None = None, after: float | None = None) -> Tuple[Sample, ...]:
        out=[]
        for p in points:
            if before is not None and not p.timestamp < before:
                continue
            if after is not None and not p.timestamp > after:
                continue
            out.append(Sample(p.timestamp, p.score, p.confidence))
        return tuple(sorted(out, key=lambda x: x.timestamp))

    async def collect(self, req: EvidenceRequest, *, proof_valid: bool = True) -> AttributionObservation:
        try:
            treated = tuple(await self.provider.telemetry(req.component, req.pre_start, req.post_end))
            control = ()
            if req.control_component is not None:
                control = tuple(await self.provider.telemetry(req.control_component, req.pre_start, req.post_end))
            events = tuple(await self.provider.mutation_events(req.pre_start, req.post_end))
        except Exception:
            return AttributionObservation(
                component=req.component, action_fingerprint=req.action_fingerprint,
                intervention_ts=req.intervention_ts, treated_pre=(), treated_post=(),
                control_component=req.control_component, proof_valid=False,
            )

        # Only an event carrying the exact globally unique intervention identity may
        # be recognized as this execution's own mutation. Action fingerprints are
        # content identities and MUST NOT suppress events. Missing/legacy IDs remain
        # conservative contamination evidence.
        overlaps = tuple(
            e for e in events
            if not (req.intervention_id and req.mutation_receipt_hash and e.intervention_id == req.intervention_id and e.mutation_receipt_hash == req.mutation_receipt_hash)
        )
        mutation_ids = tuple(e.event_id for e in overlaps)
        requested_scopes=set(req.protected_scopes)
        scope_events=[]
        for e in overlaps:
            for scope in e.protected_scopes:
                if scope in requested_scopes:
                    scope_events.append(f"{e.event_id}:{scope}")

        return AttributionObservation(
            component=req.component,
            action_fingerprint=req.action_fingerprint,
            intervention_ts=req.intervention_ts,
            treated_pre=self._samples(treated, before=req.intervention_ts),
            treated_post=self._samples(treated, after=req.intervention_ts),
            control_component=req.control_component,
            control_pre=self._samples(control, before=req.intervention_ts) if req.control_component else (),
            control_post=self._samples(control, after=req.intervention_ts) if req.control_component else (),
            mutation_events=mutation_ids,
            protected_scope_events=tuple(scope_events),
            proof_valid=proof_valid,
        )


class InMemoryEvidenceProvider:
    """Deterministic read-only provider for tests, replay and offline simulation."""
    def __init__(self, *, telemetry: Mapping[str, Sequence[TelemetryPoint]] | None = None,
                 mutations: Sequence[MutationEvent] = ()):
        self._telemetry = {k: tuple(v) for k,v in (telemetry or {}).items()}
        self._mutations = tuple(mutations)

    async def telemetry(self, component: str, start: float, end: float) -> Sequence[TelemetryPoint]:
        return tuple(p for p in self._telemetry.get(component, ()) if start <= p.timestamp <= end)

    async def mutation_events(self, start: float, end: float) -> Sequence[MutationEvent]:
        return tuple(e for e in self._mutations if start <= e.timestamp <= end)
