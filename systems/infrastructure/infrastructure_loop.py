
from __future__ import annotations

import asyncio
import dataclasses
import enum
import hashlib
import json
import math
import random
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Deque, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, Tuple

from topology_governor import BlastRadiusGovernor, MutationLeaseManager, TopologyModel
from canary_executor import CanaryStatus, StagedCanaryExecutor
from attribution import CounterfactualAttributor
from evidence_provider import EvidenceRequest, ReadOnlyEvidenceCollector
from source_receipts import DecisionReceipt, SourceNativeEnvelopeAssembler
from proof_envelope import ProofEnvelopeVerifier
from mutation_receipt import MutationLifecycleRecorder
from proof_journal import ProofJournalTransaction, ProofJournalReplayVerifier
from durable_journal import DurableProofJournal
from recovery_policy import StartupRecoveryPolicy
from recovery_checkpoint import RecoveryCheckpoint, AtomicRecoveryCheckpointStore
from recovery_continuity import RecoveryContinuityVerifier
from recovery_chain import AppendOnlyRecoveryChain, AuthenticatedRecoveryChain
from recovery_lock import RecoveryChainLock
from recovery_transaction import RecoveryDualChainCoordinator


# ============================================================
# Core types
# ============================================================

class Severity(str, enum.Enum):
    INFO = "info"
    WARN = "warn"
    CRITICAL = "critical"


class ActionClass(str, enum.Enum):
    OBSERVE = "observe"       # no mutation
    TUNE = "tune"             # reversible configuration changes
    RESTART = "restart"       # restart/reload a component
    SCALE = "scale"           # change capacity
    ROUTE = "route"           # alter traffic/task routing
    REPAIR = "repair"         # corrective mutation
    ISOLATE = "isolate"       # quarantine a component/path
    ROLLBACK = "rollback"     # return to prior known-good state


@dataclass(frozen=True)
class Signal:
    source: str
    metric: str
    value: float
    ts: float = field(default_factory=time.time)
    tags: Mapping[str, str] = field(default_factory=dict)


@dataclass
class HealthReport:
    component: str
    score: float                  # 0..1
    confidence: float             # 0..1
    symptoms: List[str] = field(default_factory=list)
    evidence: Dict[str, float] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)


@dataclass
class ProposedAction:
    component: str
    action_class: ActionClass
    name: str
    payload: Dict[str, Any]
    expected_gain: float          # normalized utility delta
    estimated_risk: float         # 0..1
    reversibility: float          # 0..1
    confidence: float             # 0..1
    reason: str
    fingerprint: str = ""

    def finalize(self) -> "ProposedAction":
        raw = json.dumps(
            {
                "component": self.component,
                "class": self.action_class.value,
                "name": self.name,
                "payload": self.payload,
            },
            sort_keys=True,
            default=str,
        ).encode()
        self.fingerprint = hashlib.sha256(raw).hexdigest()[:16]
        return self


@dataclass
class ActionResult:
    action: ProposedAction
    success: bool
    before_score: float
    after_score: float
    latency_ms: float
    rolled_back: bool = False
    message: str = ""
    causal_eligible: bool = False
    evidence_hash: str = ""
    attribution_eligible: bool = False
    attribution_hash: str = ""
    proof_envelope_hash: str = ""
    intervention_id: str = ""
    mutation_receipt_hash: str = ""
    ts: float = field(default_factory=time.time)

    @property
    def realized_gain(self) -> float:
        return self.after_score - self.before_score


# ============================================================
# Adapter boundary: the loop surrounds infrastructure through
# adapters instead of hard-coding itself into each subsystem.
# ============================================================

class InfraAdapter(Protocol):
    name: str

    async def collect_signals(self) -> Sequence[Signal]:
        ...

    async def health(self) -> HealthReport:
        ...

    async def snapshot(self) -> Dict[str, Any]:
        ...

    async def execute(self, action: ProposedAction) -> Tuple[bool, str]:
        ...

    async def rollback(self, snapshot: Dict[str, Any], action: ProposedAction) -> Tuple[bool, str]:
        ...


# ============================================================
# Memory / online learning
# ============================================================

class OutcomeMemory:
    """
    Tiny online learner over action fingerprints and action families.

    It does NOT directly mutate infrastructure. It only adjusts expected
    utility / confidence used by the planner. This makes learning advisory
    rather than authoritative.
    """

    def __init__(self, window: int = 200):
        self.window = window
        self.by_key: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=window))
        self.failures: Dict[str, int] = defaultdict(int)
        self.successes: Dict[str, int] = defaultdict(int)

    @staticmethod
    def key(a: ProposedAction) -> str:
        return f"{a.component}|{a.action_class.value}|{a.name}"

    def update(self, result: ActionResult) -> None:
        k = self.key(result.action)
        # Positive utility learning requires proof-carrying causal eligibility.
        # Uncorroborated success may be coincidental environmental recovery and
        # must not increase future action utility. Failures remain conservative
        # evidence and are counted, but do not populate positive gain history.
        if result.success and not result.rolled_back:
            if (not result.causal_eligible or not result.evidence_hash
                    or not result.attribution_eligible or not result.attribution_hash):
                return
            self.by_key[k].append(result.realized_gain)
            self.successes[k] += 1
        else:
            self.failures[k] += 1

    def prior(self, action: ProposedAction) -> Tuple[float, float]:
        """
        Returns (mean realized gain, empirical confidence).
        Confidence rises with observations but is capped.
        """
        k = self.key(action)
        xs = self.by_key[k]
        if not xs:
            return 0.0, 0.0
        mean = sum(xs) / len(xs)
        conf = 1.0 - math.exp(-len(xs) / 12.0)
        return mean, min(conf, 0.95)


