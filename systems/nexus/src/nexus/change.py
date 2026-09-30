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
        if not math.isfinite(float(alpha)) or not (0.0 < float(alpha) <= 1.0):
            raise ValueError("alpha must be finite and in (0,1]")
        if not math.isfinite(float(drift)) or float(drift) < 0.0:
            raise ValueError("drift must be finite and non-negative")
        if not math.isfinite(float(threshold)) or float(threshold) <= 0.0:
            raise ValueError("threshold must be finite and positive")
        self.alpha=float(alpha); self.drift=float(drift); self.threshold=float(threshold)
        self.mean=None; self.var=0.0; self.pos=0.0; self.neg=0.0

    def update(self, x: float) -> ChangeState:
        x=float(x)
        if not math.isfinite(x):
            raise ValueError("change-point observation must be finite")
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
