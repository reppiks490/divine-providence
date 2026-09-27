from __future__ import annotations
from dataclasses import dataclass, field
from typing import Mapping

@dataclass(frozen=True, slots=True)
class CounterfactualSpec:
    scenario_id: str
    hypothesis_id: str
    created_ns: int
    removals: tuple[str, ...] = ()
    delays: Mapping[str, int] = field(default_factory=dict)
    randomization: str | None = None
    multipliers: Mapping[str, float] = field(default_factory=dict)
    additive: Mapping[str, float] = field(default_factory=dict)
    purpose: str = "stress_test"
    def __post_init__(self):
        if not self.scenario_id or not self.hypothesis_id or self.created_ns < 0:
            raise ValueError("invalid counterfactual")
        if any(int(v) < 0 for v in self.delays.values()):
            raise ValueError("delays must be non-negative")

def standard_attack_suite(hypothesis_id: str, created_ns: int, sensors: tuple[str, ...]) -> tuple[CounterfactualSpec, ...]:
    out = [CounterfactualSpec(f"ablate::{s}", hypothesis_id, created_ns, removals=(s,), purpose="sensor_ablation") for s in sensors]
    out += [
        CounterfactualSpec("delay::features", hypothesis_id, created_ns, delays={"all_features": 1}, purpose="leakage_attack"),
        CounterfactualSpec("shuffle::dates", hypothesis_id, created_ns, randomization="permute_dates", purpose="null_attack"),
        CounterfactualSpec("cost::2x", hypothesis_id, created_ns, multipliers={"transaction_cost": 2.0}, purpose="cost_stress"),
        CounterfactualSpec("threshold::wide", hypothesis_id, created_ns, multipliers={"decision_threshold": 1.10}, purpose="threshold_stress"),
    ]
    return tuple(out)
