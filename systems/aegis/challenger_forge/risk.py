
from __future__ import annotations
from .core import BaseComponentAdapter, ComponentContext, ComponentResult

class ATRRiskAdapter(BaseComponentAdapter):
    component_id = "OGE-RISK-ATR-001"
    component_version = "0.3.0"
    role = "risk"

    def __init__(self, length=14, stop_multiple=1.5, target_rr=2.0):
        self.length = int(length)
        self.stop_multiple = float(stop_multiple)
        self.target_rr = float(target_rr)

    def run(self, ctx: ComponentContext) -> ComponentResult:
        self.validate_context(ctx)
        high, low, close = ctx.series["high"], ctx.series["low"], ctx.series["close"]
        n = len(close)
        tr = [None] * n
        for i in range(n):
            if i == 0:
                tr[i] = high[i] - low[i]
            else:
                tr[i] = max(high[i] - low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1]))
        atr = [None] * n
        for i in range(self.length-1, n):
            atr[i] = sum(tr[i-self.length+1:i+1]) / self.length

        out = [None] * n
        for i, a in enumerate(atr):
            if a is not None:
                stop = a * self.stop_multiple
                out[i] = {"atr": a, "stop_distance": stop, "target_distance": stop * self.target_rr}
        return ComponentResult(
            self.component_id, self.component_version, list(ctx.timestamps), out,
            {"corpus_ids": list(ctx.corpus_ids), "length": self.length, "stop_multiple": self.stop_multiple, "target_rr": self.target_rr}
        )
