
from __future__ import annotations
import math
from .core import BaseComponentAdapter, ComponentContext, ComponentResult

class KNNDistanceOODAdapter(BaseComponentAdapter):
    component_id="NQCM-KNN-OOD-001"
    component_version="0.7.0"
    role="anomaly_fallback"

    def __init__(self, feature_names, lookback=120, k=5, threshold=3.0):
        self.feature_names=list(feature_names)
        self.lookback=int(lookback)
        self.k=int(k)
        self.threshold=float(threshold)
        if self.k < 1 or self.k >= self.lookback:
            raise ValueError("k must be >=1 and < lookback")

    @staticmethod
    def _mean_std(xs):
        m=sum(xs)/len(xs)
        var=sum((x-m)**2 for x in xs)/max(1,len(xs)-1)
        return m, math.sqrt(var)

    def run(self, ctx: ComponentContext) -> ComponentResult:
        self.validate_context(ctx)
        for n in self.feature_names:
            if n not in ctx.series:
                raise ValueError(f"missing feature {n}")
        out=[None]*len(ctx.timestamps)
        for i in range(self.lookback, len(ctx.timestamps)):
            lo=i-self.lookback
            mus={}; sigmas={}
            for n in self.feature_names:
                m,s=self._mean_std(ctx.series[n][lo:i])
                mus[n]=m
                sigmas[n]=s if s>1e-12 else 1.0

            current=[(ctx.series[n][i]-mus[n])/sigmas[n] for n in self.feature_names]
            dists=[]
            for j in range(lo,i):
                prior=[(ctx.series[n][j]-mus[n])/sigmas[n] for n in self.feature_names]
                d=math.sqrt(sum((a-b)**2 for a,b in zip(current,prior)))
                dists.append(d)
            dists.sort()
            score=sum(dists[:self.k])/self.k
            out[i]={
                "knn_distance":score,
                "ood":score>self.threshold,
                "abstain":score>self.threshold,
                "event_time_index":i
            }
        return ComponentResult(
            self.component_id,self.component_version,list(ctx.timestamps),out,
            {"corpus_ids":list(ctx.corpus_ids),"feature_names":self.feature_names,
             "lookback":self.lookback,"k":self.k,"threshold":self.threshold},
            available_at=list(ctx.timestamps)
        )
