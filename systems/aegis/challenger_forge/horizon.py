from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class HorizonSignal:
    horizon: str
    direction: int
    confidence: float

def reconcile_horizons(signals, min_confidence=0.5):
    active=[s for s in signals if s.direction in (-1,1) and s.confidence>=min_confidence]
    if not active:
        return {"direction":0,"abstain":True,"reason":"no_confident_signal","active":0}
    dirs={s.direction for s in active}
    if len(dirs)>1:
        return {"direction":0,"abstain":True,"reason":"horizon_disagreement","active":len(active)}
    d=active[0].direction
    return {"direction":d,"abstain":False,"reason":"consensus","active":len(active),
            "mean_confidence":sum(s.confidence for s in active)/len(active)}
