
from __future__ import annotations
from .core import BaseComponentAdapter, ComponentContext, ComponentResult

class LiquiditySweepAdapter(BaseComponentAdapter):
    component_id = "NQCM-LIQ-SWEEP-001"
    component_version = "0.5.0"
    role = "liquidity"

    def __init__(self, lookback=20, body_ratio_threshold=0.50):
        self.lookback=int(lookback)
        self.body_ratio_threshold=float(body_ratio_threshold)

    def run(self, ctx: ComponentContext) -> ComponentResult:
        self.validate_context(ctx)
        h,l,o,c = ctx.series["high"],ctx.series["low"],ctx.series["open"],ctx.series["close"]
        out=[None]*len(c)
        for i in range(self.lookback,len(c)):
            ph=max(h[i-self.lookback:i])
            pl=min(l[i-self.lookback:i])
            rng=h[i]-l[i]
            body=abs(c[i]-o[i])/(rng if rng else 1.0)
            direction=0
            if l[i] < pl and c[i] > pl and body >= self.body_ratio_threshold:
                direction=1
            elif h[i] > ph and c[i] < ph and body >= self.body_ratio_threshold:
                direction=-1
            out[i]={
                "direction":direction,
                "prior_high":ph,
                "prior_low":pl,
                "body_ratio":body,
                "event_time_index":i
            }
        return ComponentResult(
            self.component_id,self.component_version,list(ctx.timestamps),out,
            {"corpus_ids":list(ctx.corpus_ids),"lookback":self.lookback,"body_ratio_threshold":self.body_ratio_threshold},
            available_at=list(ctx.timestamps)
        )

class SessionVWAPVolumeSweepAdapter(BaseComponentAdapter):
    component_id = "EXT-SESSION-VWAP-VOL-SWEEP-001"
    component_version = "0.5.0"
    role = "liquidity"

    def __init__(self, lookback=20, min_volume_ratio=0.75):
        self.lookback=int(lookback)
        self.min_volume_ratio=float(min_volume_ratio)

    def run(self, ctx: ComponentContext) -> ComponentResult:
        self.validate_context(ctx)
        h,l,o,c,v = (ctx.series[k] for k in ["high","low","open","close","volume"])
        sessions=ctx.metadata.get("session_id")
        if sessions is None or len(sessions)!=len(c):
            raise ValueError("session_id metadata aligned to every bar is required")
        out=[None]*len(c)
        cum_pv=0.0
        cum_v=0.0
        prev_session=None
        for i in range(len(c)):
            if sessions[i] != prev_session:
                cum_pv=0.0
                cum_v=0.0
                prev_session=sessions[i]
            tp=(h[i]+l[i]+c[i])/3.0
            cum_pv += tp*v[i]
            cum_v += v[i]
            vwap = cum_pv/cum_v if cum_v else c[i]
            if i < self.lookback:
                continue
            ph=max(h[i-self.lookback:i])
            pl=min(l[i-self.lookback:i])
            avgv=sum(v[i-self.lookback:i])/self.lookback
            vol_ratio=(v[i]/avgv) if avgv else 0.0
            direction=0
            if l[i] < pl and c[i] > pl and c[i] > vwap and c[i] > o[i] and vol_ratio >= self.min_volume_ratio:
                direction=1
            elif h[i] > ph and c[i] < ph and c[i] < vwap and c[i] < o[i] and vol_ratio >= self.min_volume_ratio:
                direction=-1
            out[i]={
                "direction":direction,
                "session_vwap":vwap,
                "volume_ratio":vol_ratio,
                "event_time_index":i
            }
        return ComponentResult(
            self.component_id,self.component_version,list(ctx.timestamps),out,
            {"corpus_ids":list(ctx.corpus_ids),"lookback":self.lookback,"min_volume_ratio":self.min_volume_ratio},
            available_at=list(ctx.timestamps)
        )
