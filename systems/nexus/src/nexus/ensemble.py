from __future__ import annotations
from dataclasses import dataclass
import pandas as pd
from .synthetic import FactorEnsembleEngine,EnsembleDefinition as _CoreEnsembleDefinition

@dataclass(frozen=True)
class EnsembleDefinition:
    name:str;components:tuple[str,...]
    methods:tuple[str,...]=('adaptive_pca','inverse_vol','equal')
    window:int=120;min_periods:int=40;rebalance_every:int=10;clip_z:float=6.0;max_component_weight:float=1.0

class AdaptiveFactorEnsemble:
    """Compatibility facade for the v2 factor ensemble with stability diagnostics."""
    def build(self,values:pd.DataFrame,definition:EnsembleDefinition)->pd.DataFrame:
        core=_CoreEnsembleDefinition(definition.name,definition.components,definition.methods,definition.window,definition.min_periods,definition.rebalance_every,definition.clip_z,definition.max_component_weight)
        return FactorEnsembleEngine().build(values,core)
