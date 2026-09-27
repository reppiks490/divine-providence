from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from .contracts import QualityFlag
from .ingest import BarClockPolicy


class RepresentationKind(str, Enum):
    TIME_BAR = "time_bar"
    EVENT_BAR = "event_bar"          # tick / volume / range / renko-like completion
    DERIVED_TIME_BAR = "derived_time_bar"  # e.g. Heikin-Ashi over time bars
    DERIVED_EVENT_BAR = "derived_event_bar"
    UNKNOWN = "unknown"


class TimestampSemantics(str, Enum):
    BAR_OPEN = "bar_open"
    BAR_CLOSE = "bar_close"
    EVENT_COMPLETION = "event_completion"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RepresentationPolicy:
    representation_id: str
    kind: RepresentationKind
    timestamp_semantics: TimestampSemantics
    fixed_interval_ns: int | None = None
    availability_delay_ns: int = 0
    reviewed: bool = False

    def __post_init__(self):
        if self.availability_delay_ns < 0:
            raise ValueError("availability delay cannot be negative")
        if self.timestamp_semantics == TimestampSemantics.BAR_OPEN:
            if self.kind not in (RepresentationKind.TIME_BAR, RepresentationKind.DERIVED_TIME_BAR):
                raise ValueError("open-stamped fixed completion only applies to time bars")
            if not self.fixed_interval_ns or self.fixed_interval_ns <= 0:
                raise ValueError("open-stamped time bars require fixed_interval_ns")
        if self.kind in (RepresentationKind.EVENT_BAR, RepresentationKind.DERIVED_EVENT_BAR):
            if self.timestamp_semantics == TimestampSemantics.BAR_OPEN:
                raise ValueError("event bars cannot infer completion by adding a fixed cadence")

    @property
    def is_derived(self) -> bool:
        return self.kind in (RepresentationKind.DERIVED_TIME_BAR, RepresentationKind.DERIVED_EVENT_BAR)

    @property
    def is_event_driven(self) -> bool:
        return self.kind in (RepresentationKind.EVENT_BAR, RepresentationKind.DERIVED_EVENT_BAR)

    def to_clock_policy(self) -> BarClockPolicy:
        flags=[]
        if self.is_derived:
            flags.append(QualityFlag.DERIVED_REPRESENTATION.value)
        if self.is_event_driven:
            flags.append(QualityFlag.EVENT_DRIVEN_REPRESENTATION.value)
        if self.reviewed:
            flags.append(QualityFlag.CLOCK_POLICY_REVIEWED.value)

        if self.timestamp_semantics == TimestampSemantics.BAR_OPEN:
            return BarClockPolicy(
                source_stamp="open", cadence_ns=self.fixed_interval_ns,
                availability_delay_ns=self.availability_delay_ns,
                basis="verified_bar_close", extra_quality_flags=tuple(flags),
            )
        if self.timestamp_semantics in (TimestampSemantics.BAR_CLOSE, TimestampSemantics.EVENT_COMPLETION):
            return BarClockPolicy(
                source_stamp="close", cadence_ns=None,
                availability_delay_ns=self.availability_delay_ns,
                basis="verified_bar_close", extra_quality_flags=tuple(flags),
            )
        return BarClockPolicy(
            source_stamp="conservative_next", cadence_ns=None,
            availability_delay_ns=self.availability_delay_ns,
            basis="unknown", extra_quality_flags=tuple(flags),
        )


@dataclass(frozen=True)
class RepresentationConsensus:
    """Robust cross-representation summary that preserves every representation identity."""
    symbol: str
    event_ns: int
    consensus_return: float
    disagreement: float
    directional_agreement: float
    representation_count: int
    contributions: dict[str, float]


def robust_representation_consensus(symbol: str, event_ns: int, returns: dict[str, float]) -> RepresentationConsensus:
    import math
    import numpy as np
    clean={k:float(v) for k,v in returns.items() if math.isfinite(float(v))}
    if not clean:
        return RepresentationConsensus(symbol,int(event_ns),0.0,0.0,0.0,0,{})
    vals=np.array(list(clean.values()),dtype=float)
    med=float(np.median(vals)); mad=float(np.median(np.abs(vals-med)))
    scale=max(1.4826*mad,1e-12)
    robust_z=np.abs(vals-med)/scale
    raw=1.0/(1.0+robust_z*robust_z); weights=raw/raw.sum()
    consensus=float(np.dot(weights,vals))
    disagreement=float(np.sqrt(np.dot(weights,(vals-consensus)**2)))
    if abs(consensus)<1e-15:
        agreement=float(np.mean(np.abs(vals)<scale))
    else:
        agreement=float(np.mean(np.sign(vals)==np.sign(consensus)))
    return RepresentationConsensus(symbol,int(event_ns),consensus,disagreement,agreement,len(clean),{k:float(w) for k,w in zip(clean,weights)})


@dataclass(frozen=True, slots=True)
class RepresentationHypothesis:
    kind:str
    confidence:float
    reasons:tuple[str,...]
    authoritative:bool=False

def infer_representation_hypothesis(manifest)->RepresentationHypothesis:
    """Triage representation behavior from data without asserting chart semantics.

    This deliberately returns a *hypothesis*. Only a reviewed registry may convert it
    into timestamp/availability authority.
    """
    from .filename import timeframe_claim_to_ns
    reasons=[];claim_ns=timeframe_claim_to_ns(manifest.identity.filename_claim);obs=manifest.observed_cadence_ns
    conf=float(manifest.cadence_confidence or 0.0)
    if 'fractional_time' in manifest.quality_flags:reasons.append('fractional_timestamps')
    if 'repeated_time' in manifest.quality_flags:reasons.append('repeated_timestamps')
    if claim_ns and obs:
        ratio=obs/claim_ns
        if abs(ratio-1.0)<=0.05 and conf>=0.5:
            reasons.append('observed_cadence_matches_filename_claim')
            return RepresentationHypothesis('fixed_time_candidate',min(0.99,0.6+0.4*conf),tuple(reasons),False)
        reasons.append(f'cadence_claim_ratio={ratio:.6g}')
        if ratio<0.2 or ratio>5.0 or 'fractional_time' in manifest.quality_flags:
            return RepresentationHypothesis('event_or_transformed_candidate',min(0.99,0.55+0.35*conf),tuple(reasons),False)
        return RepresentationHypothesis('timeframe_mismatch_candidate',min(0.9,0.45+0.3*conf),tuple(reasons),False)
    if 'fractional_time' in manifest.quality_flags or 'repeated_time' in manifest.quality_flags:
        return RepresentationHypothesis('event_or_transformed_candidate',0.6,tuple(reasons),False)
    return RepresentationHypothesis('unknown',max(0.1,min(0.5,conf)),tuple(reasons or ['insufficient_semantic_evidence']),False)
