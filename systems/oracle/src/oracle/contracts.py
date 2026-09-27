from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib, json, math
from typing import Any, Mapping


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False, default=str)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def finite01(name: str, value: float) -> float:
    value=float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be finite in [0,1]")
    return value


class DataPlane(str, Enum):
    RESEARCH="research"
    SHADOW="shadow"
    PRODUCTION_OBSERVATION="production_observation"


class HypothesisStatus(str, Enum):
    DISCOVERED="DISCOVERED"
    QUEUED="QUEUED"
    TESTING="TESTING"
    VALIDATED="VALIDATED"
    STRESS_TESTED="STRESS_TESTED"
    SHADOW="SHADOW"
    APPROVED_FEATURE="APPROVED_FEATURE"
    REJECTED="REJECTED"
    RETIRED="RETIRED"


class JobStatus(str, Enum):
    QUEUED="QUEUED"
    CLAIMED="CLAIMED"
    COMPLETED="COMPLETED"
    FAILED="FAILED"
    CANCELLED="CANCELLED"


@dataclass(frozen=True, slots=True)
class Provenance:
    source_system: str
    source_id: str
    event_ns: int
    available_ns: int
    ingested_ns: int
    plane: str=DataPlane.RESEARCH.value
    lineage_id: str=""
    quality_flags: tuple[str,...]=()
    version: str="v1"
    def __post_init__(self):
        if not self.source_system or not self.source_id: raise ValueError("source identity required")
        if min(self.event_ns,self.available_ns,self.ingested_ns)<0: raise ValueError("timestamps must be non-negative")
        if self.event_ns>self.available_ns or self.available_ns>self.ingested_ns: raise ValueError("causal timestamp ordering violated")
        if self.plane not in {p.value for p in DataPlane}: raise ValueError("unknown plane")


@dataclass(frozen=True, slots=True)
class FinancialState:
    state_id: str
    decision_ns: int
    features: Mapping[str,float]
    confidence: float
    ood_score: float
    source_health: Mapping[str,float]=field(default_factory=dict)
    provenance: tuple[Provenance,...]=()
    production_authorized: bool=False
    def __post_init__(self):
        if not self.state_id or self.decision_ns<0: raise ValueError("invalid state identity")
        finite01("confidence",self.confidence); finite01("ood_score",self.ood_score)
        for k,v in self.features.items():
            if not k or not math.isfinite(float(v)): raise ValueError("features must be finite")
        if self.production_authorized: raise ValueError("ORACLE financial states cannot authorize production")
    @property
    def state_hash(self)->str: return digest({"id":self.state_id,"t":self.decision_ns,"features":dict(self.features),"confidence":self.confidence,"ood":self.ood_score})


@dataclass(frozen=True, slots=True)
class Hypothesis:
    hypothesis_id: str
    family: str
    statement: str
    target: str
    horizon: str
    falsification_criteria: tuple[str,...]
    created_ns: int
    trigger_state_id: str|None=None
    status: str=HypothesisStatus.DISCOVERED.value
    tags: tuple[str,...]=()
    parent_ids: tuple[str,...]=()
    production_authorized: bool=False
    def __post_init__(self):
        if not all((self.hypothesis_id,self.family,self.statement,self.target,self.horizon)): raise ValueError("hypothesis fields required")
        if self.created_ns<0: raise ValueError("created_ns must be non-negative")
        if self.status not in {s.value for s in HypothesisStatus}: raise ValueError("invalid hypothesis status")
        if not self.falsification_criteria: raise ValueError("falsification criteria required")
        if self.production_authorized: raise ValueError("research hypothesis cannot authorize production")
    @property
    def spec_hash(self)->str:
        return digest({"family":self.family,"statement":self.statement,"target":self.target,"horizon":self.horizon,"falsification":self.falsification_criteria,"parents":self.parent_ids})


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    hypothesis_id: str
    source_system: str
    kind: str
    observed_ns: int
    payload: Mapping[str,Any]
    lineage_hash: str
    strength: float
    supports: bool|None
    plane: str=DataPlane.RESEARCH.value
    immutable_hash: str=""
    def __post_init__(self):
        if not all((self.evidence_id,self.hypothesis_id,self.source_system,self.kind,self.lineage_hash)): raise ValueError("evidence identity required")
        if self.observed_ns<0: raise ValueError("observed_ns must be non-negative")
        finite01("strength",self.strength)
        if self.plane not in {p.value for p in DataPlane}: raise ValueError("unknown plane")
        canonical(dict(self.payload))
        computed=digest({"id":self.evidence_id,"hypothesis_id":self.hypothesis_id,"source_system":self.source_system,"kind":self.kind,"observed_ns":self.observed_ns,"payload":dict(self.payload),"lineage_hash":self.lineage_hash,"strength":self.strength,"supports":self.supports,"plane":self.plane})
        if self.immutable_hash and self.immutable_hash!=computed: raise ValueError("evidence immutable_hash mismatch")
        object.__setattr__(self,"immutable_hash",computed)


