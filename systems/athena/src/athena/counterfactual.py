from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Scenario:
    name: str
    multipliers: Mapping[str, float]
    additive: Mapping[str, float]
    forced_flags: tuple[str, ...] = ()


def apply_scenario(state: Mapping[str, float], scenario: Scenario) -> dict[str, float]:
    out = dict(state)
    for k, m in scenario.multipliers.items():
        if k in out:
            out[k] = out[k] * float(m)
    for k, a in scenario.additive.items():
        out[k] = out.get(k, 0.0) + float(a)
    return out
