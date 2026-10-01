from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from .contracts import BookLevel, BookSnapshot, EvidenceTier


@dataclass(frozen=True)
class DepthImpactPoint:
    requested_size: float
    filled_size: float
    fill_fraction: float
    average_price: float | None
    marginal_price: float | None
    consumed_levels: int
    average_slippage_ticks_from_best: float | None
    marginal_displacement_ticks_from_best: float | None
    implementation_shortfall_ticks_from_mid: float | None
    implementation_shortfall_ticks_from_microprice: float | None
    book_exhausted: bool


@dataclass(frozen=True)
class DepthImpactCurve:
    event_time_ns: int
    sequence: int
    side: int
    tick_size: float
    best_bid: float
    best_ask: float
    spread_ticks: float
    midprice: float
    microprice: float
    visible_opposite_size: float
    capacity_at_marginal_ticks: tuple[tuple[float, float], ...]
    points: tuple[DepthImpactPoint, ...]
    evidence_tier: EvidenceTier = EvidenceTier.TRUE_DEPTH
    assumption: str = "static_visible_depth_only"
    execution_authorized: bool = False
    production_decision_authorized: bool = False


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite")
    return out


def _positive(name: str, value: float) -> float:
    out = _finite(name, value)
    if out <= 0:
        raise ValueError(f"{name} must be positive")
    return out


def _nonnegative(name: str, value: float) -> float:
    out = _finite(name, value)
    if out < 0:
        raise ValueError(f"{name} must be non-negative")
    return out


def _tick_index(raw: float, *, field: str) -> int:
    index = int(round(raw))
    if index < 0 or abs(raw - index) > 1e-6:
        raise ValueError(f"{field} is not aligned to tick_size")
    return index


def _validated_levels(
    levels: tuple[BookLevel, ...],
    *,
    side_name: str,
    tick_size: float,
    reverse: bool,
) -> tuple[BookLevel, ...]:
    if not levels:
        raise ValueError(f"{side_name} depth is required")

    seen: set[float] = set()
    validated: list[BookLevel] = []
    for level in levels:
        price = _positive(f"{side_name} price", level.price)
        size = _positive(f"{side_name} size", level.size)
        price_ticks = price / tick_size
        if abs(price_ticks - round(price_ticks)) > 1e-6:
            raise ValueError(f"{side_name} price is not aligned to tick_size")
        if price in seen:
            raise ValueError(f"duplicate {side_name} price level")
        seen.add(price)
        validated.append(BookLevel(price=price, size=size))

    return tuple(
        sorted(validated, key=lambda item: item.price, reverse=reverse)
    )


def _validate_book(
    book: BookSnapshot,
    *,
    tick_size: float,
) -> tuple[tuple[BookLevel, ...], tuple[BookLevel, ...]]:
    if isinstance(book.event_time_ns, bool) or not isinstance(book.event_time_ns, int):
        raise TypeError("book event_time_ns must be an integer")
    if book.event_time_ns < 0:
        raise ValueError("book event_time_ns must be non-negative")
    if isinstance(book.sequence, bool) or not isinstance(book.sequence, int):
        raise TypeError("book sequence must be an integer")
    if book.sequence < 0:
        raise ValueError("book sequence must be non-negative")

    bids = _validated_levels(
        book.bids,
        side_name="bid",
        tick_size=tick_size,
        reverse=True,
    )
    asks = _validated_levels(
        book.asks,
        side_name="ask",
        tick_size=tick_size,
        reverse=False,
    )
    if bids[0].price >= asks[0].price:
        raise ValueError("crossed/locked books require venue-specific handling")

    _tick_index(
        (asks[0].price - bids[0].price) / tick_size,
        field="spread",
    )
    return bids, asks


def _strictly_increasing_positive(
    name: str,
    values: Iterable[float],
) -> tuple[float, ...]:
    out = tuple(_positive(name, value) for value in values)
    if not out:
        raise ValueError(f"{name} values are required")
    if any(right <= left for left, right in zip(out, out[1:])):
        raise ValueError(f"{name} values must be strictly increasing")
    return out


def _strictly_increasing_nonnegative(
    name: str,
    values: Iterable[float],
) -> tuple[float, ...]:
    out = tuple(_nonnegative(name, value) for value in values)
    if not out:
        raise ValueError(f"{name} values are required")
    if any(right <= left for left, right in zip(out, out[1:])):
        raise ValueError(f"{name} values must be strictly increasing")
    return out


