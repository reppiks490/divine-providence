from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class ChangeState:
    mean: float
    variance: float
    zscore: float
    positive_cusum: float
    negative_cusum: float
    change: bool

class ChangePointEngine:
    """Online EWMA baseline + two-sided CUSUM. State updates only after each observation."""
    def __init__(self, alpha: float=.03, drift: float=.5, threshold: float=5.0):
        self.alpha=alpha; self.drift=drift; self.threshold=threshold
        self.mean=None; self.var=0.0; self.pos=0.0; self.neg=0.0

    def update(self, x: float) -> ChangeState:
        if self.mean is None:
            self.mean=float(x)
            return ChangeState(self.mean,0.0,0.0,0.0,0.0,False)
        sd=math.sqrt(max(self.var,1e-12)); z=(x-self.mean)/sd if sd>1e-6 else 0.0
        self.pos=max(0.0,self.pos+z-self.drift); self.neg=min(0.0,self.neg+z+self.drift)
        change=self.pos>self.threshold or self.neg<-self.threshold
        if change: self.pos=self.neg=0.0
        delta=x-self.mean; self.mean += self.alpha*delta
        self.var=(1-self.alpha)*(self.var+self.alpha*delta*delta)
        return ChangeState(self.mean,self.var,z,self.pos,self.neg,change)
