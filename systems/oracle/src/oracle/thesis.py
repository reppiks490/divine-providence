from __future__ import annotations
from dataclasses import dataclass, field
import math
from .contracts import ThesisAssessment, finite01

@dataclass(frozen=True, slots=True)
class ThesisPolicy:
    half_life_ns: int = 86_400_000_000_000
    retest_age_ns: int = 259_200_000_000_000
    drift_threshold: float = .20
    min_effective_health: float = .35
    def __post_init__(self):
        if self.half_life_ns<=0 or self.retest_age_ns<=0: raise ValueError("thesis age policies must be positive")
        finite01("drift_threshold",self.drift_threshold); finite01("min_effective_health",self.min_effective_health)

@dataclass(frozen=True, slots=True)
class ThesisHealthSnapshot:
    hypothesis_id: str
    decision_ns: int
    assessed_ns: int
    raw_health: float
    freshness: float
    effective_health: float
    drift: float
    retest_required: bool
    reasons: tuple[str,...]

@dataclass
class ThesisMonitor:
    policy: ThesisPolicy = field(default_factory=ThesisPolicy)
    history: dict[str,list[ThesisAssessment]] = field(default_factory=dict)
    def observe(self,a:ThesisAssessment)->None:
        rows=self.history.setdefault(a.hypothesis_id,[])
        if rows and a.assessed_ns<rows[-1].assessed_ns: raise ValueError("assessment time must be non-decreasing")
        if rows and a.assessed_ns==rows[-1].assessed_ns:
            if rows[-1]!=a: raise ValueError("assessment timestamp collision")
            return
        rows.append(a)
    def snapshot(self,hypothesis_id:str,decision_ns:int)->ThesisHealthSnapshot:
        rows=self.history.get(hypothesis_id,())
        if not rows: raise KeyError(hypothesis_id)
        cur=rows[-1]
        if decision_ns<cur.assessed_ns: raise ValueError("decision before assessment")
        age=decision_ns-cur.assessed_ns
        freshness=2.0**(-age/self.policy.half_life_ns)
        raw=cur.thesis_health; effective=max(0.0,min(1.0,raw*freshness))
        drift=abs(raw-rows[-2].thesis_health) if len(rows)>1 else 0.0
        reasons=[]
        if age>=self.policy.retest_age_ns: reasons.append("THESIS_STALE")
        if drift>=self.policy.drift_threshold: reasons.append("THESIS_DRIFT")
        if effective<self.policy.min_effective_health: reasons.append("THESIS_HEALTH_LOW")
        return ThesisHealthSnapshot(hypothesis_id,decision_ns,cur.assessed_ns,raw,freshness,effective,drift,bool(reasons),tuple(reasons))
