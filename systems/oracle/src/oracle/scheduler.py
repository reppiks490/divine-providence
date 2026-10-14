from __future__ import annotations
from typing import Mapping
import math
from .contracts import ResearchJob


def priority(job:ResearchJob)->float:
    # Geometric information value prevents one extreme dimension from hiding zero evidence value.
    info=max(1e-9,job.expected_information_gain)
    relevance=max(1e-9,job.strategic_relevance)
    deficit=max(1e-9,job.evidence_deficit)
    impact=max(1e-9,job.dependency_impact)
    novelty=max(.05,job.novelty)
    value=(info*relevance*deficit*impact)**0.25
    return value*(0.75+0.25*novelty)/max(job.estimated_compute_cost,1e-9)


def rank_jobs(jobs:list[ResearchJob])->list[ResearchJob]:
    return sorted(jobs,key=lambda j:(-priority(j),j.created_ns,j.job_id))


def rank_jobs_adaptive(jobs:list[ResearchJob], multipliers:Mapping[str,float]|None=None)->list[ResearchJob]:
    """Rank immutable jobs through a causal, external priority overlay.

    The ResearchJob specification never changes after creation. Operating-layer
    urgency is expressed only as a positive multiplier keyed by job id. This
    keeps original research intent auditable while allowing deterministic
    reprioritization as evidence/state changes.
    """
    m=multipliers or {}
    def score(j:ResearchJob)->float:
        x=float(m.get(j.job_id,1.0))
        if not 0.05<=x<=20.0:
            raise ValueError("priority multiplier must be in [0.05,20]")
        return priority(j)*x
    return sorted(jobs,key=lambda j:(-score(j),j.created_ns,j.job_id))


class ResearchScheduler:
    def __init__(self): self._jobs:dict[str,ResearchJob]={}
    def submit(self,job:ResearchJob)->None:
        prior=self._jobs.get(job.job_id)
        if prior is not None and prior!=job: raise ValueError("job id collision")
        self._jobs[job.job_id]=job
    def rank(self,decision_ns:int,*,multipliers:Mapping[str,float]|None=None,
             groups:Mapping[str,str]|None=None, group_counts:Mapping[str,int]|None=None,
             diversity_penalty:float=1.0, limit:int|None=None)->list[ResearchJob]:
        if limit is not None and (type(limit) is not int or limit<0): raise ValueError("invalid ranking limit")
        jobs=[j for j in self._jobs.values() if j.status=="QUEUED" and j.created_ns<=decision_ns]
        ranked=rank_jobs_adaptive(jobs,multipliers) if multipliers is not None else rank_jobs(jobs)
        if groups is None: return ranked if limit is None else ranked[:limit]
        if not math.isfinite(diversity_penalty) or diversity_penalty<0: raise ValueError("invalid diversity penalty")
        counts=dict(group_counts or {})
        if any(type(v) is not int or v<0 for v in counts.values()): raise ValueError("invalid group counts")
        def group(job): return groups.get(job.job_id,"job:"+job.job_id)
        # Marginal utility is an explainable policy overlay. No specification,
        # empirical information-gain estimate, or second scheduler is invented.
        selected=[]
        while ranked and (limit is None or len(selected)<limit):
            def score(j):
                return priority(j)*float((multipliers or {}).get(j.job_id,1))/(1+diversity_penalty*counts.get(group(j),0))
            best=min(ranked,key=lambda j:(-score(j),j.created_ns,j.job_id))
            selected.append(best); ranked.remove(best)
            key=group(best); counts[key]=counts.get(key,0)+1
        return selected
