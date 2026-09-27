from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from .automation import AutonomousResearchLoop, DispatchBatch
from .contracts import FinancialState, HypothesisStatus, digest
from .decision_policy import ResearchDecisionPolicy, ResearchRecommendation, recommend
from .thesis import ThesisHealthSnapshot, ThesisMonitor, ThesisPolicy
from .trigger_policy import AdaptiveTriggerDetector, FeatureTriggerSpec, FinancialTriggerPolicy
from .views import CommandGraphView, FinancialTabView, OracleViewProjector, ResearchTabView

_TRIGGER_STATE_KEY="adaptive_trigger_detector.v1"

@dataclass(frozen=True,slots=True)
class OperatingCycleResult:
    decision_ns:int
    state_id:str
    trigger_types:tuple[str,...]
    hypothesis_ids:tuple[str,...]
    duplicate_hypotheses:tuple[str,...]
    priority_hash:str

@dataclass(frozen=True,slots=True)
class PriorityDecision:
    job_id:str
    hypothesis_id:str
    multiplier:float
    reasons:tuple[str,...]

@dataclass(frozen=True,slots=True)
class OperatingViews:
    financial:FinancialTabView
    research:ResearchTabView
    command_graph:CommandGraphView

class OracleOperatingLayer:
    """Restart-safe Financial/Research operating layer for ORACLE.

    This layer turns causal financial-state changes into bounded research work,
    monitors thesis freshness, and supplies a dynamic priority overlay to the
    already-durable autonomous loop. It cannot promote a feature or authorize an
    order; those boundaries remain in DAEDALUS/ATHENA/Icarus.
    """
    def __init__(
        self,
        loop:AutonomousResearchLoop,
        *,
        trigger_policy:FinancialTriggerPolicy|None=None,
        thesis_policy:ThesisPolicy|None=None,
        decision_policy:ResearchDecisionPolicy|None=None,
    ):
        self.loop=loop
        self.detector=AdaptiveTriggerDetector(trigger_policy or FinancialTriggerPolicy())
        self.theses=ThesisMonitor(thesis_policy or ThesisPolicy())
        self.decision_policy=decision_policy or ResearchDecisionPolicy()
        for assessment in self.loop.engine.store.load_assessments():
            self.theses.observe(assessment)
        saved=self.loop.engine.store.load_operating_state(_TRIGGER_STATE_KEY)
        if saved is not None:
            _,payload=saved
            self.detector.restore_control_state(payload,last_state=self.loop.latest_state)
        elif self.loop.latest_state is not None:
            # On an upgraded database with no detector snapshot, treat the latest
            # durable state as the comparison baseline. This avoids fabricating a
            # delta from "nothing" after restart.
            self.detector._last_state=self.loop.latest_state

    def _persist_detector(self,decision_ns:int)->None:
        self.loop.engine.store.put_operating_state(_TRIGGER_STATE_KEY,updated_ns=decision_ns,payload=self.detector.snapshot())

    def ingest_financial_state(
        self,
        state:FinancialState,
        *,
        feature_specs:tuple[FeatureTriggerSpec,...]=(),
        horizon:str="60m",
        sensors:Iterable[str]=(),
    )->OperatingCycleResult:
        # Persist the state before deriving research from it. If a process dies
        # after this point, restart sees the same state and detector snapshot.
        self.loop.set_financial_state(state)
        triggers=self.detector.evaluate(state,feature_specs=feature_specs)
        hypothesis_ids=[]; duplicates=[]
        sensor_tuple=tuple(sorted({str(x) for x in sensors if str(x)}))
        for trigger in triggers:
            h=self.loop.submit_trigger(trigger,horizon=horizon,sensors=sensor_tuple)
            hypothesis_ids.append(h.hypothesis_id)
            if self.loop._last_duplicate: duplicates.append(h.hypothesis_id)
        self._persist_detector(state.decision_ns)
        overlay=self.priority_multipliers(state.decision_ns)
        return OperatingCycleResult(
            state.decision_ns,state.state_id,tuple(t.trigger_type for t in triggers),tuple(hypothesis_ids),tuple(duplicates),
            digest({"decision_ns":state.decision_ns,"multipliers":overlay}),
        )

    def sync_assessments(self)->None:
        # Assessment history is append-only in the store, so rebuilding the monitor
        # is deterministic and cheap relative to research work.
        monitor=ThesisMonitor(self.theses.policy)
        for assessment in self.loop.engine.store.load_assessments(): monitor.observe(assessment)
        self.theses=monitor

    def thesis_health(self,decision_ns:int)->tuple[ThesisHealthSnapshot,...]:
        self.sync_assessments()
        rows=[]
        for hypothesis_id in sorted(self.theses.history):
            rows.append(self.theses.snapshot(hypothesis_id,decision_ns))
        return tuple(rows)

    def retest_required(self,decision_ns:int)->tuple[ThesisHealthSnapshot,...]:
        return tuple(x for x in self.thesis_health(decision_ns) if x.retest_required)

    def priority_decisions(self,decision_ns:int)->tuple[PriorityDecision,...]:
        """Explain every causal dispatch multiplier without rewriting job specs."""
        self.sync_assessments()
        state=self.loop.latest_state
        health_by_hypothesis={x.hypothesis_id:x for x in self.thesis_health(decision_ns)} if self.theses.history else {}
        out=[]
        for job in self.loop.engine.scheduler._jobs.values():
            if job.created_ns>decision_ns or job.job_id in self.loop.runtime.completed or job.job_id in self.loop.runtime.dead_letter:
                continue
            task=self.loop.task_by_job.get(job.job_id)
            system=(task.system if task else (job.required_systems[0] if job.required_systems else "")).upper()
            mult=1.0; reasons=[]
            if state is not None:
                if state.ood_score>=.70:
                    if system in {"NEXUS","AION","ATHENA"}: mult*=1.0+.75*state.ood_score; reasons.append("HIGH_OOD_CONTEXT")
                    elif system=="DAEDALUS": mult*=1.0+.35*state.ood_score; reasons.append("HIGH_OOD_FALSIFICATION")
                if state.confidence<.55:
                    if system in {"NEXUS","ATHENA"}: mult*=1.35; reasons.append("LOW_STATE_CONFIDENCE_AUDIT")
                    else: mult*=.80; reasons.append("LOW_STATE_CONFIDENCE_DEFER")
                if state.source_health:
                    avg=sum(float(v) for v in state.source_health.values())/len(state.source_health)
                    if avg<.60:
                        if system in {"NEXUS","ATHENA"}: mult*=1.45; reasons.append("SOURCE_HEALTH_AUDIT")
                        elif system=="DAEDALUS": mult*=.85; reasons.append("SOURCE_HEALTH_DEFER_FALSIFICATION")
            thesis=health_by_hypothesis.get(job.hypothesis_id)
            if thesis is not None:
                if thesis.retest_required and system in {"AION","ATHENA","DAEDALUS"}: mult*=1.50; reasons.append("THESIS_RETEST_REQUIRED")
                if thesis.effective_health<.45 and system=="DAEDALUS": mult*=1.35; reasons.append("THESIS_HEALTH_LOW")
                if thesis.drift>=self.theses.policy.drift_threshold and system in {"AION","DAEDALUS"}: mult*=1.25; reasons.append("THESIS_DRIFT")
            out.append(PriorityDecision(job.job_id,job.hypothesis_id,max(.05,min(20.0,mult)),tuple(reasons or ("BASE_PRIORITY",))))
        return tuple(sorted(out,key=lambda x:x.job_id))

    def priority_multipliers(self,decision_ns:int)->dict[str,float]:
        return {x.job_id:x.multiplier for x in self.priority_decisions(decision_ns)}

    def action_board(self,decision_ns:int)->tuple[ResearchRecommendation,...]:
        self.sync_assessments()
        health={x.hypothesis_id:x for x in self.thesis_health(decision_ns)} if self.theses.history else {}
        rows=[]
        for hid in sorted(self.loop.engine.hypotheses):
            rows.append(recommend(hid,self.loop.engine.status[hid],self.loop.engine.assessments.get(hid),health.get(hid),policy=self.decision_policy))
        return tuple(rows)

    def dispatch(self,decision_ns:int,*,max_requests:int|None=None)->DispatchBatch:
        return self.loop.dispatch(decision_ns,max_requests=max_requests,priority_multipliers=self.priority_multipliers(decision_ns))

    def views(self,decision_ns:int)->OperatingViews:
        return OperatingViews(
            OracleViewProjector.financial(self.loop,self.loop.latest_state,as_of_ns=decision_ns),
            OracleViewProjector.research(self.loop,as_of_ns=decision_ns),
            OracleViewProjector.command_graph(self.loop,as_of_ns=decision_ns),
        )