# ============================================================
# Risk / policy gate
# ============================================================

@dataclass
class GuardPolicy:
    max_action_risk: float = 0.35
    min_confidence: float = 0.55
    min_reversibility: float = 0.55
    cooldown_seconds: float = 30.0
    max_mutations_per_cycle: int = 2
    critical_health_floor: float = 0.25
    canary_required_above_risk: float = 0.18
    fail_open: bool = True
    denied_action_classes: Tuple[ActionClass, ...] = ()

class ActionGuard:
    HIGH_IMPACT_CLASSES = frozenset({
        ActionClass.RESTART,
        ActionClass.SCALE,
        ActionClass.REPAIR,
        ActionClass.ISOLATE,
    })

    def __init__(self, policy: GuardPolicy):
        self.policy = policy
        self.last_action_at: Dict[str, float] = {}

    def approve(
        self,
        action: ProposedAction,
        now: Optional[float] = None,
        health_score: Optional[float] = None,
        canary_available: bool = False,
    ) -> Tuple[bool, str]:
        now = now or time.time()

        if action.action_class in self.policy.denied_action_classes:
            return False, "action class denied by policy"
        if action.estimated_risk > self.policy.max_action_risk:
            return False, "risk above policy ceiling"
        if action.confidence < self.policy.min_confidence:
            return False, "confidence below policy floor"
        if action.reversibility < self.policy.min_reversibility:
            return False, "insufficient reversibility"

        # The current adapter contract has no genuine canary execution path.
        # Do not accept a metadata flag as a substitute: actions above the
        # canary threshold remain fail-closed until a real staged executor is
        # implemented and verified.
        requires_canary = action.estimated_risk > self.policy.canary_required_above_risk
        if requires_canary and not canary_available:
            return False, "canary required above risk threshold; canary execution unavailable"

        if action.action_class in self.HIGH_IMPACT_CLASSES and health_score is None:
            return False, "health context required for high-impact autonomous mutation"

        if (
            health_score is not None
            and health_score < self.policy.critical_health_floor
            and action.action_class in self.HIGH_IMPACT_CLASSES
        ):
            return False, "critical health floor: high-impact autonomous mutation denied"

        last = self.last_action_at.get(action.component, 0.0)
        if now - last < self.policy.cooldown_seconds:
            return False, "component cooldown active"

        if requires_canary:
            return True, "approved via staged canary requirement"
        return True, "approved"

    def mark(self, action: ProposedAction) -> None:
        self.last_action_at[action.component] = time.time()


# ============================================================
# Anomaly / drift detection
# ============================================================

