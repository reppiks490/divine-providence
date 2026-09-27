from __future__ import annotations
import json,sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any
from .contracts import EvidenceRecord,FinancialState,Hypothesis,JobStatus,ResearchJob,ThesisAssessment,LifecycleTransition
from .plans import PlanTask, ResearchPlan

SCHEMA='''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS hypotheses(hypothesis_id TEXT PRIMARY KEY,spec_hash TEXT NOT NULL,payload_json TEXT NOT NULL,created_ns INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS evidence(evidence_id TEXT PRIMARY KEY,hypothesis_id TEXT NOT NULL,immutable_hash TEXT NOT NULL,payload_json TEXT NOT NULL,observed_ns INTEGER NOT NULL,FOREIGN KEY(hypothesis_id) REFERENCES hypotheses(hypothesis_id));
CREATE TABLE IF NOT EXISTS jobs(job_id TEXT PRIMARY KEY,hypothesis_id TEXT NOT NULL,payload_json TEXT NOT NULL,status TEXT NOT NULL,created_ns INTEGER NOT NULL,FOREIGN KEY(hypothesis_id) REFERENCES hypotheses(hypothesis_id));
CREATE TABLE IF NOT EXISTS assessments(hypothesis_id TEXT NOT NULL,assessed_ns INTEGER NOT NULL,payload_json TEXT NOT NULL,PRIMARY KEY(hypothesis_id,assessed_ns));
CREATE TABLE IF NOT EXISTS transitions(hypothesis_id TEXT NOT NULL,occurred_ns INTEGER NOT NULL,from_status TEXT NOT NULL,to_status TEXT NOT NULL,payload_json TEXT NOT NULL,PRIMARY KEY(hypothesis_id,occurred_ns,to_status));
CREATE TABLE IF NOT EXISTS research_plans(plan_id TEXT PRIMARY KEY,hypothesis_id TEXT NOT NULL,created_ns INTEGER NOT NULL,payload_json TEXT NOT NULL,FOREIGN KEY(hypothesis_id) REFERENCES hypotheses(hypothesis_id));
CREATE TABLE IF NOT EXISTS plan_tasks(job_id TEXT PRIMARY KEY,plan_id TEXT NOT NULL,payload_json TEXT NOT NULL,FOREIGN KEY(job_id) REFERENCES jobs(job_id),FOREIGN KEY(plan_id) REFERENCES research_plans(plan_id));
CREATE TABLE IF NOT EXISTS job_evidence(job_id TEXT PRIMARY KEY,evidence_id TEXT NOT NULL UNIQUE,claim TEXT NOT NULL,received_ns INTEGER NOT NULL,FOREIGN KEY(job_id) REFERENCES jobs(job_id),FOREIGN KEY(evidence_id) REFERENCES evidence(evidence_id));
CREATE TABLE IF NOT EXISTS financial_states(state_id TEXT PRIMARY KEY,decision_ns INTEGER NOT NULL,payload_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS operating_state(state_key TEXT PRIMARY KEY,updated_ns INTEGER NOT NULL,payload_json TEXT NOT NULL);
'''

def _json(v:Any):
    return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False,default=lambda o:o.value if hasattr(o,"value") else str(o))

def _loads(raw:str)->dict[str,Any]:
    return json.loads(raw)

