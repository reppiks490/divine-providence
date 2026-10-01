from __future__ import annotations

from dataclasses import dataclass
import math

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
    bids = tuple(sorted(book.bids, key=lambda x: x.price, reverse=True))
    asks = tuple(sorted(book.asks, key=lambda x: x.price))
    bb, ba = bids[0], asks[0]
    if bb.price >= ba.price:
        raise ValueError("crossed/locked snapshots require venue-specific handling")
    bdepth = sum(max(0.0, x.size) for x in bids[:levels])
    adepth = sum(max(0.0, x.size) for x in asks[:levels])
    total = bdepth + adepth
    imb = (bdepth - adepth) / total if total else 0.0
    top = max(0.0, bb.size) + max(0.0, ba.size)
    micro = (
        (ba.price * max(0.0, bb.size)) + (bb.price * max(0.0, ba.size))
    ) / top if top else (bb.price + ba.price) / 2
    return BookMapStats(
        bb.price,
        ba.price,
        ba.price - bb.price,
        micro,
        imb,
        bdepth,
        adepth,
    )


def depth_persistence(
    history: list[BookSnapshot],
    price: float,
    side: str,
    tolerance: float = 1e-12,
) -> float:
    if not history:
        return 0.0
    hits = 0
    for book in history:
        levels = book.bids if side == "bid" else book.asks
        if any(abs(x.price - price) <= tolerance and x.size > 0 for x in levels):
            hits += 1
    return hits / len(history)


@dataclass(frozen=True)
class DepthDynamics:
    """Causal TRUE_DEPTH shape/dynamics over an already-ordered snapshot history.

    Buckets are distance from each snapshot's own touch, so the feature is stable
    across price translation. Positive migration means the depth centroid moved
    away from the touch; negative migration means it moved toward the touch.
    Replenishment/cancellation are bounded per-transition rates in [0, 1].
    """

    event_time_ns: int
    sequence: int
    tick_size: float
    levels: int
    spread_ticks: int
    bid_depth_by_tick: tuple[float, ...]
    ask_depth_by_tick: tuple[float, ...]
    bid_persistence_by_tick: tuple[float, ...]
    ask_persistence_by_tick: tuple[float, ...]
    bid_replenishment_rate_by_tick: tuple[float, ...]
    ask_replenishment_rate_by_tick: tuple[float, ...]
    bid_cancellation_rate_by_tick: tuple[float, ...]
    ask_cancellation_rate_by_tick: tuple[float, ...]
    bid_centroid_ticks: float
    ask_centroid_ticks: float
    bid_migration_ticks: float
    ask_migration_ticks: float
    bid_concentration: float
    ask_concentration: float
    evidence_tier: EvidenceTier = EvidenceTier.TRUE_DEPTH


def _positive_finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    out = float(value)
    if not math.isfinite(out) or out <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return out


def _ordered_depth(book: BookSnapshot) -> tuple[tuple, tuple]:
    if not isinstance(book.event_time_ns, int) or isinstance(book.event_time_ns, bool) or book.event_time_ns < 0:
        raise ValueError("book event_time_ns must be a non-negative integer")
    if not isinstance(book.sequence, int) or isinstance(book.sequence, bool) or book.sequence < 0:
        raise ValueError("book sequence must be a non-negative integer")
    if not book.bids or not book.asks:
        raise ValueError("two-sided depth is required")

    bids = tuple(sorted(book.bids, key=lambda x: x.price, reverse=True))
    asks = tuple(sorted(book.asks, key=lambda x: x.price))
    for side_name, rows in (("bid", bids), ("ask", asks)):
        seen: set[float] = set()
        for row in rows:
            price = float(row.price)
            size = float(row.size)
            if not math.isfinite(price) or not math.isfinite(size) or size <= 0:
                raise ValueError(f"{side_name} levels require finite price and positive size")
            if price in seen:
                raise ValueError(f"duplicate {side_name} price level")
            seen.add(price)
    if bids[0].price >= asks[0].price:
        raise ValueError("crossed/locked snapshots require venue-specific handling")
    return bids, asks


def _tick_index(raw: float, *, field: str) -> int:
    index = int(round(raw))
    if index < 0 or abs(raw - index) > 1e-6:
        raise ValueError(f"{field} is not aligned to tick_size")
    return index


def _bucket_depth(
    book: BookSnapshot,
    *,
    side: str,
    tick_size: float,
    levels: int,
) -> tuple[float, ...]:
    bids, asks = _ordered_depth(book)
    rows = bids if side == "bid" else asks
    touch = float(rows[0].price)
    out = [0.0] * levels
    for row in rows:
        distance = (
            (touch - float(row.price)) / tick_size
            if side == "bid"
            else (float(row.price) - touch) / tick_size
        )
        index = _tick_index(distance, field=f"{side} level")
        if index < levels:
            out[index] += float(row.size)
    return tuple(out)