class RollingDetector:
    def __init__(self, window: int = 60, z_threshold: float = 3.0):
        self.window = window
        self.z_threshold = z_threshold
        self.values: Dict[Tuple[str, str], Deque[float]] = defaultdict(lambda: deque(maxlen=window))

    def ingest(self, signals: Iterable[Signal]) -> List[Tuple[Signal, float]]:
        anomalies = []
        for s in signals:
            key = (s.source, s.metric)
            hist = self.values[key]
            if len(hist) >= max(8, self.window // 5):
                mean = sum(hist) / len(hist)
                var = sum((x - mean) ** 2 for x in hist) / max(1, len(hist) - 1)
                sd = math.sqrt(max(var, 1e-12))
                z = abs((s.value - mean) / sd)
                if z >= self.z_threshold:
                    anomalies.append((s, z))
            hist.append(s.value)
        return anomalies


# ============================================================
# Planner
# ============================================================

class Planner:
    """
    Converts health + anomaly evidence into low-risk candidate actions.
    A production implementation can swap this out for a stronger planner,
    rules engine, LLM, optimizer, or learned policy.
    """

    def __init__(self, memory: OutcomeMemory):
        self.memory = memory

    def propose(
        self,
        reports: Sequence[HealthReport],
        anomalies: Sequence[Tuple[Signal, float]],
    ) -> List[ProposedAction]:
        anomaly_by_component: Dict[str, float] = defaultdict(float)
        for sig, z in anomalies:
            anomaly_by_component[sig.source] = max(anomaly_by_component[sig.source], z)

        out: List[ProposedAction] = []

        for h in reports:
            z = anomaly_by_component.get(h.component, 0.0)

            # Telemetry/observer failures are uncertainty, not evidence that the
            # target itself is unhealthy. Fail open: never plan mutations from
            # a synthetic observer-error report.
            if any(symptom.startswith("observer_error:") for symptom in h.symptoms):
                continue

            # Healthy components are observed, not mutated.
            if h.score >= 0.85 and z < 3.0:
                continue

            # Default strategy: prefer reversible, low-blast-radius tuning.
            if h.score < 0.80:
                out.append(
                    ProposedAction(
                        component=h.component,
                        action_class=ActionClass.TUNE,
                        name="adaptive_backpressure",
                        payload={"level": min(1.0, max(0.1, 1.0 - h.score))},
                        expected_gain=0.08 + (0.80 - h.score) * 0.2,
                        estimated_risk=0.08,
                        reversibility=0.98,
                        confidence=h.confidence,
                        reason=f"health={h.score:.3f}; anomaly_z={z:.2f}",
                    ).finalize()
                )

            if h.score < 0.55:
                out.append(
                    ProposedAction(
                        component=h.component,
                        action_class=ActionClass.ROUTE,
                        name="shift_load_to_healthier_peers",
                        payload={"fraction": min(0.35, max(0.05, 0.55 - h.score))},
                        expected_gain=0.12,
                        estimated_risk=0.16,
                        reversibility=0.95,
                        confidence=h.confidence,
                        reason="degraded health; reduce exposure before repair",
                    ).finalize()
                )

            if h.score < 0.35:
                out.append(
                    ProposedAction(
                        component=h.component,
                        action_class=ActionClass.RESTART,
                        name="graceful_restart",
                        payload={"drain_first": True},
                        expected_gain=0.20,
                        estimated_risk=0.24,
                        reversibility=0.80,
                        confidence=h.confidence,
                        reason="severe degradation after lower-impact options",
                    ).finalize()
                )

        # Blend online outcome memory into expected utility only. Historical
        # action outcomes are advisory; they must never manufacture confidence
        # in the *current* telemetry/evidence used to authorize a mutation.
        for a in out:
            learned_gain, learned_conf = self.memory.prior(a)
            if learned_conf > 0:
                a.expected_gain = (1 - learned_conf) * a.expected_gain + learned_conf * learned_gain

        # Utility: high gain/confidence/reversibility, low risk.
        def utility(a: ProposedAction) -> float:
            return (
                a.expected_gain * (0.5 + 0.5 * a.confidence)
                + 0.05 * a.reversibility
                - 0.35 * a.estimated_risk
            )

        return sorted(out, key=utility, reverse=True)


# ============================================================
# Canary verifier / rollback decision
# ============================================================

@dataclass
class VerificationPolicy:
    settle_seconds: float = 0.20
    min_improvement: float = -0.015
    rollback_below_score: float = 0.30

class Verifier:
    def __init__(self, policy: VerificationPolicy):
        self.policy = policy

    async def verify(
        self,
        adapter: InfraAdapter,
        before: HealthReport,
    ) -> Tuple[bool, HealthReport, str]:
        await asyncio.sleep(self.policy.settle_seconds)
        after = await adapter.health()
        delta = after.score - before.score

        if after.score < self.policy.rollback_below_score:
            return False, after, "post-action health below rollback floor"
        if delta < self.policy.min_improvement:
            return False, after, f"health regressed by {delta:.4f}"
        return True, after, f"verified delta={delta:.4f}"


# ============================================================
# Loop engine
# ============================================================

@dataclass
class LoopConfig:
    cycle_seconds: float = 5.0
    shadow_mode: bool = True
    max_concurrent_collectors: int = 16
    learning_enabled: bool = True
    journal_path: str = "infra_loop_journal.jsonl"
    attribution_pre_seconds: float = 60.0
    attribution_post_seconds: float = 60.0
    proof_envelope_ttl_seconds: float = 300.0
    durable_proof_journal_path: str | None = None
    durable_proof_fsync: bool = True
    startup_recovery_enabled: bool = False
    recovery_quarantine_dir: str | None = None
    startup_recovery_now: float | None = None
    recovery_checkpoint_path: str | None = None
    recovery_checkpoint_fsync: bool = True
    recovery_chain_dir: str | None = None
    recovery_chain_lock_timeout_seconds: float = 2.0
    recovery_authenticator: Any | None = None

class InfrastructureSupervisoryLoop:
    """
    OBSERVE -> MODEL -> PROPOSE -> GUARD -> SNAPSHOT -> ACT
           -> VERIFY -> ROLLBACK? -> LEARN -> JOURNAL

    Design goals:
      * Surround infrastructure via adapters.
      * Never become a hard dependency.
      * Prefer observation and reversible changes.
      * Fail open when the loop itself has trouble.
      * Keep a complete action/outcome journal.
    """

    def __init__(
        self,
        adapters: Sequence[InfraAdapter],
        config: LoopConfig | None = None,
        guard_policy: GuardPolicy | None = None,
        verification_policy: VerificationPolicy | None = None,
        topology_model: TopologyModel | None = None,
        canary_executor: StagedCanaryExecutor | None = None,
        evidence_collector: ReadOnlyEvidenceCollector | None = None,
        attributor: CounterfactualAttributor | None = None,
        control_components: Mapping[str, str] | None = None,
    ):
        self.adapters = {a.name: a for a in adapters}
        self.config = config or LoopConfig()
        self.memory = OutcomeMemory()
        self.detector = RollingDetector()
        self.planner = Planner(self.memory)
        self.guard = ActionGuard(guard_policy or GuardPolicy())
        self.verifier = Verifier(verification_policy or VerificationPolicy())
        self.topology_governor = BlastRadiusGovernor(topology_model) if topology_model is not None else None
        self.mutation_leases = MutationLeaseManager()
        self.canary_executor = canary_executor
        self.evidence_collector = evidence_collector
        self.attributor = attributor or CounterfactualAttributor()
        self.control_components = dict(control_components or {})
        self.envelope_assembler = SourceNativeEnvelopeAssembler()
        self.envelope_verifier = ProofEnvelopeVerifier()
        self.proof_journal_verifier = ProofJournalReplayVerifier()
        self.durable_proof_journal = (DurableProofJournal(self.config.durable_proof_journal_path)
                                      if self.config.durable_proof_journal_path else None)
        self._recovered_proof_transactions = ()
        self._startup_recovery_decision = None
        if self.config.startup_recovery_enabled and self.config.durable_proof_journal_path:
            try:
                policy = StartupRecoveryPolicy(self.config.durable_proof_journal_path, verifier=self.proof_journal_verifier)
                decision = policy.recover(quarantine_dir=self.config.recovery_quarantine_dir, now=self.config.startup_recovery_now)
                self._startup_recovery_decision = decision
                restore_eligible = decision.proof_restore_eligible
                if self.config.recovery_chain_dir:
                    try:
                        chain = AppendOnlyRecoveryChain(self.config.recovery_chain_dir)
                        lock = RecoveryChainLock(str(chain.directory / ".append.lock"), timeout_seconds=self.config.recovery_chain_lock_timeout_seconds)
                        with lock:
                            auth_chain = (AuthenticatedRecoveryChain(chain.directory, self.config.recovery_authenticator)
                                          if self.config.recovery_authenticator is not None else None)
                            transaction_coordinator = (RecoveryDualChainCoordinator(chain.directory)
                                                       if auth_chain is not None else None)
                            transaction_verdict = (transaction_coordinator.reconcile(
                                chain, auth_chain, fsync=self.config.recovery_checkpoint_fsync
                            ) if transaction_coordinator is not None else None)
                            prior_verdict = chain.verify_chain()
                            prior_head = chain.head() if prior_verdict.valid else None
                            auth_verdict = auth_chain.verify_against(chain) if auth_chain is not None else None
                            transaction_ok = bool(transaction_verdict and transaction_verdict.valid) if auth_chain is not None else True
                            # Chain corruption/fork/gap/stale HEAD, authentication divergence, or transaction corruption fails closed.
                            if prior_verdict.valid and prior_head is not None:
                                continuity_ok = bool(RecoveryContinuityVerifier().verify(prior_head.recovery_checkpoint, decision).valid)
                                authentication_ok = bool(auth_verdict and auth_verdict.valid) if auth_chain is not None else True
                                restore_eligible = bool(continuity_ok and authentication_ok and transaction_ok)
                            else:
                                restore_eligible = False
                            # Never advance corrupt/divergent/uncommitted authenticated history.
                            # V32 separates verification from signing: a public-key-only authenticator may
                            # restore already committed history but cannot bootstrap or append new evidence.
                            authentication_ok = bool(auth_verdict and auth_verdict.valid) if auth_chain is not None else True
                            if prior_verdict.valid and authentication_ok and transaction_ok:
                                checkpoint = RecoveryCheckpoint.from_decision(decision)
                                if transaction_coordinator is not None:
                                    next_generation = prior_verdict.generation + 1
                                    capability = getattr(self.config.recovery_authenticator, "can_sign_for_generation", None)
                                    can_sign = (bool(capability(next_generation)) if callable(capability)
                                                else bool(getattr(self.config.recovery_authenticator, "can_sign", True)))
                                    if can_sign:
                                        write_verdict = transaction_coordinator.stage_and_commit(
                                            checkpoint, chain, auth_chain, fsync=self.config.recovery_checkpoint_fsync
                                        )
                                        if not write_verdict.valid or not write_verdict.committed:
                                            raise RuntimeError(f"dual-chain recovery commit failed: {write_verdict.reason}")
                                    elif prior_head is None:
                                        # Verification-only mode cannot create an authenticated genesis.
                                        restore_eligible = False
                                else:
                                    chain.append(checkpoint, fsync=self.config.recovery_checkpoint_fsync)
                    except Exception:
                        restore_eligible = False
                elif self.config.recovery_checkpoint_path:
                    try:
                        store = AtomicRecoveryCheckpointStore(self.config.recovery_checkpoint_path)
                        prior = store.read()
                        restore_eligible = bool(prior and RecoveryContinuityVerifier().verify(prior, decision).valid)
                        cp = RecoveryCheckpoint.from_decision(decision)
                        store.write(cp, fsync=self.config.recovery_checkpoint_fsync)
                    except Exception:
                        restore_eligible = False
                self._recovered_proof_transactions = (decision.accepted_transactions if restore_eligible else ())
            except Exception:
                # Recovery is evidence-side only: fail closed for restored proof,
                # fail open for unrelated infrastructure supervision.
                self._startup_recovery_decision = None
                self._recovered_proof_transactions = ()
        self._latest_envelopes = {}
        self._stop = asyncio.Event()
        self._cycle_id = 0

    async def stop(self) -> None:
        self._stop.set()

    def recover_durable_proofs(self, *, now: float | None = None):
        """Recover and independently replay-verify complete durable proof records.

        Bad/partial records never regain proof status. Recovery failure does not grant or
        revoke mutation authority and does not stop unrelated infrastructure operation.
        """
        if self.durable_proof_journal is None:
            self._recovered_proof_transactions = ()
            return None, ()
        report = self.durable_proof_journal.recover()
        valid=[]
        check_now=time.time() if now is None else now
        for record in report.records:
            try:
                tx=ProofJournalTransaction.from_mapping(record.payload)
                replay=self.proof_journal_verifier.verify(tx,now=check_now)
            except Exception:
                continue
            if replay.valid:
                valid.append(tx)
        self._recovered_proof_transactions=tuple(valid)
        return report, self._recovered_proof_transactions

    def _canary_available(self, component: str) -> bool:
        if self.canary_executor is None:
            return False
        adapter = self.adapters.get(component)
        return adapter is not None and self.canary_executor.adapter_capable(adapter)

    def _requires_canary(self, action: ProposedAction) -> bool:
        return action.estimated_risk > self.guard.policy.canary_required_above_risk

    async def _collect(self) -> Tuple[List[Signal], List[HealthReport]]:
        # Bound observer fan-out so a large adapter set cannot overload the
        # supervisory process or the infrastructure it is observing.
        limit = max(1, int(self.config.max_concurrent_collectors))
        semaphore = asyncio.Semaphore(limit)

        async def one(a: InfraAdapter):
            async with semaphore:
                try:
                    sigs, health = await asyncio.gather(a.collect_signals(), a.health())
                    return list(sigs), health, None
                except Exception as exc:
                    return [], None, exc

        results = await asyncio.gather(*(one(a) for a in self.adapters.values()))
        signals: List[Signal] = []
        reports: List[HealthReport] = []

        for name, (sigs, health, err) in zip(self.adapters, results):
            if err is not None:
                # Fail-open: a broken observer should not break its target.
                reports.append(
                    HealthReport(
                        component=name,
                        score=0.50,
                        confidence=0.20,
                        symptoms=[f"observer_error:{type(err).__name__}"],
                    )
                )
                continue
            signals.extend(sigs)
            reports.append(health)

        return signals, reports

    async def _execute_action(
        self,
        action: ProposedAction,
        before: HealthReport,
    ) -> ActionResult:
        adapter = self.adapters[action.component]
        snapshot = await adapter.snapshot()
        t0 = time.perf_counter()

        ok, msg = await adapter.execute(action)
        if not ok:
            return ActionResult(
                action=action,
                success=False,
                before_score=before.score,
                after_score=before.score,
                latency_ms=(time.perf_counter() - t0) * 1000,
                message=f"execute failed: {msg}",
            )

        verified, after, vmsg = await self.verifier.verify(adapter, before)

        if not verified:
            rb_ok, rb_msg = await adapter.rollback(snapshot, action)
            final_health = await adapter.health()
            return ActionResult(
                action=action,
                success=False,
                before_score=before.score,
                after_score=final_health.score,
                latency_ms=(time.perf_counter() - t0) * 1000,
                rolled_back=rb_ok,
                message=f"{vmsg}; rollback={rb_ok}:{rb_msg}",
            )

        return ActionResult(
            action=action,
            success=True,
            before_score=before.score,
            after_score=after.score,
            latency_ms=(time.perf_counter() - t0) * 1000,
            message=vmsg,
        )

    def _journal(self, event: Mapping[str, Any]) -> None:
        p = Path(self.config.journal_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str, sort_keys=True) + "\n")

    def _source_receipt(self, action: ProposedAction, stage: str, payload: Mapping[str, Any]) -> DecisionReceipt:
        receipt = DecisionReceipt.issue(
            stage=stage, action_identity=action.fingerprint, issued_at=time.time(), payload=payload
        )
        self._journal({
            "type": "source_receipt", "cycle": self._cycle_id,
            "receipt": dataclasses.asdict(receipt), "ts": receipt.issued_at,
        })
        return receipt

    def _finalize_envelope(self, action: ProposedAction, receipts: Sequence[DecisionReceipt]) -> str:
        now = time.time()
        assembled = self.envelope_assembler.assemble(
            receipts, now=now, ttl_seconds=self.config.proof_envelope_ttl_seconds
        )
        verified = self.envelope_verifier.verify(assembled.envelope, now=now) if assembled.valid and assembled.envelope else None
        valid = bool(assembled.valid and verified and verified.valid)
        reason = verified.reason if verified is not None else assembled.reason
        self._journal({
            "type": "proof_envelope", "cycle": self._cycle_id,
            "action_identity": action.fingerprint, "valid": valid,
            "reason": reason,
            "envelope": dataclasses.asdict(assembled.envelope) if assembled.envelope else None,
            "ts": now,
        })
        if valid and assembled.envelope:
            self._latest_envelopes[action.fingerprint] = assembled.envelope
            return assembled.envelope.envelope_hash
        self._latest_envelopes.pop(action.fingerprint, None)
        return ""

    async def cycle(self) -> Dict[str, Any]:
        self._cycle_id += 1
        signals, reports = await self._collect()
        anomalies = self.detector.ingest(signals)
        candidates = self.planner.propose(reports, anomalies)

        report_by_component = {r.component: r for r in reports}
        health_scores = {r.component: r.score for r in reports}
        approved: List[ProposedAction] = []
        topology_decisions: List[Dict[str, Any]] = []
        lease_owners: List[str] = []
        traces: Dict[str, List[DecisionReceipt]] = {}
        lease_scopes_by_action: Dict[str, Tuple[str, ...]] = {}
        intervention_ids: Dict[str, str] = {}
        mutation_recorders: Dict[str, MutationLifecycleRecorder] = {}

        for a in candidates:
            intervention_id = str(uuid.uuid4())
            intervention_ids[a.fingerprint] = intervention_id
            recorder = MutationLifecycleRecorder(intervention_id=intervention_id, action_fingerprint=a.fingerprint, component=a.component)
            recorder.record("created", timestamp=time.time(), details={"cycle": self._cycle_id, "action": a.name})
            mutation_recorders[a.fingerprint] = recorder
            trace: List[DecisionReceipt] = []
            traces[a.fingerprint] = trace
            ok, why = self.guard.approve(
                a,
                health_score=report_by_component[a.component].score,
                canary_available=self._canary_available(a.component),
            )
            trace.append(self._source_receipt(a, "guard", {
                "approved": ok, "reason": why, "health_score": report_by_component[a.component].score,
                "canary_available": self._canary_available(a.component), "intervention_id": intervention_id,
            }))

            scopes: Tuple[str, ...] = ()
            if ok and self.topology_governor is not None:
                decision = self.topology_governor.evaluate(a, health_scores=health_scores)
                scopes = tuple(decision.lease_scopes)
                topology_payload = {
                    "configured": True, "component": a.component, "action": a.name,
                    "approved": decision.approved, "reason": decision.reason,
                    "impacted_components": list(decision.impacted_components),
                    "lease_scopes": list(decision.lease_scopes),
                }
                topology_decisions.append(dict(topology_payload))
                ok, why = decision.approved, decision.reason
            elif ok:
                topology_payload = {"configured": False, "approved": True, "reason": "topology governor not configured"}
            else:
                topology_payload = {"configured": self.topology_governor is not None, "approved": False, "reason": "guard denied; topology not evaluated"}
            trace.append(self._source_receipt(a, "topology", topology_payload))

            lease_payload: Dict[str, Any]
            if ok and scopes:
                owner = f"intervention:{intervention_id}"
                acquired = self.mutation_leases.acquire(owner, scopes, ttl_seconds=max(1.0, self.config.cycle_seconds * 2))
                lease_payload = {"required": True, "acquired": acquired, "owner": owner, "scopes": list(scopes), "intervention_id": intervention_id}
                if not acquired:
                    ok, why = False, "mutation lease conflict"
                    if topology_decisions:
                        topology_decisions[-1]["approved"] = False
                        topology_decisions[-1]["reason"] = why
                else:
                    lease_owners.append(owner)
                    lease_scopes_by_action[a.fingerprint] = scopes
            elif ok:
                lease_payload = {"required": False, "acquired": False, "owner": None, "scopes": [], "intervention_id": intervention_id}
            else:
                lease_payload = {"required": bool(scopes), "acquired": False, "owner": None, "scopes": list(scopes), "reason": "upstream denial", "intervention_id": intervention_id}
            recorder.lease_owner = lease_payload.get("owner")
            recorder.lease_scopes = tuple(lease_payload.get("scopes", ()))
            recorder.record("lease_acquired" if lease_payload.get("acquired") else "lease_skipped", timestamp=time.time(), details=lease_payload)
            trace.append(self._source_receipt(a, "lease", lease_payload))

            self._journal({
                "type": "proposal", "cycle": self._cycle_id, "action": dataclasses.asdict(a),
                "approved": ok, "reason": why, "ts": time.time(),
            })
            if ok:
                approved.append(a)
            if len(approved) >= self.guard.policy.max_mutations_per_cycle:
                break

        results: List[ActionResult] = []

        if not self.config.shadow_mode:
            for a in approved:
                before = report_by_component[a.component]
                trace = traces[a.fingerprint]
                intervention_ts = time.time()
                intervention_id = intervention_ids[a.fingerprint]
                mutation_recorder = mutation_recorders[a.fingerprint]
                mutation_recorder.record("mutation_started", timestamp=time.time(), details={"action": a.name, "component": a.component})
                canary_proof_valid = False
                canary_payload: Dict[str, Any]
                try:
                    if self._requires_canary(a):
                        canary = await self.canary_executor.execute(
                            self.adapters[a.component], a, before, cycle_id=self._cycle_id
                        )
                        self._journal({
                            "type": "canary_proof", "cycle": self._cycle_id,
                            "proof": dataclasses.asdict(canary.proof), "ts": time.time(),
                        })
                        after_score = canary.proof.observed_score
                        canary_proof_valid = canary.proof.verify_integrity()
                        causal_eligible = (
                            canary.status is CanaryStatus.PROMOTED and canary_proof_valid
                            and canary.proof.promotion_authorized
                            and (canary.proof.observed_score - canary.proof.before_score) > 0.0
                        )
                        canary_payload = {
                            "required": True, "status": canary.status.value,
                            "proof_hash": canary.proof.proof_hash, "proof_valid": canary_proof_valid,
                            "promotion_authorized": canary.proof.promotion_authorized,
                        }
                        r = ActionResult(
                            action=a, success=canary.status is CanaryStatus.PROMOTED,
                            before_score=before.score, after_score=after_score, latency_ms=0.0,
                            rolled_back=canary.status in {CanaryStatus.ABORTED, CanaryStatus.PROMOTION_FAILED},
                            message=f"staged canary {canary.status.value}: {canary.message}; proof={canary.proof.proof_hash}",
                            causal_eligible=causal_eligible,
                            evidence_hash=canary.proof.proof_hash if causal_eligible else "",
                        )
                    else:
                        canary_payload = {"required": False, "status": "not_required", "proof_valid": False}
                        r = await self._execute_action(a, before)
                except Exception as exc:
                    canary_payload = {"required": self._requires_canary(a), "status": "execution_error", "proof_valid": False,
                                      "error": f"{type(exc).__name__}: {exc}"}
                    r = ActionResult(
                        action=a, success=False, before_score=before.score, after_score=before.score,
                        latency_ms=0.0, message=f"loop execution error: {type(exc).__name__}: {exc}",
                    )
                mutation_recorder.record("mutation_completed" if r.success else "mutation_failed", timestamp=time.time(),
                                         details={"success": r.success, "rolled_back": r.rolled_back, "message": r.message})
                trace.append(self._source_receipt(a, "canary", canary_payload))

                observation = None
                attribution = None
                if self.evidence_collector is not None:
                    req = EvidenceRequest(
                        component=a.component, action_fingerprint=a.fingerprint, intervention_ts=intervention_ts,
                        pre_start=intervention_ts - max(0.0, self.config.attribution_pre_seconds),
                        post_end=intervention_ts + max(0.0, self.config.attribution_post_seconds),
                        intervention_id=intervention_id,
                        control_component=self.control_components.get(a.component),
                        protected_scopes=lease_scopes_by_action.get(a.fingerprint, ()),
                    )
                    observation = await self.evidence_collector.collect(req, proof_valid=(canary_proof_valid if self._requires_canary(a) else r.success))
                    evidence_payload = dataclasses.asdict(observation)
                    attribution = self.attributor.evaluate(observation)
                    attribution_payload = dataclasses.asdict(attribution)
                    r.attribution_eligible = attribution.positive_learning_eligible
                    r.attribution_hash = attribution.evidence_hash if attribution.positive_learning_eligible else ""
                else:
                    evidence_payload = {"available": False, "reason": "read-only evidence collector not configured"}
                    attribution_payload = {"eligible": False, "reason": "attribution evidence unavailable"}
                    r.attribution_eligible = False
                    r.attribution_hash = ""
                trace.append(self._source_receipt(a, "evidence", evidence_payload))
                trace.append(self._source_receipt(a, "attribution", attribution_payload))
                r.intervention_id = intervention_id
                r.proof_envelope_hash = self._finalize_envelope(a, trace)

                results.append(r)
                self.guard.mark(a)
                if self.config.learning_enabled:
                    self.memory.update(r)
                lease_owner = f"intervention:{intervention_id}"
                released = self.mutation_leases.release(lease_owner)
                mutation_recorder.record("lease_released" if released else "lease_release_skipped", timestamp=time.time(),
                                         details={"owner": lease_owner, "released": released})
                mutation_receipt = mutation_recorder.finalize()
                if not mutation_receipt.verify_integrity():
                    raise RuntimeError("mutation receipt integrity failed")
                r.mutation_receipt_hash = mutation_receipt.receipt_hash
                self._journal({"type": "mutation_receipt", "cycle": self._cycle_id,
                               "receipt": dataclasses.asdict(mutation_receipt), "ts": time.time()})
                envelope = self._latest_envelopes.get(a.fingerprint)
                if envelope is not None:
                    tx_now = time.time()
                    tx = ProofJournalTransaction.create(
                        intervention_id=intervention_id, action_identity=a.fingerprint,
                        result=dataclasses.asdict(r), proof_envelope=envelope,
                        mutation_receipt=mutation_receipt, created_at=tx_now,
                    )
                    replay = self.proof_journal_verifier.verify(tx, now=tx_now)
                    if replay.valid:
                        tx_payload=dataclasses.asdict(tx)
                        durable_ok=True
                        if self.durable_proof_journal is not None:
                            try:
                                self.durable_proof_journal.append(tx_payload, fsync=self.config.durable_proof_fsync)
                            except Exception as exc:
                                durable_ok=False
                                self._journal({"type": "durable_proof_append_failed", "cycle": self._cycle_id,
                                               "intervention_id": intervention_id, "reason": str(exc), "ts": tx_now})
                        self._journal({"type": "proof_transaction", "cycle": self._cycle_id,
                                       "transaction": tx_payload, "durable": durable_ok, "ts": tx_now})
                    else:
                        self._journal({"type": "proof_transaction_rejected", "cycle": self._cycle_id,
                                       "intervention_id": intervention_id, "reason": replay.reason, "ts": tx_now})
                self._journal({
                    "type": "result", "cycle": self._cycle_id, "result": dataclasses.asdict(r), "ts": time.time(),
                })
        else:
            for a in approved:
                trace = traces[a.fingerprint]
                trace.append(self._source_receipt(a, "canary", {"status": "shadow_not_executed", "required": self._requires_canary(a)}))
                trace.append(self._source_receipt(a, "evidence", {"available": False, "reason": "shadow action not executed"}))
                trace.append(self._source_receipt(a, "attribution", {"eligible": False, "reason": "shadow action not executed"}))
                envelope_hash = self._finalize_envelope(a, trace)
                self._journal({
                    "type": "shadow_action", "cycle": self._cycle_id, "action": dataclasses.asdict(a),
                    "proof_envelope_hash": envelope_hash, "ts": time.time(),
                })

        if self.config.shadow_mode:
            for owner in lease_owners:
                self.mutation_leases.release(owner)

        summary = {
            "cycle": self._cycle_id, "signals": len(signals),
            "reports": [dataclasses.asdict(r) for r in reports],
            "anomalies": [{"source": s.source, "metric": s.metric, "value": s.value, "z": z} for s, z in anomalies],
            "candidate_actions": len(candidates), "approved_actions": [dataclasses.asdict(a) for a in approved],
            "topology_decisions": topology_decisions, "executed_results": [dataclasses.asdict(r) for r in results],
            "shadow_mode": self.config.shadow_mode,
        }
        self._journal({"type": "cycle_summary", **summary, "ts": time.time()})
        return summary

    async def run(self) -> None:
        while not self._stop.is_set():
            started = time.perf_counter()
            try:
                await self.cycle()
            except Exception as exc:
                # The supervisory loop must not become an outage source.
                self._journal({
                    "type": "loop_error",
                    "error": f"{type(exc).__name__}: {exc}",
                    "ts": time.time(),
                })
                if not self.guard.policy.fail_open:
                    raise

            elapsed = time.perf_counter() - started
            timeout = max(0.0, self.config.cycle_seconds - elapsed)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                pass


