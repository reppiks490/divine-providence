from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Iterable
from .contracts import Hypothesis, digest, finite01
from .counterfactual import CounterfactualSpec, standard_attack_suite

_ALLOWED_SYSTEMS = ("NEXUS", "AION", "ARGUS", "ATHENA", "DAEDALUS")

@dataclass(frozen=True, slots=True)
class PlanTask:
    task_key: str
    system: str
    task_type: str
    evidence_kind: str
    estimated_compute_cost: float
    expected_information_gain: float
    strategic_relevance: float
    evidence_deficit: float
    novelty: float
    required_states: tuple[str, ...] = ()
    required: bool = True
    payload: dict[str, Any] | None = None
    def __post_init__(self):
        if not self.task_key or self.system not in _ALLOWED_SYSTEMS or not self.task_type or not self.evidence_kind:
            raise ValueError("plan task identity required")
        if self.estimated_compute_cost <= 0:
            raise ValueError("compute cost must be positive")
        for name in ("expected_information_gain", "strategic_relevance", "evidence_deficit", "novelty"):
            finite01(name, getattr(self, name))

@dataclass(frozen=True, slots=True)
class PlanPolicy:
    include_nexus_quality: bool = True
    daedalus_cost: float = 2.5
    default_cost: float = 1.0
    def __post_init__(self):
        if self.daedalus_cost <= 0 or self.default_cost <= 0:
            raise ValueError("plan costs must be positive")

@dataclass(frozen=True, slots=True)
class ResearchPlan:
    plan_id: str
    hypothesis_id: str
    created_ns: int
    tasks: tuple[PlanTask, ...]
    attack_suite: tuple[CounterfactualSpec, ...] = ()
    production_authorized: bool = False
    def __post_init__(self):
        if not self.plan_id or not self.hypothesis_id or self.created_ns < 0 or not self.tasks:
            raise ValueError("invalid research plan")
        if self.production_authorized:
            raise ValueError("research plans cannot authorize production")
        keys = [t.task_key for t in self.tasks]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate plan task key")
    @property
    def required_evidence_kinds(self) -> tuple[str, ...]:
        return tuple(sorted({t.evidence_kind for t in self.tasks if t.required}))
    @property
    def plan_hash(self) -> str:
        return digest({"plan_id": self.plan_id, "hypothesis_id": self.hypothesis_id, "tasks": [t.task_key for t in self.tasks], "attacks": [x.scenario_id for x in self.attack_suite]})

def _task(h: Hypothesis, key: str, system: str, task_type: str, kind: str, cost: float, info: float, relevance: float, deficit: float, novelty: float, states: tuple[str, ...] = (), required: bool = True, payload: dict[str, Any] | None = None) -> PlanTask:
    task_key = f"{key}:{digest({'h': h.hypothesis_id, 'system': system, 'type': task_type})[:10]}"
    return PlanTask(task_key, system, task_type, kind, cost, info, relevance, deficit, novelty, states, required, payload)

def default_research_plan(h: Hypothesis, *, sensors: Iterable[str] = (), policy: PlanPolicy | None = None) -> ResearchPlan:
    p = policy or PlanPolicy()
    sensor_tuple = tuple(sorted({str(x) for x in sensors if str(x)}))
    attacks = standard_attack_suite(h.hypothesis_id, h.created_ns, sensor_tuple)
    attack_payload = {"scenarios": [
        {"scenario_id": x.scenario_id, "purpose": x.purpose, "removals": list(x.removals), "delays": dict(x.delays), "randomization": x.randomization, "multipliers": dict(x.multipliers), "additive": dict(x.additive)}
        for x in attacks
    ]}
    tasks = [
        _task(h, "nexus.state", "NEXUS", "market_state_context", "market_state", p.default_cost, .75, .85, .90, .80, ("aligned_state", "factor_context", "topology")),
        _task(h, "aion.analogues", "AION", "historical_analogue_search", "historical_analogue", p.default_cost, .90, .90, .95, .75, ("strict_asof", "regime_neighbors")),
        _task(h, "argus.microstructure", "ARGUS", "microstructure_context", "microstructure_context", p.default_cost, .70, .80, .65, .70, ("evidence_tier_preserved",), required=False),
        _task(h, "athena.supervision", "ATHENA", "supervisory_context", "supervisory_context", p.default_cost, .70, .95, .80, .65, ("ood", "abstention", "quality")),
        _task(h, "daedalus.falsify", "DAEDALUS", "scientific_falsification", "research_result", p.daedalus_cost, .98, .98, 1.0, .85, ("purged_walk_forward", "holdout", "stress"), payload=attack_payload),
    ]
    if p.include_nexus_quality:
        tasks.append(_task(h, "nexus.quality", "NEXUS", "source_quality_audit", "data_quality", p.default_cost, .68, .84, .88, .60, ("source_health", "missingness", "clock_quality")))
    pid = "PLAN-" + digest({"hypothesis": h.spec_hash, "created_ns": h.created_ns, "tasks": [t.task_key for t in tasks], "attacks": [a.scenario_id for a in attacks]})[:20]
    return ResearchPlan(pid, h.hypothesis_id, h.created_ns, tuple(tasks), attacks)