def _microprice(best_bid: BookLevel, best_ask: BookLevel) -> float:
    total = best_bid.size + best_ask.size
    return (
        best_ask.price * best_bid.size
        + best_bid.price * best_ask.size
    ) / total


def _walk(
    levels: tuple[BookLevel, ...],
    *,
    side: int,
    requested_size: float,
    best_price: float,
    midprice: float,
    microprice: float,
    tick_size: float,
) -> DepthImpactPoint:
    remaining = requested_size
    filled = 0.0
    cost = 0.0
    consumed = 0
    marginal: float | None = None

    for level in levels:
        if remaining <= 1e-12:
            break
        take = min(remaining, level.size)
        if take <= 0:
            continue
        cost += take * level.price
        filled += take
        remaining -= take
        consumed += 1
        marginal = level.price

    average = cost / filled if filled > 0 else None
    fill_fraction = min(1.0, filled / requested_size)

    return DepthImpactPoint(
        requested_size=requested_size,
        filled_size=filled,
        fill_fraction=fill_fraction,
        average_price=average,
        marginal_price=marginal,
        consumed_levels=consumed,
        average_slippage_ticks_from_best=(
            ((average - best_price) * side) / tick_size
            if average is not None
            else None
        ),
        marginal_displacement_ticks_from_best=(
            ((marginal - best_price) * side) / tick_size
            if marginal is not None
            else None
        ),
        implementation_shortfall_ticks_from_mid=(
            ((average - midprice) * side) / tick_size
            if average is not None
            else None
        ),
        implementation_shortfall_ticks_from_microprice=(
            ((average - microprice) * side) / tick_size
            if average is not None
            else None
        ),
        book_exhausted=remaining > 1e-12,
    )


def depth_impact_curve(
    book: BookSnapshot,
    *,
    side: int,
    sizes: Iterable[float],
    tick_size: float,
    capacity_threshold_ticks: Iterable[float] = (0.0, 1.0, 2.0, 4.0, 8.0),
) -> DepthImpactCurve:
    """Compute static displayed-depth impact and capacity from TRUE_DEPTH.

    This is a deterministic snapshot calculation. It says what the currently
    displayed opposite-side depth could fill if it remained unchanged while the
    hypothetical market order walked the book. It does not model latency,
    hidden liquidity, queue priority, replenishment, cancellation, market
    impact after the snapshot, or actual future fills.
    """

    if isinstance(side, bool) or side not in (-1, 1):
        raise ValueError("side must be +1 for buy or -1 for sell")

    tick = _positive("tick_size", tick_size)
    requested_sizes = _strictly_increasing_positive("size", sizes)
    thresholds = _strictly_increasing_nonnegative(
        "capacity threshold",
        capacity_threshold_ticks,
    )

    bids, asks = _validate_book(book, tick_size=tick)
    best_bid = bids[0].price
    best_ask = asks[0].price
    best_bid_level = bids[0]
    best_ask_level = asks[0]
    mid = (best_bid + best_ask) / 2.0
    micro = _microprice(best_bid_level, best_ask_level)
    opposite = asks if side == 1 else bids
    best = best_ask if side == 1 else best_bid

    capacity: list[tuple[float, float]] = []
    for threshold in thresholds:
        max_price_displacement = threshold * tick
        visible = sum(
            level.size
            for level in opposite
            if ((level.price - best) * side) <= max_price_displacement + 1e-12
        )
        capacity.append((threshold, visible))

    points = tuple(
        _walk(
            opposite,
            side=side,
            requested_size=size,
            best_price=best,
            midprice=mid,
            microprice=micro,
            tick_size=tick,
        )
        for size in requested_sizes
    )

    return DepthImpactCurve(
        event_time_ns=book.event_time_ns,
        sequence=book.sequence,
        side=side,
        tick_size=tick,
        best_bid=best_bid,
        best_ask=best_ask,
        spread_ticks=(best_ask - best_bid) / tick,
        midprice=mid,
        microprice=micro,
        visible_opposite_size=sum(level.size for level in opposite),
        capacity_at_marginal_ticks=tuple(capacity),
        points=points,
    )
