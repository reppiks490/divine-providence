from __future__ import annotations

from dataclasses import dataclass
import math

from .contracts import EvidenceTier, Trade
from .orderflow import classify_tick_rule


@dataclass(frozen=True)
class FlowDynamics:
    """Deterministic causal trade-flow summary over already-ordered prints.

    TRUE_TRADE is claimed only when every trade carries an explicit aggressor
    side. If any side is missing and tick-rule inference is used, the entire
    summary is downgraded to INFERRED_TRADE.
    """

    event_time_ns: int
    sequence: int
    tick_size: float
    trade_count: int
    buy_count: int
    sell_count: int
    unresolved_count: int
    buy_volume: float
    sell_volume: float
    unresolved_volume: float
    signed_volume: float
    total_volume: float
    imbalance: float
    volume_concentration: float
    price_range_ticks: float
    net_price_change_ticks: float
    path_length_ticks: float
    directional_efficiency: float
    flow_price_alignment: float
    pressure_without_displacement: float
    side_flip_rate: float
    max_same_side_run_volume_fraction: float
    buy_vwap: float | None
    sell_vwap: float | None
    aggressor_vwap_gap_ticks: float | None
    duration_ns: int
    trade_rate_per_second: float
    volume_rate_per_second: float
    evidence_tier: EvidenceTier


def _positive_finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    out = float(value)
    if not math.isfinite(out) or out <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return out


def _validate_trade(trade: Trade) -> None:
    if isinstance(trade.event_time_ns, bool) or not isinstance(trade.event_time_ns, int) or trade.event_time_ns < 0:
        raise ValueError("trade event_time_ns must be a non-negative integer")
    if isinstance(trade.sequence, bool) or not isinstance(trade.sequence, int) or trade.sequence < 0:
        raise ValueError("trade sequence must be a non-negative integer")
    _positive_finite("trade price", trade.price)
    _positive_finite("trade size", trade.size)
    if trade.side not in (-1, 1, None):
        raise ValueError("trade side must be -1, +1, or None")


def _vwap(prices: list[float], sizes: list[float]) -> float | None:
    total = sum(sizes)
    if total <= 0:
        return None
    return sum(price * size for price, size in zip(prices, sizes)) / total