# ============================================================
# Example adapter
# ============================================================

class DemoServiceAdapter:
    """
    Replace with adapters for:
      - Docker / systemd
      - Kubernetes
      - Redis / Postgres
      - Kafka / NATS
      - GitHub Actions / CI runners
      - model workers / inference queues
      - data-ingestion pipelines
      - trading research services

    This demo intentionally uses an in-memory "load" knob.
    """

    def __init__(self, name: str, base_health: float = 0.72):
        self.name = name
        self.load = 0.75
        self.base_health = base_health

    async def collect_signals(self) -> Sequence[Signal]:
        jitter = random.uniform(-0.02, 0.02)
        return [
            Signal(self.name, "load", self.load + jitter),
            Signal(self.name, "latency_ms", 70 + 180 * self.load + random.uniform(-8, 8)),
            Signal(self.name, "error_rate", max(0.0, (self.load - 0.70) * 0.08 + random.uniform(0, 0.005))),
        ]

    async def health(self) -> HealthReport:
        score = max(0.0, min(1.0, self.base_health + (0.72 - self.load) * 0.55))
        return HealthReport(
            component=self.name,
            score=score,
            confidence=0.90,
            symptoms=[] if score > 0.75 else ["load_pressure"],
            evidence={"load": self.load},
        )

    async def snapshot(self) -> Dict[str, Any]:
        return {"load": self.load, "base_health": self.base_health}

    async def execute(self, action: ProposedAction) -> Tuple[bool, str]:
        if action.name == "adaptive_backpressure":
            self.load = max(0.20, self.load - 0.08)
            return True, "backpressure adjusted"
        if action.name == "shift_load_to_healthier_peers":
            self.load = max(0.20, self.load - float(action.payload.get("fraction", 0.1)))
            return True, "load shifted"
        if action.name == "graceful_restart":
            self.load = max(0.35, self.load - 0.15)
            return True, "graceful restart completed"
        return False, f"unsupported action {action.name}"

    async def rollback(self, snapshot: Dict[str, Any], action: ProposedAction) -> Tuple[bool, str]:
        self.load = snapshot["load"]
        self.base_health = snapshot["base_health"]
        return True, "restored snapshot"


async def demo():
    loop = InfrastructureSupervisoryLoop(
        adapters=[
            DemoServiceAdapter("ingestion", base_health=0.68),
            DemoServiceAdapter("feature-store", base_health=0.76),
            DemoServiceAdapter("model-worker", base_health=0.64),
        ],
        config=LoopConfig(
            cycle_seconds=0.4,
            shadow_mode=True,   # start here; switch only after observing journal
            journal_path="demo_infra_loop_journal.jsonl",
        ),
    )
    for _ in range(5):
        summary = await loop.cycle()
        print(json.dumps(summary, indent=2, default=str))
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(demo())
