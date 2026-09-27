from __future__ import annotations
from pathlib import Path
from .contracts import HypothesisStatus
from .orchestrator import OracleCoordinator
from .state_graph import Edge
from .store import OracleStore

class OracleEngine(OracleCoordinator):
    def __init__(self,db_path:Path):
        super().__init__()
        self.store=OracleStore(db_path)
        self.evidence_records={}
        self._hydrate_from_store()

    def _hydrate_from_store(self)->None:
        hypotheses=self.store.load_hypotheses()
        if not hypotheses:
            return
        for h in hypotheses:
            self.hypotheses[h.hypothesis_id]=h
            self.status[h.hypothesis_id]=HypothesisStatus(h.status)
            self.graph.upsert_node(h.hypothesis_id,"hypothesis",family=h.family,target=h.target,status=h.status,spec_hash=h.spec_hash)
            target=f"target:{h.target}"
            self.graph.upsert_node(target,"target",target=h.target)
            self.graph.add_edge(Edge(h.hypothesis_id,target,"investigates",1,0,h.created_ns))
            q=self.exchange.open(h)
            self.question_by_hypothesis[h.hypothesis_id]=q.question_id
        for j in self.store.load_jobs():
            self.scheduler.submit(j)
            self.graph.upsert_node(j.job_id,"research_job",task_type=j.task_type,status=j.status)
            self.graph.add_edge(Edge(j.hypothesis_id,j.job_id,"requires",1,0,j.created_ns))
        for e in self.store.load_evidence():
            self.evidence_records[e.evidence_id]=e
            self.graph.upsert_node(e.evidence_id,"evidence",evidence_kind=e.kind,source=e.source_system,hash=e.immutable_hash)
            self.graph.add_edge(Edge(e.hypothesis_id,e.evidence_id,"evidence",e.strength,0,e.observed_ns))
        for t in self.store.load_transitions():
            self.status[t.hypothesis_id]=HypothesisStatus(t.to_status)
            node=self.graph.nodes.get(t.hypothesis_id)
            attrs=dict(node.attrs) if node else {}
            attrs["status"]=t.to_status
            self.graph.upsert_node(t.hypothesis_id,"hypothesis",**attrs)
        for a in self.store.load_assessments():
            self.assessments[a.hypothesis_id]=a

    def ingest_trigger(self,*args,**kwargs):
        h=super().ingest_trigger(*args,**kwargs); self.store.add_hypothesis(h); return h
    def create_research_job(self,*args,**kwargs):
        j=super().create_research_job(*args,**kwargs); self.store.add_job(j); return j
    def contribute(self,hypothesis_id,evidence,*,claim,submitted_ns):
        super().contribute(hypothesis_id,evidence,claim=claim,submitted_ns=submitted_ns)
        self.store.add_evidence(evidence); self.evidence_records[evidence.evidence_id]=evidence
    def contribute_for_job(self,job_id,hypothesis_id,evidence,*,claim,submitted_ns):
        # Persist evidence + job ownership atomically before mutating in-memory state.
        self.store.add_evidence_for_job(job_id,evidence,claim=claim,received_ns=submitted_ns)
        super().contribute(hypothesis_id,evidence,claim=claim,submitted_ns=submitted_ns)
        self.evidence_records[evidence.evidence_id]=evidence
    def transition_hypothesis(self,*args,**kwargs):
        t=super().transition_hypothesis(*args,**kwargs); self.store.add_transition(t); return t
    def assess(self,*args,**kwargs):
        a=super().assess(*args,**kwargs); self.store.add_assessment(a); return a
