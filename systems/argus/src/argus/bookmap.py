from __future__ import annotations

from dataclasses import dataclass
from .contracts import BookSnapshot, EvidenceTier


@dataclass(frozen=True)
class BookMapStats:
    best_bid: float
    best_ask: float
    spread: float
    microprice: float
    top_depth_imbalance: float
    bid_depth: float
    ask_depth: float
    evidence_tier: EvidenceTier = EvidenceTier.TRUE_DEPTH


def book_stats(book: BookSnapshot, levels: int = 5) -> BookMapStats:
    if not book.bids or not book.asks:
        raise ValueError("two-sided depth is required")
    bids=tuple(sorted(book.bids, key=lambda x:x.price, reverse=True))
    asks=tuple(sorted(book.asks, key=lambda x:x.price))
    bb, ba=bids[0], asks[0]
    if bb.price >= ba.price:
        raise ValueError("crossed/locked snapshots require venue-specific handling")
    bdepth=sum(max(0.0,x.size) for x in bids[:levels])
    adepth=sum(max(0.0,x.size) for x in asks[:levels])
    total=bdepth+adepth
    imb=(bdepth-adepth)/total if total else 0.0
    top= max(0.0,bb.size)+max(0.0,ba.size)
    micro=((ba.price*max(0.0,bb.size))+(bb.price*max(0.0,ba.size)))/top if top else (bb.price+ba.price)/2
    return BookMapStats(bb.price,ba.price,ba.price-bb.price,micro,imb,bdepth,adepth)


def depth_persistence(history: list[BookSnapshot], price: float, side: str, tolerance: float = 1e-12) -> float:
    if not history:
        return 0.0
    hits=0
    for b in history:
        levels=b.bids if side=="bid" else b.asks
        if any(abs(x.price-price)<=tolerance and x.size>0 for x in levels):
            hits += 1
    return hits/len(history)
