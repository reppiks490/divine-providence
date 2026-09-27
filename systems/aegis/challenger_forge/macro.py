
from __future__ import annotations
from .core import BaseComponentAdapter, ComponentContext, ComponentResult

class DXYMacroPressureAdapter(BaseComponentAdapter):
    component_id = "OGE-MACRO-DXY-001"
    component_version = "0.3.0"
    role = "feature"

    def __init__(self, corr_window=20, slope_window=5, min_abs_corr=0.15):
        self.corr_window = int(corr_window)
        self.slope_window = int(slope_window)
        self.min_abs_corr = float(min_abs_corr)

    @staticmethod
    def _corr(a, b):
        n = len(a)
        if n < 2:
            return None
        ma, mb = sum(a)/n, sum(b)/n
        va = sum((x-ma)**2 for x in a)
        vb = sum((y-mb)**2 for y in b)
        if va <= 0 or vb <= 0:
            return 0.0
        cov = sum((x-ma)*(y-mb) for x,y in zip(a,b))
        return cov / (va*vb)**0.5

    def run(self, ctx: ComponentContext) -> ComponentResult:
        self.validate_context(ctx)
        asset = ctx.series["asset_return"]
        dxy = ctx.series["dxy_return"]
        dxy_level = ctx.series["dxy_level"]
        n = len(asset)
        out = [None] * n
        for i in range(n):
            if i+1 < max(self.corr_window, self.slope_window):
                continue
            c = self._corr(asset[i-self.corr_window+1:i+1], dxy[i-self.corr_window+1:i+1])
            slope = dxy_level[i] - dxy_level[i-self.slope_window+1]
            stable_inverse = c is not None and c <= -self.min_abs_corr
            pressure = -1 if (stable_inverse and slope > 0) else (1 if (stable_inverse and slope < 0) else 0)
            out[i] = {"rolling_corr": c, "dxy_slope": slope, "macro_pressure": pressure, "abstain": not stable_inverse}
        return ComponentResult(
            self.component_id, self.component_version, list(ctx.timestamps), out,
            {"corpus_ids": list(ctx.corpus_ids), "corr_window": self.corr_window, "slope_window": self.slope_window}
        )
