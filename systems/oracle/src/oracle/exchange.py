from __future__ import annotations
from dataclasses import dataclass
from .contracts import EvidenceRecord,Hypothesis,ThesisAssessment,digest
@dataclass(frozen=True,slots=True)
class ResearchQuestion:
    question_id:str; hypothesis_id:str; requested_kinds:tuple[str,...]; created_ns:int; prompt:str
@dataclass(frozen=True,slots=True)
class Contribution:
    contribution_id:str; question_id:str; system:str; evidence:EvidenceRecord; claim:str; submitted_ns:int
class ResearchExchange:
    DEFAULT_KINDS=("market_state","historical_analogue","microstructure_context","supervisory_context","research_result","data_quality")
    def __init__(self): self.questions={}; self.contributions={}
    def open(self,h:Hypothesis,*,requested_kinds:tuple[str,...]|None=None,prompt:str|None=None)->ResearchQuestion:
        kinds=tuple(requested_kinds or self.DEFAULT_KINDS); qid="RQ-"+digest({"hypothesis_id":h.hypothesis_id,"kinds":kinds})[:20]
        q=ResearchQuestion(qid,h.hypothesis_id,kinds,h.created_ns,prompt or h.statement)
        old=self.questions.get(qid)
        if old is not None and old!=q: raise ValueError("research question collision")
        self.questions[qid]=q; return q
    def contribute(self,question_id:str,*,system:str,evidence:EvidenceRecord,claim:str,submitted_ns:int)->Contribution:
        q=self.questions[question_id]
        if evidence.hypothesis_id!=q.hypothesis_id or submitted_ns<evidence.observed_ns: raise ValueError("invalid contribution")
        cid="RC-"+digest({"q":question_id,"system":system,"evidence":evidence.evidence_id,"claim":claim})[:20]
        c=Contribution(cid,question_id,system,evidence,claim,submitted_ns); self.contributions.setdefault(cid,c); return self.contributions[cid]
    def assess(self,question_id:str,*,assessed_ns:int,robustness_score:float=0,regime_fit:float=0,data_confidence:float=0,ood_risk:float=0)->ThesisAssessment:
        q=self.questions[question_id]; cs=tuple(sorted((c for c in self.contributions.values() if c.question_id==question_id),key=lambda c:(c.submitted_ns,c.contribution_id)))
        covered={c.evidence.kind for c in cs}; coverage=len(covered.intersection(q.requested_kinds))/max(1,len(q.requested_kinds))
        # source cap: repeated evidence from one subsystem cannot create unlimited voting power
        by={}
        for c in cs: by.setdefault(c.system.upper(),[]).append(c)
        sm=cm=0.0
        for rows in by.values():
            denom=max(1.0,sum(x.evidence.strength for x in rows)); sm+=sum(x.evidence.strength for x in rows if x.evidence.supports is True)/denom; cm+=sum(x.evidence.strength for x in rows if x.evidence.supports is False)/denom
        n=max(1,len(by)); sm/=n; cm/=n
        missing=tuple(sorted(set(q.requested_kinds)-covered)); reasons=tuple(f"MISSING_{k.upper()}" for k in missing)
        return ThesisAssessment(q.hypothesis_id,assessed_ns,min(1,sm),min(1,cm),coverage,robustness_score,regime_fit,data_confidence,ood_risk,tuple(c.evidence.evidence_id for c in cs),reasons,False)