@dataclass(frozen=True, slots=True)
class ResearchJob:
    job_id: str
    hypothesis_id: str
    task_type: str
    created_ns: int
    expected_information_gain: float
    strategic_relevance: float
    evidence_deficit: float
    dependency_impact: float
    novelty: float
    estimated_compute_cost: float
    required_systems: tuple[str,...]=()
    required_states: tuple[str,...]=()
    status: str=JobStatus.QUEUED.value
    production_authorized: bool=False
    def __post_init__(self):
        if not all((self.job_id,self.hypothesis_id,self.task_type)): raise ValueError("job identity required")
        if self.created_ns<0 or self.estimated_compute_cost<=0: raise ValueError("invalid job timing/cost")
        for n in ("expected_information_gain","strategic_relevance","evidence_deficit","dependency_impact","novelty"):
            finite01(n,getattr(self,n))
        if self.status not in {s.value for s in JobStatus}: raise ValueError("invalid job status")
        if self.production_authorized: raise ValueError("research job cannot authorize production")


@dataclass(frozen=True, slots=True)
class LifecycleTransition:
    hypothesis_id: str
    from_status: str
    to_status: str
    occurred_ns: int
    reason: str
    evidence_ids: tuple[str,...]=()
    actor: str="ORACLE"
    def __post_init__(self):
        valid={s.value for s in HypothesisStatus}
        if self.from_status not in valid or self.to_status not in valid: raise ValueError("invalid lifecycle status")
        if self.occurred_ns<0 or not self.reason: raise ValueError("transition timing/reason required")


@dataclass(frozen=True, slots=True)
class PromotionEvidence:
    daedalus_promoted: bool
    holdout_clean: bool
    stress_passed: bool
    shadow_ready: bool
    athena_abstain: bool
    athena_ood_score: float
    unresolved_critical_quality_flags: tuple[str,...]=()
    def __post_init__(self): finite01("athena_ood_score",self.athena_ood_score)


def to_dict(obj: Any)->dict[str,Any]:
    return asdict(obj)

@dataclass(frozen=True, slots=True)
class ThesisAssessment:
    hypothesis_id: str
    assessed_ns: int
    support_score: float
    contradiction_score: float
    evidence_coverage: float
    robustness_score: float
    regime_fit: float
    data_confidence: float
    ood_risk: float
    evidence_ids: tuple[str,...]=()
    reason_codes: tuple[str,...]=()
    production_authorized: bool=False
    def __post_init__(self):
        if not self.hypothesis_id or self.assessed_ns < 0: raise ValueError("invalid thesis assessment")
        for n in ("support_score","contradiction_score","evidence_coverage","robustness_score","regime_fit","data_confidence","ood_risk"):
            finite01(n,getattr(self,n))
        if self.production_authorized: raise ValueError("ORACLE thesis assessment cannot authorize production")
    @property
    def thesis_health(self)->float:
        positive=(self.support_score+self.evidence_coverage+self.robustness_score+self.regime_fit+self.data_confidence)/5.0
        return max(0.0,min(1.0,positive*(1.0-0.65*max(self.contradiction_score,self.ood_risk))))
