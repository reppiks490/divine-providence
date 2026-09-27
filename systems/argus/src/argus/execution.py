from __future__ import annotations

from dataclasses import dataclass
from .contracts import BookSnapshot
from .bookmap import book_stats


@dataclass(frozen=True)
class ExecutionEstimate:
    side: int
    requested_size: float
    filled_size: float
    average_price: float | None
    best_price: float
    slippage: float | None
    unfilled_size: float


def walk_book(book: BookSnapshot, side: int, size: float) -> ExecutionEstimate:
    if side not in (-1,1) or size<=0:
        raise ValueError("side must be +/-1 and size positive")
    stats=book_stats(book)
    levels=sorted(book.asks,key=lambda x:x.price) if side==1 else sorted(book.bids,key=lambda x:x.price,reverse=True)
    remaining=float(size); cost=0.0; filled=0.0
    for lvl in levels:
        take=min(remaining,max(0.0,lvl.size))
        cost += take*lvl.price; filled += take; remaining -= take
        if remaining<=1e-12: break
    avg=cost/filled if filled else None
    best=stats.best_ask if side==1 else stats.best_bid
    slip=(avg-best)*side if avg is not None else None
    return ExecutionEstimate(side,size,filled,avg,best,slip,max(0.0,remaining))
