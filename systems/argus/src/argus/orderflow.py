from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from .contracts import EvidenceTier, Trade


@dataclass(frozen=True)
class FlowStats:
    signed_volume: float
    total_volume: float
    imbalance: float
    large_trade_concentration: float
    toxicity: float
    evidence_tier: EvidenceTier


def classify_tick_rule(trades: list[Trade]) -> list[int]:
    sides: list[int] = []
    last_side = 0
    last_price = None
    for t in trades:
        if t.side in (-1, 1):
            side = int(t.side)
        elif last_price is None or t.price == last_price:
            side = last_side
        else:
            side = 1 if t.price > last_price else -1
        sides.append(side)
        if side:
            last_side = side
        last_price = t.price
    return sides


def flow_stats(trades: list[Trade]) -> FlowStats:
    if not trades:
        return FlowStats(0,0,0,0,0,EvidenceTier.INFERRED_TRADE)
    explicit = all(t.side in (-1,1) for t in trades)
    sides = classify_tick_rule(trades)
    vols = [max(0.0, float(t.size)) for t in trades]
    total = sum(vols)
    signed = sum(s*v for s,v in zip(sides,vols))
    imbalance = signed/total if total else 0.0
    # concentration distinguishes flow dominated by a few prints from broad participation
    denom = sum(v*v for v in vols)
    concentration = (max(vols)**2/denom) if denom else 0.0
    # bounded directional toxicity proxy: magnitude adjusted by participation concentration
    toxicity = min(1.0, abs(imbalance) * sqrt(max(concentration, 1.0/len(vols))))
    tier = EvidenceTier.TRUE_TRADE if explicit else EvidenceTier.INFERRED_TRADE
    return FlowStats(signed,total,imbalance,concentration,toxicity,tier)
