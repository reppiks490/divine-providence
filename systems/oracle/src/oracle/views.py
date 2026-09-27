from __future__ import annotations
from dataclasses import asdict,dataclass
from typing import Any
from .contracts import FinancialState,HypothesisStatus

@dataclass(frozen=True,slots=True)
class FinancialTabView:
    as_of_ns:int
    state_id:str|None
    state_confidence:float
    ood_score:float
    metrics:tuple[tuple[str,float],...]
    source_health:tuple[tuple[str,float],...]
    active_hypotheses:int
    testing_hypotheses:int
    approved_features:int
    warnings:tuple[str,...]

@dataclass(frozen=True,slots=True)
class ResearchHypothesisRow:
    hypothesis_id:str; family:str; target:str; horizon:str; status:str
    thesis_health:float|None; evidence_coverage:float|None; pending_jobs:int; completed_jobs:int
    pending_packets:int; reasons:tuple[str,...]

@dataclass(frozen=True,slots=True)
class ResearchTabView:
    as_of_ns:int
    hypotheses:tuple[ResearchHypothesisRow,...]
    queued_jobs:int
    active_jobs:int
    dead_letter_jobs:int
    pending_packets:int
    journal_head:str

@dataclass(frozen=True,slots=True)
class CommandGraphView:
    as_of_ns:int
    nodes:tuple[dict[str,Any],...]
    edges:tuple[dict[str,Any],...]

class OracleViewProjector:
    @staticmethod
    def financial(loop,state:FinancialState|None,*,as_of_ns:int)->FinancialTabView:
        statuses=tuple(loop.engine.status.values())
        warnings=[]
        if state is None: warnings.append("NO_FINANCIAL_STATE")
        elif state.confidence<.55: warnings.append("LOW_STATE_CONFIDENCE")
        if state is not None and state.ood_score>=.8: warnings.append("HIGH_OOD")
        if state is not None and state.source_health and min(state.source_health.values())<.5: warnings.append("SOURCE_HEALTH_DEGRADED")
        return FinancialTabView(
            as_of_ns,state.state_id if state else None,state.confidence if state else 0.0,state.ood_score if state else 0.0,
            tuple(sorted((k,float(v)) for k,v in (state.features.items() if state else ()))),
            tuple(sorted((k,float(v)) for k,v in (state.source_health.items() if state else ()))),
            sum(s not in {HypothesisStatus.REJECTED,HypothesisStatus.RETIRED} for s in statuses),
            sum(s is HypothesisStatus.TESTING for s in statuses),sum(s is HypothesisStatus.APPROVED_FEATURE for s in statuses),tuple(warnings))

    @staticmethod
    def research(loop,*,as_of_ns:int)->ResearchTabView:
        rows=[]
        for hid,h in sorted(loop.engine.hypotheses.items()):
            jobs=[j for j in loop.engine.scheduler._jobs.values() if j.hypothesis_id==hid]
            completed=sum(j.job_id in loop.runtime.completed for j in jobs)
            pending=sum(loop.runtime.can_claim(j.job_id,as_of_ns) for j in jobs)
            assessment=loop.engine.assessments.get(hid)
            reasons=assessment.reason_codes if assessment else ("NOT_ASSESSED",)
            rows.append(ResearchHypothesisRow(hid,h.family,h.target,h.horizon,loop.engine.status[hid].value,assessment.thesis_health if assessment else None,assessment.evidence_coverage if assessment else None,pending,completed,sum(not loop.outbox.is_acked(p.packet_id) and p.packet_id not in loop.outbox.failed for p in loop.outbox.packets.values() if p.hypothesis_id==hid),tuple(reasons)))
        journal_head=loop.journal.head_hash if loop.journal.path is not None else 'UNPERSISTED'
        return ResearchTabView(as_of_ns,tuple(rows),sum(loop.runtime.can_claim(j.job_id,as_of_ns) for j in loop.engine.scheduler._jobs.values()),sum(bool(a and a[-1].status=='CLAIMED') for a in loop.runtime.attempts.values()),len(loop.runtime.dead_letter),len(loop.outbox.pending()),journal_head)

    @staticmethod
    def command_graph(loop,*,as_of_ns:int)->CommandGraphView:
        nodes=tuple({"id":n.node_id,"kind":n.kind,**n.attrs} for _,n in sorted(loop.engine.graph.nodes.items()))
        active=sorted(loop.engine.graph.active_edges(as_of_ns),key=lambda e:(e.source,e.target,e.relation,e.valid_from_ns,e.valid_to_ns if e.valid_to_ns is not None else 2**63-1))
        edges=tuple({"source":e.source,"target":e.target,"relation":e.relation,"weight":e.weight,"uncertainty":e.uncertainty,"valid_from_ns":e.valid_from_ns,"valid_to_ns":e.valid_to_ns} for e in active)
        return CommandGraphView(as_of_ns,nodes,edges)