class OracleStore:
    def __init__(self,path:Path):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as c:
            c.executescript(SCHEMA)

    def add_hypothesis(self,h:Hypothesis):
        raw=_json(asdict(h))
        with sqlite3.connect(self.path) as c:
            row=c.execute("SELECT spec_hash,payload_json FROM hypotheses WHERE hypothesis_id=?",(h.hypothesis_id,)).fetchone()
            if row and row[0]!=h.spec_hash: raise ValueError("hypothesis identity collision")
            if row and row[1]!=raw: raise ValueError("hypothesis payload collision")
            if not row: c.execute("INSERT INTO hypotheses VALUES(?,?,?,?)",(h.hypothesis_id,h.spec_hash,raw,h.created_ns))

    def add_evidence(self,e:EvidenceRecord):
        raw=_json(asdict(e))
        with sqlite3.connect(self.path) as c:
            row=c.execute("SELECT immutable_hash,payload_json FROM evidence WHERE evidence_id=?",(e.evidence_id,)).fetchone()
            if row and row!=(e.immutable_hash,raw): raise ValueError("evidence identity collision")
            if not row: c.execute("INSERT INTO evidence VALUES(?,?,?,?,?)",(e.evidence_id,e.hypothesis_id,e.immutable_hash,raw,e.observed_ns))

    def add_job(self,j:ResearchJob):
        raw=_json(asdict(j))
        with sqlite3.connect(self.path) as c:
            row=c.execute("SELECT payload_json,status FROM jobs WHERE job_id=?",(j.job_id,)).fetchone()
            if row and row!=(raw,j.status): raise ValueError("job identity collision")
            if not row: c.execute("INSERT INTO jobs VALUES(?,?,?,?,?)",(j.job_id,j.hypothesis_id,raw,j.status,j.created_ns))

    def add_assessment(self,a:ThesisAssessment):
        raw=_json(asdict(a))
        with sqlite3.connect(self.path) as c:
            row=c.execute("SELECT payload_json FROM assessments WHERE hypothesis_id=? AND assessed_ns=?",(a.hypothesis_id,a.assessed_ns)).fetchone()
            if row and row[0]!=raw: raise ValueError("assessment snapshot is immutable")
            if not row: c.execute("INSERT INTO assessments VALUES(?,?,?)",(a.hypothesis_id,a.assessed_ns,raw))

    def add_transition(self,t:LifecycleTransition):
        raw=_json(asdict(t))
        with sqlite3.connect(self.path) as c:
            row=c.execute("SELECT payload_json FROM transitions WHERE hypothesis_id=? AND occurred_ns=? AND to_status=?",(t.hypothesis_id,t.occurred_ns,t.to_status)).fetchone()
            if row and row[0]!=raw: raise ValueError("transition identity collision")
            if not row: c.execute("INSERT INTO transitions VALUES(?,?,?,?,?)",(t.hypothesis_id,t.occurred_ns,t.from_status,t.to_status,raw))

    def add_plan(self,plan:ResearchPlan,task_by_job:dict[str,PlanTask])->None:
        raw=_json(asdict(plan))
        with sqlite3.connect(self.path) as c:
            row=c.execute("SELECT payload_json FROM research_plans WHERE plan_id=?",(plan.plan_id,)).fetchone()
            if row and row[0]!=raw: raise ValueError("research plan identity collision")
            if not row:
                c.execute("INSERT INTO research_plans VALUES(?,?,?,?)",(plan.plan_id,plan.hypothesis_id,plan.created_ns,raw))
            for job_id,task in sorted(task_by_job.items()):
                traw=_json(asdict(task))
                prior=c.execute("SELECT plan_id,payload_json FROM plan_tasks WHERE job_id=?",(job_id,)).fetchone()
                if prior and prior!=(plan.plan_id,traw): raise ValueError("plan task/job identity collision")
                if not prior: c.execute("INSERT INTO plan_tasks VALUES(?,?,?)",(job_id,plan.plan_id,traw))


    def add_evidence_for_job(self,job_id:str,e:EvidenceRecord,*,claim:str,received_ns:int)->None:
        if not job_id or not claim or received_ns<e.observed_ns: raise ValueError("invalid durable job evidence")
        eraw=_json(asdict(e))
        with sqlite3.connect(self.path) as c:
            row=c.execute("SELECT immutable_hash,payload_json FROM evidence WHERE evidence_id=?",(e.evidence_id,)).fetchone()
            if row and row!=(e.immutable_hash,eraw): raise ValueError("evidence identity collision")
            if not row: c.execute("INSERT INTO evidence VALUES(?,?,?,?,?)",(e.evidence_id,e.hypothesis_id,e.immutable_hash,eraw,e.observed_ns))
            link=c.execute("SELECT evidence_id,claim,received_ns FROM job_evidence WHERE job_id=?",(job_id,)).fetchone()
            expected=(e.evidence_id,claim,received_ns)
            if link and link!=expected: raise ValueError("job evidence link is immutable")
            if not link: c.execute("INSERT INTO job_evidence VALUES(?,?,?,?)",(job_id,e.evidence_id,claim,received_ns))

    def add_financial_state(self,state:FinancialState)->None:
        raw=_json(asdict(state))
        with sqlite3.connect(self.path) as c:
            row=c.execute("SELECT payload_json FROM financial_states WHERE state_id=?",(state.state_id,)).fetchone()
            if row and row[0]!=raw: raise ValueError("financial state identity collision")
            if not row: c.execute("INSERT INTO financial_states VALUES(?,?,?)",(state.state_id,state.decision_ns,raw))

    def put_operating_state(self,state_key:str,*,updated_ns:int,payload:dict[str,Any])->None:
        if not state_key or updated_ns<0: raise ValueError("invalid operating state")
        raw=_json(payload)
        with sqlite3.connect(self.path) as c:
            row=c.execute("SELECT updated_ns,payload_json FROM operating_state WHERE state_key=?",(state_key,)).fetchone()
            if row and updated_ns<int(row[0]): raise ValueError("operating state cannot move backwards")
            c.execute("INSERT INTO operating_state(state_key,updated_ns,payload_json) VALUES(?,?,?) ON CONFLICT(state_key) DO UPDATE SET updated_ns=excluded.updated_ns,payload_json=excluded.payload_json",(state_key,updated_ns,raw))

    def load_operating_state(self,state_key:str)->tuple[int,dict[str,Any]]|None:
        with sqlite3.connect(self.path) as c:
            row=c.execute("SELECT updated_ns,payload_json FROM operating_state WHERE state_key=?",(state_key,)).fetchone()
        return (int(row[0]),_loads(row[1])) if row else None

    def load_latest_financial_state(self)->FinancialState|None:
        with sqlite3.connect(self.path) as c:
            row=c.execute("SELECT payload_json FROM financial_states ORDER BY decision_ns DESC,state_id DESC LIMIT 1").fetchone()
        return FinancialState(**_loads(row[0])) if row else None
    def link_job_evidence(self,job_id:str,evidence_id:str,*,claim:str,received_ns:int)->None:
        if not job_id or not evidence_id or not claim or received_ns<0: raise ValueError("invalid job evidence link")
        with sqlite3.connect(self.path) as c:
            row=c.execute("SELECT evidence_id,claim,received_ns FROM job_evidence WHERE job_id=?",(job_id,)).fetchone()
            expected=(evidence_id,claim,received_ns)
            if row and row!=expected: raise ValueError("job evidence link is immutable")
            if not row: c.execute("INSERT INTO job_evidence VALUES(?,?,?,?)",(job_id,evidence_id,claim,received_ns))

    def load_hypotheses(self)->tuple[Hypothesis,...]:
        with sqlite3.connect(self.path) as c: rows=c.execute("SELECT payload_json FROM hypotheses ORDER BY created_ns,hypothesis_id").fetchall()
        return tuple(Hypothesis(**_loads(r[0])) for r in rows)

    def load_jobs(self)->tuple[ResearchJob,...]:
        with sqlite3.connect(self.path) as c: rows=c.execute("SELECT payload_json FROM jobs ORDER BY created_ns,job_id").fetchall()
        return tuple(ResearchJob(**_loads(r[0])) for r in rows)

    def load_evidence(self)->tuple[EvidenceRecord,...]:
        with sqlite3.connect(self.path) as c: rows=c.execute("SELECT payload_json FROM evidence ORDER BY observed_ns,evidence_id").fetchall()
        return tuple(EvidenceRecord(**_loads(r[0])) for r in rows)

    def load_assessments(self)->tuple[ThesisAssessment,...]:
        with sqlite3.connect(self.path) as c: rows=c.execute("SELECT payload_json FROM assessments ORDER BY assessed_ns,hypothesis_id").fetchall()
        return tuple(ThesisAssessment(**_loads(r[0])) for r in rows)

    def load_transitions(self)->tuple[LifecycleTransition,...]:
        with sqlite3.connect(self.path) as c: rows=c.execute("SELECT payload_json FROM transitions ORDER BY occurred_ns,hypothesis_id,to_status").fetchall()
        return tuple(LifecycleTransition(**_loads(r[0])) for r in rows)

    def load_plans(self)->tuple[dict[str,Any],...]:
        with sqlite3.connect(self.path) as c: rows=c.execute("SELECT payload_json FROM research_plans ORDER BY created_ns,plan_id").fetchall()
        return tuple(_loads(r[0]) for r in rows)

    def load_plan_tasks(self)->dict[str,dict[str,Any]]:
        with sqlite3.connect(self.path) as c: rows=c.execute("SELECT job_id,payload_json FROM plan_tasks ORDER BY job_id").fetchall()
        return {job_id:_loads(raw) for job_id,raw in rows}

    def load_job_evidence_links(self)->dict[str,tuple[str,str,int]]:
        with sqlite3.connect(self.path) as c: rows=c.execute("SELECT job_id,evidence_id,claim,received_ns FROM job_evidence ORDER BY received_ns,job_id").fetchall()
        return {job_id:(evidence_id,claim,int(received_ns)) for job_id,evidence_id,claim,received_ns in rows}

    def queued_job_ids(self)->tuple[str,...]:
        with sqlite3.connect(self.path) as c: rows=c.execute("SELECT job_id FROM jobs WHERE status=? ORDER BY created_ns,job_id",(JobStatus.QUEUED.value,)).fetchall()
        return tuple(r[0] for r in rows)
