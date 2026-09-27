from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from .budget import BudgetLedger, ResearchBudget
from .contracts import EvidenceRecord, FinancialState, Hypothesis, HypothesisStatus, JobStatus, PromotionEvidence, digest
from .dedup import HypothesisDeduplicator
from .engine import OracleEngine
from .hypothesis_factory import Trigger, from_anomaly
from .journal import CommandRecord, LoopJournal, replay_and_verify
from .outbox import ResearchOutbox, ResearchPacket
from .plans import PlanTask, ResearchPlan, default_research_plan
from .requests import OutboundResearchRequest, build_request
from .counterfactual import CounterfactualSpec
from .runtime import AttemptRecord, JobRuntime, RetryPolicy
from .lifecycle import promotion_stages

@dataclass(frozen=True, slots=True)
class DispatchBatch:
    decision_ns: int
    requests: tuple[OutboundResearchRequest, ...]
    blocked: tuple[tuple[str, str], ...] = ()
    @property
    def batch_hash(self) -> str:
        return digest({"decision_ns": self.decision_ns, "requests": [r.request_id for r in self.requests], "blocked": self.blocked})

class AutonomousResearchLoop:
    """Bounded deterministic automation around ORACLE's research plane.

    It can schedule, persist, retry and assess research. It has no broker/order
    methods and cannot authorize production.
    """
    def __init__(
        self,
        engine: OracleEngine,
        *,
        budget: ResearchBudget | None = None,
        retry_policy: RetryPolicy | None = None,
        dedup_cooldown_ns: int = 3_600_000_000_000,
        journal_path: Path | None = None,
    ):
        self.engine = engine
        self.budget = BudgetLedger(budget or ResearchBudget(100.0))
        self.runtime = JobRuntime(retry_policy or RetryPolicy())
        self.dedup = HypothesisDeduplicator(cooldown_ns=dedup_cooldown_ns)
        self.journal = LoopJournal(journal_path)
        self.outbox = ResearchOutbox(engine.store.path)
        self.plans: dict[str, ResearchPlan] = {}
        self.task_by_job: dict[str, PlanTask] = {}
        self.latest_state: FinancialState | None = None
        self.evidence_by_job: dict[str, EvidenceRecord] = {}
        self._last_duplicate = False
        self._restore_durable_state()

    def set_financial_state(self, state: FinancialState) -> None:
        if self.latest_state is not None and state.decision_ns < self.latest_state.decision_ns:
            raise ValueError("financial state cannot move backwards")
        self.engine.store.add_financial_state(state)
        self.latest_state = state

    @staticmethod
    def _restore_task(raw: dict[str, Any]) -> PlanTask:
        raw=dict(raw)
        raw["required_states"]=tuple(raw.get("required_states", ()))
        return PlanTask(**raw)

    @staticmethod
    def _restore_attack(raw: dict[str, Any]) -> CounterfactualSpec:
        raw=dict(raw)
        raw["removals"]=tuple(raw.get("removals", ()))
        return CounterfactualSpec(**raw)

    def _restore_durable_state(self) -> None:
        """Rehydrate automation state from durable ORACLE tables + outbox.

        The relational store is authoritative for owned research state. The hash
        journal remains an independent replay/audit mechanism, not the only way
        to recover a live process.
        """
        task_raw=self.engine.store.load_plan_tasks()
        for raw in self.engine.store.load_plans():
            data=dict(raw)
            tasks=tuple(self._restore_task(x) for x in data.get("tasks", ()))
            attacks=tuple(self._restore_attack(x) for x in data.get("attack_suite", ()))
            plan=ResearchPlan(data["plan_id"],data["hypothesis_id"],int(data["created_ns"]),tasks,attacks,bool(data.get("production_authorized",False)))
            self.plans[plan.hypothesis_id]=plan
            h=self.engine.hypotheses.get(plan.hypothesis_id)
            if h is not None:
                q=self.engine.exchange.open(h,requested_kinds=plan.required_evidence_kinds)
                self.engine.question_by_hypothesis[h.hypothesis_id]=q.question_id
        for job_id,raw in task_raw.items():
            self.task_by_job[job_id]=self._restore_task(raw)

        links=self.engine.store.load_job_evidence_links()
        for job_id,(evidence_id,claim,received_ns) in links.items():
            evidence=self.engine.evidence_records.get(evidence_id)
            job=self.engine.scheduler._jobs.get(job_id)
            if evidence is None or job is None:
                raise ValueError("durable job/evidence link is orphaned")
            self.evidence_by_job[job_id]=evidence
            qid=self.engine.question_by_hypothesis.get(job.hypothesis_id)
            if qid is None:
                q=self.engine.exchange.open(self.engine.hypotheses[job.hypothesis_id])
                qid=q.question_id; self.engine.question_by_hypothesis[job.hypothesis_id]=qid
            self.engine.exchange.contribute(qid,system=evidence.source_system,evidence=evidence,claim=claim,submitted_ns=received_ns)

        for h in sorted(self.engine.hypotheses.values(),key=lambda x:(x.created_ns,x.hypothesis_id)):
            self.dedup.consider(h)

        # Reconstruct compute attempts from persist-before-send packets. One packet
        # is one ORACLE research attempt; a retry creates a new packet identity.
        for job_id,job in sorted(self.engine.scheduler._jobs.items(),key=lambda kv:(kv[1].created_ns,kv[0])):
            packets=[p for p in self.outbox.packets_for_job(job_id) if self.outbox.dispatches.get(p.packet_id)]
            packets.sort(key=lambda p:(self.outbox.dispatches[p.packet_id][0].dispatched_ns,p.packet_id))
            for attempt_no,packet in enumerate(packets,1):
                first=self.outbox.dispatches[packet.packet_id][0]
                acked=next((r.acked_ns for r in self.outbox.dispatches[packet.packet_id] if r.acked_ns is not None),None)
                if acked is not None:
                    status=JobStatus.COMPLETED.value; finished=acked; error=None
                elif packet.packet_id in self.outbox.failed:
                    status=JobStatus.FAILED.value; finished=self.outbox.failed[packet.packet_id]; error=self.outbox.failure_codes.get(packet.packet_id,"RECOVERED_FAILURE")
                else:
                    status=JobStatus.CLAIMED.value; finished=None; error=None
                rec=AttemptRecord("ATT-"+digest({"job":job_id,"attempt":attempt_no,"started_ns":first.dispatched_ns})[:20],job_id,attempt_no,first.dispatched_ns,finished,status,error)
                self.runtime.restore_attempt(rec)
                self.budget.restore_reservation(job,active=status==JobStatus.CLAIMED.value)
            if job_id in links:
                self.runtime.completed.add(job_id)
                self.runtime.next_eligible_ns.pop(job_id,None)
                self.runtime.dead_letter.pop(job_id,None)

        self.latest_state=self.engine.store.load_latest_financial_state()

    def submit_trigger(self, trigger: Trigger, *, horizon: str = "60m", sensors: tuple[str, ...] = (), _record: bool = True) -> Hypothesis:
        candidate = from_anomaly(trigger, horizon=horizon)
        d = self.dedup.consider(candidate)
        self._last_duplicate = d.duplicate
        if d.duplicate:
            h = self.engine.hypotheses[d.canonical_hypothesis_id]
        else:
            h = self.engine.ingest_trigger(trigger, horizon=horizon)
            self._plan(h, sensors=sensors)
            self.engine.transition_hypothesis(h.hypothesis_id, HypothesisStatus.QUEUED.value, occurred_ns=trigger.decision_ns, reason="AUTONOMOUS_RESEARCH_PLAN_CREATED")
        if _record:
            self.journal.append("submit_trigger", trigger.decision_ns, {"trigger": asdict(trigger), "horizon": horizon, "sensors": list(sensors)}, self._hyp_result(h, d.duplicate))
        return h

    def _plan(self, h: Hypothesis, *, sensors: tuple[str, ...]) -> ResearchPlan:
        p = default_research_plan(h, sensors=sensors)
        self.plans[h.hypothesis_id] = p
        self.engine.set_research_requirements(h.hypothesis_id, p.required_evidence_kinds)
        task_map: dict[str, PlanTask] = {}
        for t in p.tasks:
            j = self.engine.create_research_job(
                h.hypothesis_id,
                now_ns=h.created_ns,
                task_type=t.task_type,
                expected_information_gain=t.expected_information_gain,
                strategic_relevance=t.strategic_relevance,
                evidence_deficit=t.evidence_deficit,
                novelty=t.novelty,
                estimated_compute_cost=t.estimated_compute_cost,
                required_systems=(t.system,),
                required_states=t.required_states,
            )
            self.task_by_job[j.job_id] = t
            task_map[j.job_id] = t
        self.engine.store.add_plan(p, task_map)
        self.engine.ledger.append("research_plan.created", h.created_ns, {"plan_id": p.plan_id, "hypothesis_id": h.hypothesis_id, "plan_hash": p.plan_hash, "task_count": len(p.tasks), "attack_count": len(p.attack_suite)})
        return p

    @staticmethod
    def _packet(req: OutboundResearchRequest) -> ResearchPacket:
        lineage = digest({"request_id": req.request_id, "schema": req.schema, "payload": req.payload})
        pid = "PKT-" + digest({"request_id": req.request_id, "target": req.target_system, "lineage": lineage})[:20]
        return ResearchPacket(pid, req.job_id, req.hypothesis_id, req.target_system, req.emitted_ns, req.schema, dict(req.payload), lineage, False)

    def dispatch(self, decision_ns: int, *, max_requests: int | None = None, priority_multipliers: dict[str,float] | None = None, _record: bool = True) -> DispatchBatch:
        if decision_ns < 0:
            raise ValueError("decision_ns must be non-negative")
        out: list[OutboundResearchRequest] = []
        blocked: list[tuple[str, str]] = []
        for job in self.engine.scheduler.rank(decision_ns,multipliers=priority_multipliers):
            if max_requests is not None and len(out) >= max_requests:
                break
            if not self.runtime.can_claim(job.job_id, decision_ns):
                continue
            bd = self.budget.reserve(job)
            if not bd.allowed:
                blocked.append((job.job_id, bd.reason))
                continue
            self.runtime.claim(job.job_id, decision_ns)
            task = self.task_by_job.get(job.job_id)
            req = build_request(job, self.engine.hypotheses[job.hypothesis_id], emitted_ns=decision_ns, state=self.latest_state, task_payload=task.payload if task else None)
            packet = self.outbox.enqueue(self._packet(req))  # persist before send
            self.outbox.dispatch(packet.packet_id, decision_ns)
            out.append(req)
            self.engine.ledger.append("research_job.dispatched", decision_ns, {"job_id": job.job_id, "request_id": req.request_id, "packet_id": packet.packet_id, "system": req.target_system})
            if self.engine.status[job.hypothesis_id] is HypothesisStatus.QUEUED:
                self.engine.transition_hypothesis(job.hypothesis_id, HypothesisStatus.TESTING.value, occurred_ns=decision_ns, reason="FIRST_RESEARCH_JOB_DISPATCHED")
        batch = DispatchBatch(decision_ns, tuple(out), tuple(blocked))
        if _record:
            self.journal.append("dispatch", decision_ns, {"max_requests": max_requests, "priority_multipliers": dict(sorted((priority_multipliers or {}).items()))}, self._batch_result(batch))
        return batch

    def _ack_job_packets(self, job_id: str, acked_ns: int) -> None:
        for packet in self.outbox.packets_for_job(job_id):
            if self.outbox.is_acked(packet.packet_id) or packet.packet_id in self.outbox.failed:
                continue
            rows = self.outbox.dispatches.get(packet.packet_id, ())
            if rows and acked_ns >= rows[-1].dispatched_ns:
                self.outbox.acknowledge(packet.packet_id, acked_ns)

    def ingest_evidence(self, job_id: str, evidence: EvidenceRecord, *, claim: str, received_ns: int, _record: bool = True) -> EvidenceRecord:
        job = self._job(job_id)
        prior = self.evidence_by_job.get(job_id)
        if job_id in self.runtime.completed:
            if prior is not None and prior.immutable_hash == evidence.immutable_hash:
                return prior
            raise ValueError("completed job received conflicting evidence")
        if evidence.hypothesis_id != job.hypothesis_id:
            raise ValueError("evidence hypothesis/job mismatch")
        if evidence.source_system.upper() not in {s.upper() for s in job.required_systems}:
            raise ValueError("evidence source does not match dispatched system")
        task = self.task_by_job.get(job_id)
        if task is not None and evidence.kind != task.evidence_kind:
            raise ValueError(f"evidence kind mismatch: expected {task.evidence_kind}, got {evidence.kind}")
        self.engine.contribute_for_job(job_id, job.hypothesis_id, evidence, claim=claim, submitted_ns=received_ns)
        self.runtime.complete(job_id, received_ns)
        self.budget.release(job)
        self.evidence_by_job[job_id] = evidence
        self._ack_job_packets(job_id, received_ns)
        self.engine.ledger.append("research_job.completed", received_ns, {"job_id": job_id, "evidence_id": evidence.evidence_id, "evidence_hash": evidence.immutable_hash})
        self._maybe_auto_assess(job.hypothesis_id, received_ns)
        if _record:
            self.journal.append("ingest_evidence", received_ns, {"job_id": job_id, "evidence": asdict(evidence), "claim": claim}, evidence.immutable_hash)
        return evidence

    def fail_job(self, job_id: str, *, failed_ns: int, error_code: str, _record: bool = True) -> str:
        job = self._job(job_id)
        a = self.runtime.fail(job_id, failed_ns, error_code)
        self.budget.release(job)
        # A failed sibling attempt is terminal for that exact packet. A retry gets a
        # new packet id, so late/duplicate delivery can never masquerade as the retry.
        packets = self.outbox.packets_for_job(job_id)
        for packet in reversed(packets):
            if not self.outbox.is_acked(packet.packet_id) and packet.packet_id not in self.outbox.failed:
                self.outbox.mark_failed(packet.packet_id, failed_ns, error_code)
                break
        outcome = "DEAD_LETTER" if job_id in self.runtime.dead_letter else "RETRY_SCHEDULED"
        self.engine.ledger.append("research_job.failed", failed_ns, {"job_id": job_id, "attempt": a.attempt, "error_code": a.error_code, "outcome": outcome, "retry_at": self.runtime.next_eligible_ns.get(job_id)})
        if _record:
            self.journal.append("fail_job", failed_ns, {"job_id": job_id, "error_code": error_code}, outcome)
        return outcome

    def _required_complete(self, hypothesis_id: str) -> bool:
        plan = self.plans.get(hypothesis_id)
        if plan is None:
            return False
        required_jobs = {
            jid for jid, task in self.task_by_job.items()
            if self._job(jid).hypothesis_id == hypothesis_id and task.required
        }
        return bool(required_jobs) and required_jobs.issubset(self.runtime.completed)

    def _evidence_for_hypothesis(self, hypothesis_id: str) -> tuple[EvidenceRecord, ...]:
        return tuple(e for jid, e in self.evidence_by_job.items() if self._job(jid).hypothesis_id == hypothesis_id)

    @staticmethod
    def _explicit_metric(rows: tuple[EvidenceRecord, ...], system: str, keys: tuple[str, ...], default: float) -> float:
        vals: list[float] = []
        for e in rows:
            if e.source_system.upper() != system:
                continue
            for key in keys:
                raw = e.payload.get(key)
                if isinstance(raw, (int, float)) and 0.0 <= float(raw) <= 1.0:
                    vals.append(float(raw)); break
        return sum(vals) / len(vals) if vals else default

    def _maybe_auto_assess(self, hypothesis_id: str, assessed_ns: int):
        if hypothesis_id in self.engine.assessments or not self._required_complete(hypothesis_id):
            return None
        rows = self._evidence_for_hypothesis(hypothesis_id)
        # Missing explicit supervisory/scientific metrics are penalized rather than
        # invented. Evidence support/coverage is still computed by ResearchExchange.
        robustness = self._explicit_metric(rows, "DAEDALUS", ("robustness_score", "holdout_score"), 0.0)
        regime_fit = self._explicit_metric(rows, "ATHENA", ("regime_fit",), 0.0)
        ood_risk = self._explicit_metric(rows, "ATHENA", ("ood_risk", "ood_score"), 1.0)
        data_rows = tuple(e for e in rows if e.source_system.upper() in {"NEXUS", "AION"})
        data_confidence = sum(e.strength for e in data_rows) / len(data_rows) if data_rows else 0.0
        a = self.engine.assess(hypothesis_id, assessed_ns=assessed_ns, robustness_score=robustness, regime_fit=regime_fit, data_confidence=data_confidence, ood_risk=ood_risk)
        self.engine.ledger.append("thesis.auto_assessed", assessed_ns, {"hypothesis_id": hypothesis_id, "thesis_health": a.thesis_health, "evidence_ids": a.evidence_ids, "reason_codes": a.reason_codes})
        return a

    def assess(self, hypothesis_id: str, *, assessed_ns: int, robustness_score: float = 0, regime_fit: float = 0, data_confidence: float = 0, ood_risk: float = 0, _record: bool = True):
        a = self.engine.assess(hypothesis_id, assessed_ns=assessed_ns, robustness_score=robustness_score, regime_fit=regime_fit, data_confidence=data_confidence, ood_risk=ood_risk)
        if _record:
            self.journal.append("assess", assessed_ns, {"hypothesis_id": hypothesis_id, "robustness_score": robustness_score, "regime_fit": regime_fit, "data_confidence": data_confidence, "ood_risk": ood_risk}, asdict(a))
        return a

    def apply_promotion_evidence(self, hypothesis_id: str, evidence: PromotionEvidence, *, occurred_ns: int, evidence_ids: tuple[str, ...] = ()):
        if hypothesis_id not in self.engine.hypotheses:
            raise KeyError(hypothesis_id)
        stages, reasons = promotion_stages(self.engine.status[hypothesis_id].value, evidence)
        transitions = []
        for stage in stages:
            transitions.append(self.engine.transition_hypothesis(
                hypothesis_id,
                stage.value,
                occurred_ns=occurred_ns,
                reason="EXTERNAL_PROMOTION_EVIDENCE",
                evidence_ids=evidence_ids,
            ))
        self.engine.ledger.append("promotion_evidence.applied", occurred_ns, {
            "hypothesis_id": hypothesis_id,
            "stages": [x.value for x in stages],
            "blocked_reasons": reasons,
            "production_authorized": False,
        })
        return tuple(transitions), reasons

    @classmethod
    def recover_from_journal(
        cls,
        engine: OracleEngine,
        journal_path: Path,
        *,
        budget: ResearchBudget | None = None,
        retry_policy: RetryPolicy | None = None,
        dedup_cooldown_ns: int = 3_600_000_000_000,
    ) -> "AutonomousResearchLoop":
        """Recover from durable state and independently audit it against the journal.

        Recovery itself comes from the relational store + transactional outbox. The
        command journal is replayed into an isolated temporary ORACLE instance and
        compared with the durable state, so verification cannot mutate the database
        being recovered.
        """
        import tempfile
        source = LoopJournal(journal_path)
        recovered = cls(engine, budget=budget, retry_policy=retry_policy, dedup_cooldown_ns=dedup_cooldown_ns, journal_path=None)
        with tempfile.TemporaryDirectory(prefix="oracle-recovery-audit-") as td:
            shadow = cls(OracleEngine(Path(td) / "oracle.db"), budget=budget, retry_policy=retry_policy, dedup_cooldown_ns=dedup_cooldown_ns, journal_path=None)
            holder = object.__new__(cls)
            holder.journal = source
            holder.replay_into(shadow)
            if set(shadow.outbox.packets) != set(recovered.outbox.packets):
                raise ValueError("durable outbox packet set does not match journal replay")
            for pid, packet in shadow.outbox.packets.items():
                durable_packet=recovered.outbox.packets[pid]
                if durable_packet.packet_hash != packet.packet_hash:
                    raise ValueError("durable outbox packet hash mismatch")
                if shadow.outbox.failed.get(pid) != recovered.outbox.failed.get(pid):
                    raise ValueError("durable outbox failed-state mismatch")
                if shadow.outbox.failure_codes.get(pid) != recovered.outbox.failure_codes.get(pid):
                    raise ValueError("durable outbox failure-code mismatch")
                sdispatch=[(x.dispatched_ns,x.acked_ns) for x in shadow.outbox.dispatches.get(pid,())]
                ddispatch=[(x.dispatched_ns,x.acked_ns) for x in recovered.outbox.dispatches.get(pid,())]
                if sdispatch != ddispatch:
                    raise ValueError("durable outbox dispatch/ack state mismatch")
            if set(shadow.engine.hypotheses) != set(recovered.engine.hypotheses):
                raise ValueError("durable hypothesis set does not match journal replay")
            if set(shadow.engine.scheduler._jobs) != set(recovered.engine.scheduler._jobs):
                raise ValueError("durable job set does not match journal replay")
            if shadow.runtime.completed != recovered.runtime.completed or shadow.runtime.dead_letter != recovered.runtime.dead_letter:
                raise ValueError("durable runtime terminal state does not match journal replay")
            if abs(shadow.budget.consumed_compute-recovered.budget.consumed_compute)>1e-12:
                raise ValueError("durable compute ledger does not match journal replay")
        recovered.journal = source
        return recovered

    def _job(self, job_id: str):
        try:
            return self.engine.scheduler._jobs[job_id]
        except KeyError:
            raise KeyError(job_id) from None

    @staticmethod
    def _hyp_result(h: Hypothesis, duplicate: bool) -> dict[str, Any]:
        return {"hypothesis_id": h.hypothesis_id, "spec_hash": h.spec_hash, "duplicate": duplicate}

    @staticmethod
    def _batch_result(b: DispatchBatch) -> dict[str, Any]:
        return {"batch_hash": b.batch_hash, "request_ids": [r.request_id for r in b.requests], "blocked": list(b.blocked)}

    def replay_into(self, other: "AutonomousResearchLoop") -> tuple[str, ...]:
        """Replay external commands into a clean loop and verify deterministic results."""
        def apply(r: CommandRecord):
            p = r.payload
            if r.command == "submit_trigger":
                t = Trigger(**p["trigger"])
                h = other.submit_trigger(t, horizon=p["horizon"], sensors=tuple(p["sensors"]), _record=False)
                return other._hyp_result(h, other._last_duplicate)
            if r.command == "dispatch":
                return other._batch_result(other.dispatch(r.event_ns, max_requests=p["max_requests"], priority_multipliers=dict(p.get("priority_multipliers",{})), _record=False))
            if r.command == "ingest_evidence":
                e = EvidenceRecord(**p["evidence"])
                other.ingest_evidence(p["job_id"], e, claim=p["claim"], received_ns=r.event_ns, _record=False)
                return e.immutable_hash
            if r.command == "fail_job":
                return other.fail_job(p["job_id"], failed_ns=r.event_ns, error_code=p["error_code"], _record=False)
            if r.command == "assess":
                return asdict(other.assess(p["hypothesis_id"], assessed_ns=r.event_ns, robustness_score=p["robustness_score"], regime_fit=p["regime_fit"], data_confidence=p["data_confidence"], ood_risk=p["ood_risk"], _record=False))
            raise ValueError(f"unsupported replay command {r.command}")
        return replay_and_verify(self.journal.records(), apply)
