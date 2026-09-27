
from __future__ import annotations
import math
from .core import BaseComponentAdapter, ComponentContext, ComponentResult

class VolatilityRegimeAdapter(BaseComponentAdapter):
    component_id="NQCM-VOL-REGIME-001"
    component_version="0.7.0"
    role="regime"

    def __init__(self, short_window=12, long_window=48, low_ratio=0.75, high_ratio=1.50):
        self.short_window=int(short_window)
        self.long_window=int(long_window)
        self.low_ratio=float(low_ratio)
        self.high_ratio=float(high_ratio)

    @staticmethod
    def _std(xs):
        if len(xs)<2: return 0.0
        m=sum(xs)/len(xs)
        return math.sqrt(sum((x-m)**2 for x in xs)/(len(xs)-1))

    def run(self, ctx: ComponentContext) -> ComponentResult:
        self.validate_context(ctx)
        close=ctx.series["close"]
        ret=[0.0]
        for i in range(1,len(close)):
            ret.append(math.log(close[i]/close[i-1]) if close[i-1] and close[i]>0 else 0.0)
        out=[None]*len(close)
        for i in range(self.long_window, len(close)):
            short=self._std(ret[i-self.short_window+1:i+1])
            long=self._std(ret[i-self.long_window+1:i+1])
            ratio=(short/long) if long>0 else 1.0
            regime="LOW" if ratio<self.low_ratio else ("HIGH" if ratio>self.high_ratio else "NORMAL")
            out[i]={
                "regime":regime,
                "short_vol":short,
                "long_vol":long,
                "vol_ratio":ratio,
                "event_time_index":i
            }
        return ComponentResult(
            self.component_id,self.component_version,list(ctx.timestamps),out,
            {"corpus_ids":list(ctx.corpus_ids),"short_window":self.short_window,"long_window":self.long_window,
             "low_ratio":self.low_ratio,"high_ratio":self.high_ratio},
            available_at=list(ctx.timestamps)
        )
