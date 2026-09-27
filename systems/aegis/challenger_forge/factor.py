from __future__ import annotations
from .core import BaseComponentAdapter, ComponentContext, ComponentResult

class PITFactorCorrelationAdapter(BaseComponentAdapter):
    component_id='NQCM-FACTOR-001'
    component_version='0.8.0'
    role='feature'

    def __init__(self, factor_names, weights=None, window=48, max_pairwise_corr=0.95):
        self.factor_names=list(factor_names)
        self.weights=weights or {n:1.0/len(self.factor_names) for n in self.factor_names}
        self.window=int(window)
        self.max_pairwise_corr=float(max_pairwise_corr)

    @staticmethod
    def corr(a,b):
        if len(a)<2: return 0.0
        ma=sum(a)/len(a); mb=sum(b)/len(b)
        va=sum((x-ma)**2 for x in a); vb=sum((y-mb)**2 for y in b)
        if va<=1e-20 or vb<=1e-20: return 0.0
        return sum((x-ma)*(y-mb) for x,y in zip(a,b))/(va*vb)**0.5

    def run(self, ctx: ComponentContext) -> ComponentResult:
        self.validate_context(ctx)
        target=ctx.series['target_return']
        for n in self.factor_names:
            if n not in ctx.series: raise ValueError(f'missing factor {n}')
        avail=ctx.metadata.get('factor_available_at')
        if avail is not None:
            if set(avail.keys()) != set(self.factor_names): raise ValueError('factor_available_at must cover every factor')
            for n in self.factor_names:
                if len(avail[n]) != len(ctx.timestamps): raise ValueError('availability length mismatch')
                for ts,a in zip(ctx.timestamps,avail[n]):
                    if a>ts: raise ValueError(f'future factor availability for {n}')
        out=[None]*len(target)
        for i in range(self.window-1,len(target)):
            lo=i-self.window+1
            cs={n:self.corr(target[lo:i+1],ctx.series[n][lo:i+1]) for n in self.factor_names}
            weighted=sum(self.weights.get(n,0.0)*cs[n] for n in self.factor_names)
            max_pc=0.0
            for ai,a in enumerate(self.factor_names):
                for b in self.factor_names[ai+1:]:
                    max_pc=max(max_pc,abs(self.corr(ctx.series[a][lo:i+1],ctx.series[b][lo:i+1])))
            out[i]={'factor_score':weighted,'correlations':cs,'max_pairwise_factor_corr':max_pc,
                    'multicollinearity_warning':max_pc>=self.max_pairwise_corr,'event_time_index':i}
        return ComponentResult(self.component_id,self.component_version,list(ctx.timestamps),out,
                               {'corpus_ids':list(ctx.corpus_ids),'factors':self.factor_names,'weights':self.weights,
                                'window':self.window,'max_pairwise_corr':self.max_pairwise_corr},
                               available_at=list(ctx.timestamps))
