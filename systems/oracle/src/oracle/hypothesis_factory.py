from __future__ import annotations
from dataclasses import dataclass
from .contracts import FinancialState,Hypothesis,digest

@dataclass(frozen=True,slots=True)
class Trigger:
    trigger_type:str; decision_ns:int; target:str; magnitude:float; confidence:float; context:dict[str,float]; lineage_hashes:tuple[str,...]=()

def from_anomaly(trigger:Trigger,*,horizon:str="60m")->Hypothesis:
    family=f"anomaly::{trigger.trigger_type}"
    hid="HYP-"+digest({"family":family,"decision_ns":trigger.decision_ns,"target":trigger.target,"context":trigger.context,"lineage":trigger.lineage_hashes,"horizon":horizon})[:20]
    statement=f"When {trigger.trigger_type} occurs in {trigger.target} with magnitude {trigger.magnitude:.6g}, does the forward state distribution differ materially from its regime-conditioned baseline over {horizon}?"
    return Hypothesis(hid,family,statement,trigger.target,horizon,(
        "effect disappears under purged walk-forward validation",
        "effect fails source/sensor ablation",
        "effect is unstable across regimes or time slices",
        "effect is explained by timestamp leakage or unavailable data",
        "effect fails realistic latency/cost perturbation when execution-related",
    ),trigger.decision_ns,tags=("machine_generated","falsification_first"))

def from_financial_state(state:FinancialState,*,trigger_type:str,target:str,magnitude:float,horizon:str="60m")->Hypothesis:
    t=Trigger(trigger_type,state.decision_ns,target,magnitude,state.confidence,dict(state.features),tuple(p.lineage_id for p in state.provenance if p.lineage_id)); return from_anomaly(t,horizon=horizon)
