from __future__ import annotations

from .contracts import EvidenceTier, MicrostructureFeature


def evidence_weight(tier: EvidenceTier) -> float:
    return {EvidenceTier.CANDLE_PROXY:.25,EvidenceTier.INFERRED_TRADE:.5,EvidenceTier.TRUE_TRADE:.75,EvidenceTier.TRUE_DEPTH:1.0}[tier]


def fuse(features: list[MicrostructureFeature]) -> tuple[float, EvidenceTier]:
    if not features:
        return 0.0, EvidenceTier.CANDLE_PROXY
    denom=sum(evidence_weight(f.evidence_tier) for f in features)
    score=sum(max(-1,min(1,float(f.value)))*evidence_weight(f.evidence_tier) for f in features)/denom if denom else 0.0
    # Overall evidence cannot be claimed stronger than the strongest actual input, but the caller
    # must retain per-feature lineage; this value is only a summary tier.
    return score, max(f.evidence_tier for f in features)

def require_true_depth(features: list[MicrostructureFeature]) -> None:
    if not any(f.evidence_tier is EvidenceTier.TRUE_DEPTH for f in features):
        raise ValueError("operation requires actual depth/L2 evidence; candle/trade proxies are insufficient")