def _centroid(depth: tuple[float, ...]) -> float:
    total = sum(depth)
    return sum(index * size for index, size in enumerate(depth)) / total if total else 0.0


def _concentration(depth: tuple[float, ...]) -> float:
    total = sum(depth)
    if total <= 0:
        return 0.0
    return sum((size / total) ** 2 for size in depth)


def _persistence(rows: list[tuple[float, ...]]) -> tuple[float, ...]:
    if not rows:
        return ()
    count = float(len(rows))
    return tuple(
        sum(1 for row in rows if row[index] > 0) / count
        for index in range(len(rows[0]))
    )


def _transition_rates(
    rows: list[tuple[float, ...]],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if not rows:
        return (), ()
    width = len(rows[0])
    if len(rows) == 1:
        zeros = tuple(0.0 for _ in range(width))
        return zeros, zeros

    replenishment = [0.0] * width
    cancellation = [0.0] * width
    transitions = len(rows) - 1
    for previous, current in zip(rows, rows[1:]):
        for index, (before, after) in enumerate(zip(previous, current)):
            scale = max(before, after)
            if scale <= 0:
                continue
            replenishment[index] += max(after - before, 0.0) / scale
            cancellation[index] += max(before - after, 0.0) / scale
    return (
        tuple(value / transitions for value in replenishment),
        tuple(value / transitions for value in cancellation),
    )


def depth_dynamics(
    history: list[BookSnapshot],
    *,
    tick_size: float,
    levels: int = 10,
) -> DepthDynamics:
    """Build deterministic distance-to-touch liquidity dynamics from TRUE_DEPTH.

    The caller must supply only snapshots that were actually available by the
    decision instant. This function additionally rejects out-of-order history,
    crossed books, duplicate levels, invalid sizes and off-tick geometry so a
    corrupted snapshot cannot silently become a microstructure feature.
    """

    tick = _positive_finite("tick_size", tick_size)
    if not isinstance(levels, int) or isinstance(levels, bool) or levels < 1:
        raise ValueError("levels must be a positive integer")
    if not history:
        raise ValueError("at least one book snapshot is required")

    previous_key: tuple[int, int] | None = None
    bid_rows: list[tuple[float, ...]] = []
    ask_rows: list[tuple[float, ...]] = []
    for book in history:
        bids, asks = _ordered_depth(book)
        key = (book.event_time_ns, book.sequence)
        if previous_key is not None and key <= previous_key:
            raise ValueError("book history must be strictly ordered by event_time_ns and sequence")
        previous_key = key

        spread_raw = (float(asks[0].price) - float(bids[0].price)) / tick
        _tick_index(spread_raw, field="spread")
        bid_rows.append(_bucket_depth(book, side="bid", tick_size=tick, levels=levels))
        ask_rows.append(_bucket_depth(book, side="ask", tick_size=tick, levels=levels))

    current = history[-1]
    current_bids, current_asks = _ordered_depth(current)
    spread_ticks = _tick_index(
        (float(current_asks[0].price) - float(current_bids[0].price)) / tick,
        field="spread",
    )

    bid_replenishment, bid_cancellation = _transition_rates(bid_rows)
    ask_replenishment, ask_cancellation = _transition_rates(ask_rows)
    bid_centroid = _centroid(bid_rows[-1])
    ask_centroid = _centroid(ask_rows[-1])
    prior_bid_centroid = _centroid(bid_rows[-2]) if len(bid_rows) > 1 else bid_centroid
    prior_ask_centroid = _centroid(ask_rows[-2]) if len(ask_rows) > 1 else ask_centroid

    return DepthDynamics(
        event_time_ns=current.event_time_ns,
        sequence=current.sequence,
        tick_size=tick,
        levels=levels,
        spread_ticks=spread_ticks,
        bid_depth_by_tick=bid_rows[-1],
        ask_depth_by_tick=ask_rows[-1],
        bid_persistence_by_tick=_persistence(bid_rows),
        ask_persistence_by_tick=_persistence(ask_rows),
        bid_replenishment_rate_by_tick=bid_replenishment,
        ask_replenishment_rate_by_tick=ask_replenishment,
        bid_cancellation_rate_by_tick=bid_cancellation,
        ask_cancellation_rate_by_tick=ask_cancellation,
        bid_centroid_ticks=bid_centroid,
        ask_centroid_ticks=ask_centroid,
        bid_migration_ticks=bid_centroid - prior_bid_centroid,
        ask_migration_ticks=ask_centroid - prior_ask_centroid,
        bid_concentration=_concentration(bid_rows[-1]),
        ask_concentration=_concentration(ask_rows[-1]),
    )
