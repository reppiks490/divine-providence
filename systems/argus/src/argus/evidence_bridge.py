"""Explicit ARGUS evidence capability bridge.

The bridge is name/capability based by design. Historical ARGUS E0-E4 labels and
AION EvidenceTier integer values are different taxonomies and must never be
translated by integer coincidence.
"""
from __future__ import annotations

from dataclasses import dataclass

from .contracts import EvidenceTier, MicrostructureFeature


@dataclass(frozen=True)
class EvidenceCapability:
    label: str
    authenticated_trade: bool = False
    top_of_book: bool = False
    market_by_price: bool = False
    market_by_order: bool = False
    candle_only: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("capability label is required")
        flags = (
            self.authenticated_trade,
            self.top_of_book,
            self.market_by_price,
            self.market_by_order,
            self.candle_only,
        )
        if any(type(x) is not bool for x in flags):
            raise TypeError("capability flags must be bool")
        if self.candle_only and any(flags[:-1]):
            raise ValueError("candle-only evidence cannot also claim authenticated microstructure")


def aion_tier_name(capability: EvidenceCapability) -> str:
    """Return an AION tier *name*, never an integer.

    TRUE_DEPTH requires authenticated book evidence. Trade prints alone remain
    TRUE_TRADE. Ambiguous capability declarations fail closed.
    """
    if capability.candle_only:
        return "CANDLE_PROXY"
    if capability.market_by_order or capability.market_by_price or capability.top_of_book:
        if not capability.authenticated_trade and not (
            capability.market_by_price or capability.market_by_order or capability.top_of_book
        ):
            raise ValueError("invalid depth capability")
        return "TRUE_DEPTH"
    if capability.authenticated_trade:
        return "TRUE_TRADE"
    raise ValueError("insufficient evidence capability; abstain instead of guessing a tier")


def feature_export(feature: MicrostructureFeature) -> dict:
    """Export an ARGUS feature without silently strengthening its evidence."""
    if not isinstance(feature, MicrostructureFeature):
        raise TypeError("feature must be MicrostructureFeature")
    return {
        "name": feature.name,
        "value": float(feature.value),
        "argus_evidence_tier": feature.evidence_tier.name,
        "aion_evidence_tier_name": {
            EvidenceTier.CANDLE_PROXY: "CANDLE_PROXY",
            EvidenceTier.INFERRED_TRADE: "INFERRED_TRADE",
            EvidenceTier.TRUE_TRADE: "TRUE_TRADE",
            EvidenceTier.TRUE_DEPTH: "TRUE_DEPTH",
        }[feature.evidence_tier],
        "event_time_ns": feature.event_time_ns,
        "source_id": feature.source_id,
        "reason": feature.reason,
        "execution_authorized": False,
    }


def reject_numeric_external_tier(value) -> None:
    """Guard adapters against historical E0-E4 / AION integer confusion."""
    if isinstance(value, int):
        raise ValueError("numeric external evidence tiers are forbidden; map explicit capabilities by name")
