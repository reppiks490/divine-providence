from __future__ import annotations
from .contracts import EvidenceRecord, Hypothesis, HypothesisStatus, ResearchJob, ThesisAssessment, digest
from .exchange import ResearchExchange, ResearchQuestion
from .hypothesis_factory import Trigger, from_anomaly
from .ledger import AuditLedger
from .scheduler import ResearchScheduler
from .lifecycle import transition
from .state_graph import KnowledgeGraph, Edge

class OracleCoordinator:
    """Deterministic Financial/Research coordinator. Never owns execution authority."""
    def __init__(self):
        self.ledger = AuditLedger()
        self.scheduler = ResearchScheduler()
        self.graph = KnowledgeGraph()
        self.exchange = ResearchExchange()
        self.hypotheses: dict[str, Hypothesis] = {}
        self.status: dict[str, HypothesisStatus] = {}
        self.assessments: dict[str, ThesisAssessment] = {}
        self.question_by_hypothesis: dict[str, str] = {}

    def ingest_trigger(self, trigger: Trigger, *, horizon: str = "60m") -> Hypothesis:
        h = from_anomaly(trigger, horizon=horizon)
        if h.hypothesis_id in self.hypotheses:
            return self.hypotheses[h.hypothesis_id]
        self.hypotheses[h.hypothesis_id] = h
        self.status[h.hypothesis_id] = HypothesisStatus.DISCOVERED
        self.graph.upsert_node(h.hypothesis_id, "hypothesis", family=h.family, target=h.target, status=h.status, spec_hash=h.spec_hash)
        target = f"target:{h.target}"
        self.graph.upsert_node(target, "target", target=h.target)
        self.graph.add_edge(Edge(h.hypothesis_id, target, "investigates", 1, 0, h.created_ns))
        q = self.exchange.open(h)
        self.question_by_hypothesis[h.hypothesis_id] = q.question_id
        self.ledger.append("hypothesis.discovered", h.created_ns, {"hypothesis_id": h.hypothesis_id, "spec_hash": h.spec_hash})
        return h

    def set_research_requirements(self, hypothesis_id: str, requested_kinds: tuple[str, ...]) -> ResearchQuestion:
        if hypothesis_id not in self.hypotheses:
            raise KeyError(hypothesis_id)
        kinds = tuple(sorted({str(x) for x in requested_kinds if str(x)}))
        if not kinds:
            raise ValueError("requested evidence kinds required")
        q = self.exchange.open(self.hypotheses[hypothesis_id], requested_kinds=kinds)
        self.question_by_hypothesis[hypothesis_id] = q.question_id
        self.ledger.append("research_question.requirements", self.hypotheses[hypothesis_id].created_ns, {"hypothesis_id": hypothesis_id, "question_id": q.question_id, "requested_kinds": kinds})
        return q

    def _question_id(self, hypothesis_id: str) -> str:
        qid = self.question_by_hypothesis.get(hypothesis_id)
        if qid:
            return qid
        q = self.exchange.open(self.hypotheses[hypothesis_id])
        self.question_by_hypothesis[hypothesis_id] = q.question_id
        return q.question_id

    def create_research_job(self, hypothesis_id: str, *, now_ns: int, task_type: str, expected_information_gain: float, strategic_relevance: float, evidence_deficit: float, novelty: float, estimated_compute_cost: float, required_systems: tuple[str, ...], required_states: tuple[str, ...] = ()) -> ResearchJob:
        if hypothesis_id not in self.hypotheses:
            raise KeyError(hypothesis_id)
        impact = min(1.0, self.graph.downstream_impact(hypothesis_id, now_ns) / 10)
        jid = "JOB-" + digest({"hypothesis_id": hypothesis_id, "now_ns": now_ns, "task_type": task_type, "systems": required_systems, "states": required_states})[:20]
        j = ResearchJob(
            job_id=jid,
            hypothesis_id=hypothesis_id,
            task_type=task_type,
            created_ns=now_ns,
            expected_information_gain=expected_information_gain,
            strategic_relevance=strategic_relevance,
            evidence_deficit=evidence_deficit,
            dependency_impact=impact,
            novelty=novelty,
            estimated_compute_cost=estimated_compute_cost,
            required_systems=required_systems,
            required_states=required_states,
        )
        self.scheduler.submit(j)
        self.graph.upsert_node(j.job_id, "research_job", task_type=task_type, status=j.status)
        self.graph.add_edge(Edge(hypothesis_id, j.job_id, "requires", 1, 0, now_ns))
        self.ledger.append("research_job.queued", now_ns, {"job_id": jid, "hypothesis_id": hypothesis_id})
        return j

    def contribute(self, hypothesis_id: str, evidence: EvidenceRecord, *, claim: str, submitted_ns: int) -> None:
        qid = self._question_id(hypothesis_id)
        self.exchange.contribute(qid, system=evidence.source_system, evidence=evidence, claim=claim, submitted_ns=submitted_ns)
        self.graph.upsert_node(evidence.evidence_id, "evidence", evidence_kind=evidence.kind, source=evidence.source_system, hash=evidence.immutable_hash)
        self.graph.add_edge(Edge(hypothesis_id, evidence.evidence_id, "evidence", evidence.strength, 0, submitted_ns))
        self.ledger.append("evidence.contributed", submitted_ns, {"hypothesis_id": hypothesis_id, "evidence_id": evidence.evidence_id, "hash": evidence.immutable_hash})

    def assess(self, hypothesis_id: str, *, assessed_ns: int, robustness_score: float = 0, regime_fit: float = 0, data_confidence: float = 0, ood_risk: float = 0) -> ThesisAssessment:
        qid = self._question_id(hypothesis_id)
        a = self.exchange.assess(qid, assessed_ns=assessed_ns, robustness_score=robustness_score, regime_fit=regime_fit, data_confidence=data_confidence, ood_risk=ood_risk)
        self.assessments[hypothesis_id] = a
        self.ledger.append("thesis.assessed", assessed_ns, {"hypothesis_id": hypothesis_id, "thesis_health": a.thesis_health, "reason_codes": a.reason_codes})
        return a

    def transition_hypothesis(self, hypothesis_id: str, to_status: str, *, occurred_ns: int, reason: str, evidence_ids: tuple[str, ...] = ()):
        if hypothesis_id not in self.hypotheses:
            raise KeyError(hypothesis_id)
        current = self.status[hypothesis_id].value
        t = transition(hypothesis_id, current, to_status, occurred_ns, reason, evidence_ids)
        self.status[hypothesis_id] = HypothesisStatus(to_status)
        node = self.graph.nodes.get(hypothesis_id)
        attrs = dict(node.attrs) if node else {}
        attrs["status"] = to_status
        self.graph.upsert_node(hypothesis_id, "hypothesis", **attrs)
        self.ledger.append("hypothesis.transition", occurred_ns, {"hypothesis_id": hypothesis_id, "from": current, "to": to_status, "reason": reason, "evidence_ids": evidence_ids})
        return t
