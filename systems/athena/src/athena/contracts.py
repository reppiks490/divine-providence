from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Sequence


class DataPlane(str, Enum):
    RESEARCH = "research"
    SHADOW = "shadow"
    PRODUCTION = "production"


@dataclass(frozen=True)
class Provenance:
    event_time_ns: int
    ingestion_time_ns: int
    source_id: str
    representation_id: str
    version: str
    plane: DataPlane
    lineage_id: str
    quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExpertEvidence:
    expert_id: str
    score: float
    calibration_error: float
    ood_score: float
    recent_health: float
    supported_states: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorldState:
    state_id: str
    confidence: float
    ood_score: float
    transition_entropy: float
    expected_duration: float
    features: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class Advisory:
    state_id: str
    state_confidence: float
    ood_score: float
    expert_weights: Mapping[str, float]
    risk_multiplier: float
    abstain: bool
    reason_codes: tuple[str, ...]
    evidence_version: str
    production_authorized: bool = False


@dataclass(frozen=True)
class ResearchRequest:
    hypothesis_family: str
    expected_information_gain: float
    strategic_relevance: float
    evidence_deficit: float
    estimated_compute_cost: float
    required_states: Sequence[str] = ()
