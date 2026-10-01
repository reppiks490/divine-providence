from __future__ import annotations

from dataclasses import dataclass
import math

from .contracts import EvidenceTier, Trade
from .flow_dynamics import flow_dynamics
from .orderflow import classify_tick_rule


@dataclass(frozen=True)
class AggressiveRun:
    """One consecutive same-side aggressor sequence.

    The run is descriptive. It does not assert trader identity, intent, stop
    hunting, institutional participation, or execution authority.
    """

    side: int
    start_event_time_ns: int
    end_event_time_ns: int
    start_sequence: int
    end_sequence: int
    trade_count: int
    total_volume: float
    vwap: float
    start_price: float
    end_price: float
    min_price: float
    max_price: float
    distinct_price_levels: int
    aligned_travel_ticks: float
    range_ticks: float
    path_length_ticks: float
    directional_efficiency: float
    duration_ns: int
    max_interarrival_ns: int
    volume_concentration: float
    evidence_tier: EvidenceTier


def _build_run(
    rows: list[tuple[Trade, int, bool]],
    *,
    tick_size: float,
) -> AggressiveRun:
    if not rows:
        raise ValueError("aggressive run cannot be empty")
    side = rows[0][1]
    if side not in (-1, 1) or any(item_side != side for _, item_side, _ in rows):
        raise ValueError("aggressive run members must share one nonzero side")

    trades = [trade for trade, _, _ in rows]
    prices = [float(trade.price) for trade in trades]
    sizes = [float(trade.size) for trade in trades]
    total = sum(sizes)
    vwap = sum(price * size for price, size in zip(prices, sizes)) / total
    path = sum(
        abs(after - before)
        for before, after in zip(prices, prices[1:])
    ) / tick_size
    net = (prices[-1] - prices[0]) / tick_size
    aligned = side * net
    efficiency = abs(net) / path if path > 0 else 0.0
    efficiency = max(0.0, min(1.0, efficiency))
    duration = trades[-1].event_time_ns - trades[0].event_time_ns
    interarrivals = [
        after.event_time_ns - before.event_time_ns
        for before, after in zip(trades, trades[1:])
    ]
    max_interarrival = max(interarrivals) if interarrivals else 0
    concentration = sum((size / total) ** 2 for size in sizes)

    return AggressiveRun(
        side=side,
        start_event_time_ns=trades[0].event_time_ns,
        end_event_time_ns=trades[-1].event_time_ns,
        start_sequence=trades[0].sequence,
        end_sequence=trades[-1].sequence,
        trade_count=len(trades),
        total_volume=total,
        vwap=vwap,
        start_price=prices[0],
        end_price=prices[-1],
        min_price=min(prices),
        max_price=max(prices),
        distinct_price_levels=len(set(prices)),
        aligned_travel_ticks=aligned,
        range_ticks=(max(prices) - min(prices)) / tick_size,
        path_length_ticks=path,
        directional_efficiency=efficiency,
        duration_ns=duration,
        max_interarrival_ns=max_interarrival,
        volume_concentration=concentration,
        evidence_tier=(
            EvidenceTier.TRUE_TRADE
            if all(explicit for _, _, explicit in rows)
            else EvidenceTier.INFERRED_TRADE
        ),
    )


def aggressive_runs(
    trades: list[Trade],
    *,
    tick_size: float,
    allow_inferred: bool = True,
) -> tuple[AggressiveRun, ...]:
    """Segment a causal trade window into consecutive same-side aggressor runs.

    Validation and evidence-tier semantics are shared with flow_dynamics.
    Unresolved tick-rule side zero breaks a run and is not silently assigned.
    """

    if type(allow_inferred) is not bool:
        raise TypeError("allow_inferred must be bool")
    if not trades:
        return ()
    validated = flow_dynamics(
        trades,
        tick_size=tick_size,
        allow_inferred=allow_inferred,
    )
    tick = validated.tick_size

    classified = [
        int(trade.side) if trade.side in (-1, 1) else 0
        for trade in trades
    ]
    if any(trade.side not in (-1, 1) for trade in trades):
        classified = classify_tick_rule(trades)

    rows = [
        (trade, side, trade.side in (-1, 1))
        for trade, side in zip(trades, classified)
    ]

    out: list[AggressiveRun] = []
    active: list[tuple[Trade, int, bool]] = []
    active_side = 0
    for row in rows:
        _, side, _ = row
        if side == 0:
            if active:
                out.append(_build_run(active, tick_size=tick))
                active = []
                active_side = 0
            continue
        if active and side != active_side:
            out.append(_build_run(active, tick_size=tick))
            active = []
        if not active:
            active_side = side
        active.append(row)
    if active:
        out.append(_build_run(active, tick_size=tick))

    return tuple(out)


def _finite_nonnegative(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    out = float(value)
    if not math.isfinite(out) or out < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return out


def select_sweep_like_runs(
    runs: tuple[AggressiveRun, ...] | list[AggressiveRun],
    *,
    min_trade_count: int = 2,
    min_distinct_price_levels: int = 2,
    min_aligned_travel_ticks: float = 1.0,
    min_directional_efficiency: float = 0.5,
    max_duration_ns: int | None = None,
    require_true_trade: bool = False,
) -> tuple[AggressiveRun, ...]:
    """Select descriptive multi-level aggressive runs.

    This is a configurable research filter, not proof of stop execution,
    liquidity taking intent, manipulation, or any particular participant.
    """

    if isinstance(min_trade_count, bool) or not isinstance(min_trade_count, int) or min_trade_count < 2:
        raise ValueError("min_trade_count must be an integer >= 2")
    if (
        isinstance(min_distinct_price_levels, bool)
        or not isinstance(min_distinct_price_levels, int)
        or min_distinct_price_levels < 2
    ):
        raise ValueError("min_distinct_price_levels must be an integer >= 2")
    travel = _finite_nonnegative(
        "min_aligned_travel_ticks",
        min_aligned_travel_ticks,
    )
    efficiency = _finite_nonnegative(
        "min_directional_efficiency",
        min_directional_efficiency,
    )
    if efficiency > 1:
        raise ValueError("min_directional_efficiency must be <= 1")
    if max_duration_ns is not None and (
        isinstance(max_duration_ns, bool)
        or not isinstance(max_duration_ns, int)
        or max_duration_ns < 0
    ):
        raise ValueError("max_duration_ns must be a non-negative integer or None")
    if type(require_true_trade) is not bool:
        raise TypeError("require_true_trade must be bool")

    selected: list[AggressiveRun] = []
    for run in runs:
        if not isinstance(run, AggressiveRun):
            raise TypeError("runs must contain AggressiveRun values")
        if run.trade_count < min_trade_count:
            continue
        if run.distinct_price_levels < min_distinct_price_levels:
            continue
        if run.aligned_travel_ticks < travel:
            continue
        if run.directional_efficiency < efficiency:
            continue
        if max_duration_ns is not None and run.duration_ns > max_duration_ns:
            continue
        if require_true_trade and run.evidence_tier is not EvidenceTier.TRUE_TRADE:
            continue
        selected.append(run)
    return tuple(selected)
