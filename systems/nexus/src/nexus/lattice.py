from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .clock import ClockPolicyRegistry, RepresentationClockRule, ClockPolicyError
from .contracts import BarEvent, StreamManifest


@dataclass(frozen=True, slots=True)
class LatticeStream:
    stream_id: str
    representation_class: str
    timestamp_semantics: str
    cadence_mode: str
    observed_cadence_ns: int | None
    reviewed: bool


class MultiResolutionClockLattice:
    """Native-clock synchronization without inventing a universal bar interval.

    The lattice exposes *visibility boundaries* only.  It never resamples an
    event-driven stream into fictional minute/hour bars.
    """

    def __init__(self, registry: ClockPolicyRegistry | None = None):
        self.registry = registry or ClockPolicyRegistry()
        self._streams: dict[str, tuple[StreamManifest, str]] = {}

    def register(
        self,
        manifest: StreamManifest,
        representation_class: str,
        *,
        rule: RepresentationClockRule | None = None,
    ) -> None:
        if rule is not None:
            if rule.representation_class != representation_class:
                raise ClockPolicyError("rule representation_class does not match registration")
            self.registry.register(rule)
        active = self.registry.get(representation_class)
        if active is None or not active.reviewed:
            raise ClockPolicyError(f"reviewed policy required for {representation_class}")
        old = self._streams.get(manifest.identity.stream_id)
        nxt = (manifest, representation_class)
        if old is not None and old != nxt:
            raise ClockPolicyError("stream clock registration is immutable; version the stream identity")
        self._streams[manifest.identity.stream_id] = nxt

    def describe(self) -> Mapping[str, LatticeStream]:
        out: dict[str, LatticeStream] = {}
        for sid, (manifest, rep) in self._streams.items():
            r = self.registry.get(rep)
            assert r is not None
            out[sid] = LatticeStream(
                stream_id=sid,
                representation_class=rep,
                timestamp_semantics=r.timestamp_semantics,
                cadence_mode=r.cadence_mode,
                observed_cadence_ns=manifest.observed_cadence_ns,
                reviewed=r.reviewed,
            )
        return out

    def visible_ns(self, stream_id: str, source_timestamp_ns: int) -> int:
        try:
            manifest, rep = self._streams[stream_id]
        except KeyError as exc:
            raise ClockPolicyError(f"unregistered stream: {stream_id}") from exc
        rule = self.registry.get(rep)
        assert rule is not None
        return rule.visible_ns(source_timestamp_ns, manifest)

    def native_boundaries(self, events: Iterable[BarEvent], *, streams: set[str] | None = None) -> tuple[int, ...]:
        """Return only observed event visibility boundaries; never synthesize gaps."""
        vals = []
        for e in events:
            if streams is not None and e.stream_id not in streams:
                continue
            if e.stream_id not in self._streams:
                raise ClockPolicyError(f"event uses unregistered stream: {e.stream_id}")
            # If ingestion already supplied verified availability, preserve it.
            vals.append(e.available_ns if e.available_ns is not None else self.visible_ns(e.stream_id, e.event_ns))
        return tuple(sorted(set(vals)))
