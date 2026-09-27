from __future__ import annotations

from .contracts import EvidenceTier, OrderBlockCandidate


def score_order_block(*, direction:int, lower:float, upper:float, origin_time_ns:int,
                      displacement_atr:float, signed_flow_alignment:float,
                      depth_vacuum:float, revisit_rejection:float,
                      evidence_tier:EvidenceTier) -> OrderBlockCandidate:
    if direction not in (-1,1) or lower>=upper:
        raise ValueError("invalid order-block geometry")
    impulse=max(0.0,min(1.0,displacement_atr/3.0))
    flow=max(0.0,min(1.0,(signed_flow_alignment+1.0)/2.0))
    liquidity=max(0.0,min(1.0,depth_vacuum))
    survival=max(0.0,min(1.0,revisit_rejection))
    # No single component can fully compensate for zero evidence elsewhere.
    return OrderBlockCandidate(direction,lower,upper,origin_time_ns,impulse,flow,liquidity,survival,evidence_tier)

def composite_score(block: OrderBlockCandidate) -> float:
    base=(block.impulse_score*block.flow_score*block.liquidity_score*block.survival_score)**0.25
    tier_factor={EvidenceTier.CANDLE_PROXY:.45,EvidenceTier.INFERRED_TRADE:.65,EvidenceTier.TRUE_TRADE:.82,EvidenceTier.TRUE_DEPTH:1.0}[block.evidence_tier]
    return base*tier_factor
