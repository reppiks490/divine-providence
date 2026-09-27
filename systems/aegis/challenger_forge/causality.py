
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List
from .core import BaseComponentAdapter, ComponentContext

@dataclass
class CausalityViolation:
    index: int
    timestamp: int
    full_value: Any
    prefix_value: Any

@dataclass
class CausalityAudit:
    component_id: str
    passed: bool
    violations: List[CausalityViolation]
    checked_points: int

def audit_prefix_invariance(adapter: BaseComponentAdapter, ctx: ComponentContext, warmup: int = 1) -> CausalityAudit:
    """
    For every index t, compare the component's output at t when run on the full
    dataset against the output at t when the component only sees observations
    through t. Any mismatch is evidence that the full-history result at t
    depends on future observations.
    """
    adapter.validate_context(ctx)
    full = adapter.run(ctx)
    violations = []
    checked = 0

    for i in range(max(0, warmup), len(ctx.timestamps)):
        prefix_ctx = ctx.prefix(i + 1)
        prefix = adapter.run(prefix_ctx)
        full_value = full.values[i]
        prefix_value = prefix.values[i]
        checked += 1
        if full_value != prefix_value:
            violations.append(
                CausalityViolation(
                    index=i,
                    timestamp=ctx.timestamps[i],
                    full_value=full_value,
                    prefix_value=prefix_value,
                )
            )

    return CausalityAudit(
        component_id=adapter.component_id,
        passed=(len(violations) == 0),
        violations=violations,
        checked_points=checked,
    )
