from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .synthetic import AdaptiveTickerEngine, SyntheticTickerDefinition

@dataclass(frozen=True)
class AblationResult:
    removed: str
    overlap: int
    correlation_to_full: float
    mean_abs_displacement: float
    tail_displacement_95: float

class SensorAblationEngine:
    """Measure dependence of a synthetic ticker on one sensor or an entire sensor cluster."""
    def _score(self,full:pd.DataFrame,sub:pd.DataFrame,removed:str)->AblationResult|None:
        z=pd.concat([full['value'].rename('full'),sub['value'].rename('sub')],axis=1).dropna()
        if not len(z): return None
        disp=(z['full']-z['sub']).abs()
        corr=float(z['full'].corr(z['sub'])) if len(z)>1 else float('nan')
        return AblationResult(removed,len(z),corr,float(disp.mean()),float(disp.quantile(.95)))

    def evaluate(self, values:pd.DataFrame, definition:SyntheticTickerDefinition) -> list[AblationResult]:
        eng=AdaptiveTickerEngine(); full=eng.build(values,definition); out=[]
        for removed in definition.components:
            keep=tuple(c for c in definition.components if c!=removed)
            if not keep: continue
            d=SyntheticTickerDefinition(definition.name+f":minus:{removed}",keep,definition.method,definition.window,definition.min_periods,definition.rebalance_every,definition.clip_z,definition.max_component_weight)
            r=self._score(full,eng.build(values,d),removed)
            if r: out.append(r)
        return sorted(out,key=lambda x:x.mean_abs_displacement,reverse=True)

    def evaluate_clusters(self,values:pd.DataFrame,definition:SyntheticTickerDefinition,clusters:dict[str,tuple[str,...]])->list[AblationResult]:
        eng=AdaptiveTickerEngine(); full=eng.build(values,definition); out=[]
        base=set(definition.components)
        for name,members in sorted(clusters.items()):
            keep=tuple(c for c in definition.components if c not in set(members))
            if not keep or set(keep)==base: continue
            d=SyntheticTickerDefinition(definition.name+f":minus-cluster:{name}",keep,definition.method,definition.window,definition.min_periods,definition.rebalance_every,definition.clip_z,definition.max_component_weight)
            r=self._score(full,eng.build(values,d),f"cluster:{name}")
            if r: out.append(r)
        return sorted(out,key=lambda x:x.mean_abs_displacement,reverse=True)
