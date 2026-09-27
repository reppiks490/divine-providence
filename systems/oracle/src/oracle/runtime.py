from __future__ import annotations
from dataclasses import dataclass,field
from .contracts import JobStatus,digest

@dataclass(frozen=True,slots=True)
class RetryPolicy:
    max_attempts:int=3
    base_backoff_ns:int=1_000_000_000
    multiplier:int=2
    def __post_init__(self):
        if self.max_attempts<1 or self.base_backoff_ns<0 or self.multiplier<1: raise ValueError("invalid retry policy")
    def retry_at(self,attempt:int,failed_ns:int)->int:
        if attempt<1: raise ValueError("attempt is one-based")
        return failed_ns+self.base_backoff_ns*(self.multiplier**(attempt-1))

@dataclass(frozen=True,slots=True)
class AttemptRecord:
    attempt_id:str; job_id:str; attempt:int; started_ns:int; finished_ns:int|None=None; status:str=JobStatus.CLAIMED.value; error_code:str|None=None
    def __post_init__(self):
        if not self.attempt_id or not self.job_id or self.attempt<1 or self.started_ns<0: raise ValueError("invalid attempt")
        if self.finished_ns is not None and self.finished_ns<self.started_ns: raise ValueError("attempt finished before start")
        if self.status not in {s.value for s in JobStatus}: raise ValueError("invalid attempt status")

@dataclass
class JobRuntime:
    retry_policy:RetryPolicy=field(default_factory=RetryPolicy)
    attempts:dict[str,list[AttemptRecord]]=field(default_factory=dict)
    next_eligible_ns:dict[str,int]=field(default_factory=dict)
    dead_letter:dict[str,str]=field(default_factory=dict)
    completed:set[str]=field(default_factory=set)
    def can_claim(self,job_id:str,now_ns:int)->bool:
        return job_id not in self.dead_letter and job_id not in self.completed and now_ns>=self.next_eligible_ns.get(job_id,0) and not any(a.status==JobStatus.CLAIMED.value for a in self.attempts.get(job_id,()))
    def claim(self,job_id:str,now_ns:int)->AttemptRecord:
        if not self.can_claim(job_id,now_ns): raise ValueError("job is not claimable")
        n=len(self.attempts.get(job_id,()))+1
        if n>self.retry_policy.max_attempts: raise ValueError("retry limit exceeded")
        a=AttemptRecord("ATT-"+digest({"job":job_id,"attempt":n,"started_ns":now_ns})[:20],job_id,n,now_ns)
        self.attempts.setdefault(job_id,[]).append(a); return a
    def complete(self,job_id:str,finished_ns:int)->AttemptRecord:
        cur=self._claimed(job_id); done=AttemptRecord(cur.attempt_id,cur.job_id,cur.attempt,cur.started_ns,finished_ns,JobStatus.COMPLETED.value)
        self.attempts[job_id][-1]=done; self.next_eligible_ns.pop(job_id,None); self.completed.add(job_id); return done
    def fail(self,job_id:str,failed_ns:int,error_code:str)->AttemptRecord:
        cur=self._claimed(job_id); failed=AttemptRecord(cur.attempt_id,cur.job_id,cur.attempt,cur.started_ns,failed_ns,JobStatus.FAILED.value,error_code or "UNKNOWN")
        self.attempts[job_id][-1]=failed
        if cur.attempt>=self.retry_policy.max_attempts:self.dead_letter[job_id]=failed.error_code or "UNKNOWN"
        else:self.next_eligible_ns[job_id]=self.retry_policy.retry_at(cur.attempt,failed_ns)
        return failed
    def restore_attempt(self,record:AttemptRecord)->None:
        rows=self.attempts.setdefault(record.job_id,[])
        expected=len(rows)+1
        if record.attempt!=expected: raise ValueError("attempt recovery order mismatch")
        rows.append(record)
        if record.status==JobStatus.COMPLETED.value:
            self.completed.add(record.job_id); self.next_eligible_ns.pop(record.job_id,None); self.dead_letter.pop(record.job_id,None)
        elif record.status==JobStatus.FAILED.value:
            if record.attempt>=self.retry_policy.max_attempts:
                self.dead_letter[record.job_id]=record.error_code or "RECOVERED_FAILURE"
                self.next_eligible_ns.pop(record.job_id,None)
            elif record.finished_ns is not None:
                self.next_eligible_ns[record.job_id]=self.retry_policy.retry_at(record.attempt,record.finished_ns)
        elif record.status==JobStatus.CLAIMED.value:
            self.next_eligible_ns.pop(record.job_id,None)
    def _claimed(self,job_id:str)->AttemptRecord:
        rows=self.attempts.get(job_id,())
        if not rows or rows[-1].status!=JobStatus.CLAIMED.value: raise ValueError("job has no claimed attempt")
        return rows[-1]