def flow_dynamics(
    trades: list[Trade],
    *,
    tick_size: float,
    allow_inferred: bool = True,
) -> FlowDynamics:
    """Build causal trade-flow dynamics from prints available by decision time.

    The function validates chronology and positive finite price/size data. Event
    times must be nondecreasing. Positive exchange/source sequence values, when
    present, must be strictly increasing. Zero sequence is treated as
    unspecified, so multiple same-timestamp prints remain representable.

    Missing aggressor sides may be inferred via the existing ARGUS tick rule
    only when allow_inferred is true. Any such inference downgrades the
    complete result to INFERRED_TRADE.
    """

    tick = _positive_finite("tick_size", tick_size)
    if not trades:
        raise ValueError("at least one trade is required")

    previous_time: int | None = None
    previous_positive_sequence: int | None = None
    for trade in trades:
        _validate_trade(trade)
        if previous_time is not None and trade.event_time_ns < previous_time:
            raise ValueError("trade history must be ordered by event_time_ns")
        previous_time = trade.event_time_ns
        if trade.sequence > 0:
            if previous_positive_sequence is not None and trade.sequence <= previous_positive_sequence:
                raise ValueError("positive trade sequence values must be strictly increasing")
            previous_positive_sequence = trade.sequence

    explicit = all(trade.side in (-1, 1) for trade in trades)
    if not explicit and not allow_inferred:
        raise ValueError("explicit aggressor side is required when inference is disabled")

    sides = [int(trade.side) if trade.side in (-1, 1) else 0 for trade in trades]
    if not explicit:
        sides = classify_tick_rule(trades)

    prices = [float(trade.price) for trade in trades]
    sizes = [float(trade.size) for trade in trades]
    total_volume = sum(sizes)
    signed_volume = sum(side * size for side, size in zip(sides, sizes))

    buy_prices = [price for price, side in zip(prices, sides) if side == 1]
    buy_sizes = [size for size, side in zip(sizes, sides) if side == 1]
    sell_prices = [price for price, side in zip(prices, sides) if side == -1]
    sell_sizes = [size for size, side in zip(sizes, sides) if side == -1]

    buy_volume = sum(buy_sizes)
    sell_volume = sum(sell_sizes)
    unresolved_volume = sum(size for side, size in zip(sides, sizes) if side == 0)
    buy_count = sum(1 for side in sides if side == 1)
    sell_count = sum(1 for side in sides if side == -1)
    unresolved_count = len(sides) - buy_count - sell_count
    imbalance = signed_volume / total_volume if total_volume else 0.0

    concentration = sum((size / total_volume) ** 2 for size in sizes) if total_volume else 0.0
    price_range_ticks = (max(prices) - min(prices)) / tick
    net_price_change_ticks = (prices[-1] - prices[0]) / tick
    path_length_ticks = sum(abs(after - before) for before, after in zip(prices, prices[1:])) / tick
    directional_efficiency = (
        min(1.0, abs(net_price_change_ticks) / path_length_ticks)
        if path_length_ticks > 0
        else 0.0
    )
    price_direction = 1.0 if net_price_change_ticks > 0 else -1.0 if net_price_change_ticks < 0 else 0.0
    flow_price_alignment = price_direction * imbalance
    pressure_without_displacement = abs(imbalance) * (1.0 - directional_efficiency)

    classified_sides = [side for side in sides if side != 0]
    flips = sum(1 for left, right in zip(classified_sides, classified_sides[1:]) if left != right)
    side_flip_rate = flips / (len(classified_sides) - 1) if len(classified_sides) > 1 else 0.0

    max_run_volume = 0.0
    current_side = 0
    current_run_volume = 0.0
    for side, size in zip(sides, sizes):
        if side == 0:
            current_side = 0
            current_run_volume = 0.0
            continue
        if side == current_side:
            current_run_volume += size
        else:
            current_side = side
            current_run_volume = size
        max_run_volume = max(max_run_volume, current_run_volume)
    max_run_fraction = max_run_volume / total_volume if total_volume else 0.0

    buy_vwap = _vwap(buy_prices, buy_sizes)
    sell_vwap = _vwap(sell_prices, sell_sizes)
    vwap_gap_ticks = (
        (buy_vwap - sell_vwap) / tick
        if buy_vwap is not None and sell_vwap is not None
        else None
    )

    duration_ns = trades[-1].event_time_ns - trades[0].event_time_ns
    if duration_ns > 0:
        duration_seconds = duration_ns / 1_000_000_000.0
        trade_rate = len(trades) / duration_seconds
        volume_rate = total_volume / duration_seconds
    else:
        trade_rate = 0.0
        volume_rate = 0.0

    return FlowDynamics(
        event_time_ns=trades[-1].event_time_ns,
        sequence=trades[-1].sequence,
        tick_size=tick,
        trade_count=len(trades),
        buy_count=buy_count,
        sell_count=sell_count,
        unresolved_count=unresolved_count,
        buy_volume=buy_volume,
        sell_volume=sell_volume,
        unresolved_volume=unresolved_volume,
        signed_volume=signed_volume,
        total_volume=total_volume,
        imbalance=imbalance,
        volume_concentration=concentration,
        price_range_ticks=price_range_ticks,
        net_price_change_ticks=net_price_change_ticks,
        path_length_ticks=path_length_ticks,
        directional_efficiency=directional_efficiency,
        flow_price_alignment=flow_price_alignment,
        pressure_without_displacement=pressure_without_displacement,
        side_flip_rate=side_flip_rate,
        max_same_side_run_volume_fraction=max_run_fraction,
        buy_vwap=buy_vwap,
        sell_vwap=sell_vwap,
        aggressor_vwap_gap_ticks=vwap_gap_ticks,
        duration_ns=duration_ns,
        trade_rate_per_second=trade_rate,
        volume_rate_per_second=volume_rate,
        evidence_tier=EvidenceTier.TRUE_TRADE if explicit else EvidenceTier.INFERRED_TRADE,
    )
