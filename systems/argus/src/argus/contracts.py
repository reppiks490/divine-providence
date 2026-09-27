from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class EvidenceTier(IntEnum):
    CANDLE_PROXY = 1
    INFERRED_TRADE = 2
    TRUE_TRADE = 3
    TRUE_DEPTH = 4


@dataclass(frozen=True)
class Trade:
    event_time_ns: int
    price: float
    size: float
    side: int | None = None  # +1 aggressive buy, -1 aggressive sell; None means unknown
    sequence: int = 0


@dataclass(frozen=True)
class BookLevel:
    price: float
    size: float


@dataclass(frozen=True)
class BookSnapshot:
    event_time_ns: int
    bids: tuple[BookLevel, ...]
    asks: tuple[BookLevel, ...]
    sequence: int = 0


@dataclass(frozen=True)
class MicrostructureFeature:
    name: str
    value: float
    evidence_tier: EvidenceTier
    event_time_ns: int
    source_id: str
    reason: str = ""


@dataclass(frozen=True)
class OrderBlockCandidate:
    direction: int
    lower: float
    upper: float
    origin_time_ns: int
    impulse_score: float
    flow_score: float
    liquidity_score: float
    survival_score: float
    evidence_tier: EvidenceTier
