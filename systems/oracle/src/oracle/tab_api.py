from __future__ import annotations
from dataclasses import asdict,dataclass
from typing import Any
from .contracts import canonical,digest
from .decision_policy import ResearchRecommendation
from .operating import OracleOperatingLayer,PriorityDecision
from .views import CommandGraphView,FinancialTabView,ResearchTabView

_SCHEMA="icarus.oracle.tabs.v1"

@dataclass(frozen=True,slots=True)
class FinancialResearchSnapshot:
    schema:str
    decision_ns:int
    financial:FinancialTabView
    research:ResearchTabView
    actions:tuple[ResearchRecommendation,...]
    priorities:tuple[PriorityDecision,...]
    command_graph:CommandGraphView
    production_authorized:bool=False
    def __post_init__(self):
        if self.schema!=_SCHEMA or self.decision_ns<0: raise ValueError("invalid tab snapshot")
        if self.production_authorized: raise ValueError("tab snapshot cannot authorize production")
    @property
    def snapshot_hash(self)->str:
        return digest(asdict(self))
    def to_dict(self)->dict[str,Any]:
        out=asdict(self); out["snapshot_hash"]=self.snapshot_hash; return out

@dataclass(frozen=True,slots=True)
class TabDelta:
    from_hash:str
    to_hash:str
    decision_ns:int
    financial_changed:bool
    changed_hypotheses:tuple[str,...]
    changed_priorities:tuple[str,...]
    warnings_changed:bool
    def __post_init__(self):
        if not self.from_hash or not self.to_hash or self.decision_ns<0: raise ValueError("invalid tab delta")

class OracleTabAPI:
    """Stable read model for the Icarus Financial and Research tabs."""
    def __init__(self,operating:OracleOperatingLayer): self.operating=operating
    def snapshot(self,decision_ns:int)->FinancialResearchSnapshot:
        v=self.operating.views(decision_ns)
        return FinancialResearchSnapshot(
            _SCHEMA,decision_ns,v.financial,v.research,self.operating.action_board(decision_ns),
            self.operating.priority_decisions(decision_ns),v.command_graph,False,
        )
    @staticmethod
    def delta(previous:FinancialResearchSnapshot,current:FinancialResearchSnapshot)->TabDelta:
        if current.decision_ns<previous.decision_ns: raise ValueError("tab snapshots cannot move backwards")
        p_rows={x.hypothesis_id:canonical(asdict(x)) for x in previous.research.hypotheses}
        c_rows={x.hypothesis_id:canonical(asdict(x)) for x in current.research.hypotheses}
        changed_h=tuple(sorted(k for k in set(p_rows)|set(c_rows) if p_rows.get(k)!=c_rows.get(k)))
        p_pr={x.job_id:canonical(asdict(x)) for x in previous.priorities}
        c_pr={x.job_id:canonical(asdict(x)) for x in current.priorities}
        changed_p=tuple(sorted(k for k in set(p_pr)|set(c_pr) if p_pr.get(k)!=c_pr.get(k)))
        return TabDelta(
            previous.snapshot_hash,current.snapshot_hash,current.decision_ns,
            canonical(asdict(previous.financial))!=canonical(asdict(current.financial)),
            changed_h,changed_p,previous.financial.warnings!=current.financial.warnings,
        )
