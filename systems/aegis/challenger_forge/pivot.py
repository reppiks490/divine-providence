
from __future__ import annotations
from .core import BaseComponentAdapter, ComponentContext, ComponentResult

def _is_pivot_high(high, i, left, right):
    if i-left < 0 or i+right >= len(high):
        return False
    x = high[i]
    return all(x > high[j] for j in range(i-left, i)) and all(x >= high[j] for j in range(i+1, i+right+1))

def _is_pivot_low(low, i, left, right):
    if i-left < 0 or i+right >= len(low):
        return False
    x = low[i]
    return all(x < low[j] for j in range(i-left, i)) and all(x <= low[j] for j in range(i+1, i+right+1))

class ConfirmedPivotAdapter(BaseComponentAdapter):
    component_id = "OGE-STRUCT-PIVOT-001"
    component_version = "0.3.0"
    role = "structure"

    def __init__(self, left=2, right=2):
        self.left = int(left)
        self.right = int(right)
        self.causal_output_delay_bars = self.right

    def run(self, ctx: ComponentContext) -> ComponentResult:
        self.validate_context(ctx)
        high = ctx.series["high"]
        low = ctx.series["low"]
        out = [None] * len(high)
        # Critical causal rule: a pivot at origin i is emitted at confirmation bar i+right.
        for origin in range(self.left, len(high) - self.right):
            confirm = origin + self.right
            if _is_pivot_high(high, origin, self.left, self.right):
                out[confirm] = {"kind": "pivot_high", "origin_index": origin, "confirmed_at_index": confirm}
            elif _is_pivot_low(low, origin, self.left, self.right):
                out[confirm] = {"kind": "pivot_low", "origin_index": origin, "confirmed_at_index": confirm}
        return ComponentResult(
            self.component_id, self.component_version, list(ctx.timestamps), out,
            {"corpus_ids": list(ctx.corpus_ids), "left": self.left, "right": self.right, "causal": True}
        )

class LeakyBackdatedPivotAdapter(BaseComponentAdapter):
    component_id = "NEGCTRL-LEAKY-PIVOT-001"
    component_version = "0.3.0"
    role = "negative_control"

    def __init__(self, left=2, right=2):
        self.left = int(left)
        self.right = int(right)

    def run(self, ctx: ComponentContext) -> ComponentResult:
        self.validate_context(ctx)
        high = ctx.series["high"]
        low = ctx.series["low"]
        out = [None] * len(high)
        # Deliberate anti-pattern: uses future right bars but writes the signal at origin.
        for origin in range(self.left, len(high) - self.right):
            if _is_pivot_high(high, origin, self.left, self.right):
                out[origin] = {"kind": "pivot_high", "origin_index": origin, "backdated": True}
            elif _is_pivot_low(low, origin, self.left, self.right):
                out[origin] = {"kind": "pivot_low", "origin_index": origin, "backdated": True}
        return ComponentResult(
            self.component_id, self.component_version, list(ctx.timestamps), out,
            {"corpus_ids": list(ctx.corpus_ids), "left": self.left, "right": self.right, "causal": False}
        )
