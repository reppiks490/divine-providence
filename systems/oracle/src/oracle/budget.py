from __future__ import annotations
from dataclasses import dataclass,field
from .contracts import ResearchJob

@dataclass(frozen=True,slots=True)
class ResearchBudget:
    compute_units:float
    max_active_jobs:int=16
    max_jobs_per_hypothesis:int=12
    max_jobs_per_system:int=8
    def __post_init__(self):
        if self.compute_units<=0: raise ValueError("compute_units must be positive")
        if min(self.max_active_jobs,self.max_jobs_per_hypothesis,self.max_jobs_per_system)<=0: raise ValueError("job caps must be positive")

@dataclass(frozen=True,slots=True)
class BudgetDecision:
    allowed:bool
    reason:str
    remaining_compute:float

@dataclass
class BudgetLedger:
    budget:ResearchBudget
    consumed_compute:float=0.0
    active_jobs:set[str]=field(default_factory=set)
    jobs_by_hypothesis:dict[str,set[str]]=field(default_factory=dict)
    jobs_by_system:dict[str,set[str]]=field(default_factory=dict)
    def remaining(self)->float: return max(0.0,self.budget.compute_units-self.consumed_compute)
    def check(self,job:ResearchJob)->BudgetDecision:
        if job.estimated_compute_cost>self.remaining(): return BudgetDecision(False,"COMPUTE_BUDGET_EXHAUSTED",self.remaining())
        if len(self.active_jobs)>=self.budget.max_active_jobs: return BudgetDecision(False,"ACTIVE_JOB_CAP",self.remaining())
        if len(self.jobs_by_hypothesis.get(job.hypothesis_id,set()))>=self.budget.max_jobs_per_hypothesis: return BudgetDecision(False,"HYPOTHESIS_JOB_CAP",self.remaining())
        for system in job.required_systems:
            if len(self.jobs_by_system.get(system.upper(),set()))>=self.budget.max_jobs_per_system:
                return BudgetDecision(False,f"SYSTEM_JOB_CAP:{system.upper()}",self.remaining())
        return BudgetDecision(True,"OK",self.remaining())
    def reserve(self,job:ResearchJob)->BudgetDecision:
        d=self.check(job)
        if not d.allowed:return d
        self.consumed_compute+=job.estimated_compute_cost; self.active_jobs.add(job.job_id)
        self.jobs_by_hypothesis.setdefault(job.hypothesis_id,set()).add(job.job_id)
        for system in job.required_systems:self.jobs_by_system.setdefault(system.upper(),set()).add(job.job_id)
        return BudgetDecision(True,"RESERVED",self.remaining())
    def release(self,job:ResearchJob)->None:
        self.active_jobs.discard(job.job_id)
        # Historical counts intentionally stay in per-hypothesis/system sets; caps are anti-runaway totals.
    def restore_reservation(self,job:ResearchJob,*,active:bool)->None:
        self.consumed_compute+=job.estimated_compute_cost
        self.jobs_by_hypothesis.setdefault(job.hypothesis_id,set()).add(job.job_id)
        for system in job.required_systems:self.jobs_by_system.setdefault(system.upper(),set()).add(job.job_id)
        if active:self.active_jobs.add(job.job_id)
