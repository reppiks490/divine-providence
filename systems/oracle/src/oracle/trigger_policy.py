from __future__ import annotations
from dataclasses import dataclass, field
import math
from .contracts import FinancialState
from .hypothesis_factory import Trigger

@dataclass(frozen=True, slots=True)
class FeatureTriggerSpec:
    metric: str
    target: str
    abs_delta: float | None = None
    rel_delta: float | None = None
    trigger_type: str = "feature_dislocation"
    def __post_init__(self):
        if not self.metric or not self.target: raise ValueError("metric/target required")
        if self.abs_delta is None and self.rel_delta is None: raise ValueError("at least one threshold required")
        if self.abs_delta is not None and self.abs_delta <= 0: raise ValueError("abs_delta must be positive")
        if self.rel_delta is not None and self.rel_delta <= 0: raise ValueError("rel_delta must be positive")

@dataclass(frozen=True, slots=True)
class FinancialTriggerPolicy:
    min_state_confidence: float = .55
    ood_enter: float = .80
    ood_exit: float = .60
    health_enter: float = .45
    health_exit: float = .65
    cooldown_ns: int = 900_000_000_000
    feature_reset_fraction: float = .50
    def __post_init__(self):
        for name in ("min_state_confidence","ood_enter","ood_exit","health_enter","health_exit","feature_reset_fraction"):
            v=float(getattr(self,name))
            if not 0<=v<=1: raise ValueError(f"{name} must be in [0,1]")
        if self.ood_exit>self.ood_enter or self.health_exit<self.health_enter: raise ValueError("invalid hysteresis bands")
        if self.cooldown_ns<0: raise ValueError("cooldown_ns must be non-negative")

@dataclass
class AdaptiveTriggerDetector:
    policy: FinancialTriggerPolicy = field(default_factory=FinancialTriggerPolicy)
    _last_state: FinancialState | None = None
    _last_emit: dict[str,int] = field(default_factory=dict)
    _latched: set[str] = field(default_factory=set)

    def _ready(self,key:str,now:int)->bool:
        return now-self._last_emit.get(key,-10**30)>=self.policy.cooldown_ns
    def _emit(self,key:str,t:Trigger)->Trigger:
        self._last_emit[key]=t.decision_ns; self._latched.add(key); return t
    @staticmethod
    def _lineage(state:FinancialState)->tuple[str,...]:
        return tuple(sorted({p.lineage_id for p in state.provenance if p.lineage_id}))

    def evaluate(self,state:FinancialState,*,feature_specs:tuple[FeatureTriggerSpec,...]=())->tuple[Trigger,...]:
        if self._last_state is not None and state.decision_ns<self._last_state.decision_ns: raise ValueError("financial states must be non-decreasing in decision time")
        prev=self._last_state; self._last_state=state; out=[]; lineage=self._lineage(state)
        # Hysteresis state is updated even when confidence is too low, but low-confidence states do not create research.
        if state.ood_score<=self.policy.ood_exit: self._latched.discard("ood")
        avg_health=sum(state.source_health.values())/len(state.source_health) if state.source_health else 0.0
        if avg_health>=self.policy.health_exit: self._latched.discard("health")
        if state.confidence<self.policy.min_state_confidence: return ()
        if state.ood_score>=self.policy.ood_enter and "ood" not in self._latched and self._ready("ood",state.decision_ns):
            out.append(self._emit("ood",Trigger("financial_state_ood",state.decision_ns,"MARKET",state.ood_score,state.confidence,{"ood_score":state.ood_score,"state_confidence":state.confidence},lineage)))
        if state.source_health and avg_health<=self.policy.health_enter and "health" not in self._latched and self._ready("health",state.decision_ns):
            out.append(self._emit("health",Trigger("source_health_break",state.decision_ns,"DATA_FABRIC",1.0-avg_health,state.confidence,{"avg_source_health":avg_health,"state_confidence":state.confidence},lineage)))
        if prev is None: return tuple(out)
        specs={x.metric:x for x in feature_specs}
        for metric,spec in specs.items():
            if metric not in state.features or metric not in prev.features: continue
            cur=float(state.features[metric]); old=float(prev.features[metric]); delta=cur-old
            rel=abs(delta)/max(abs(old),1e-12)
            threshold_hit=(spec.abs_delta is not None and abs(delta)>=spec.abs_delta) or (spec.rel_delta is not None and rel>=spec.rel_delta)
            key=f"feature:{metric}"
            reset=(spec.abs_delta is None or abs(delta)<spec.abs_delta*self.policy.feature_reset_fraction) and (spec.rel_delta is None or rel<spec.rel_delta*self.policy.feature_reset_fraction)
            if reset: self._latched.discard(key)
            if threshold_hit and key not in self._latched and self._ready(key,state.decision_ns):
                mag=abs(delta) if spec.abs_delta is not None else rel
                context={metric:cur,"previous":old,"delta":delta,"relative_delta":rel}
                out.append(self._emit(key,Trigger(spec.trigger_type,state.decision_ns,spec.target,mag,state.confidence,context,lineage)))
        return tuple(out)
    def snapshot(self)->dict[str,object]:
        return {
            "last_state_id": self._last_state.state_id if self._last_state else None,
            "last_emit": {k:int(v) for k,v in sorted(self._last_emit.items())},
            "latched": sorted(self._latched),
        }

    def restore_control_state(self,payload:dict[str,object],*,last_state:FinancialState|None)->None:
        state_id=payload.get("last_state_id")
        if state_id is not None and (last_state is None or last_state.state_id!=state_id):
            raise ValueError("trigger detector state does not match durable financial state")
        self._last_state=last_state
        self._last_emit={str(k):int(v) for k,v in dict(payload.get("last_emit",{})).items()}
        self._latched={str(x) for x in payload.get("latched",[])}

