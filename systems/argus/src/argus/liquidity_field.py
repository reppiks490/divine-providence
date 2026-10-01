from __future__ import annotations

from dataclasses import dataclass
import math

from .bookmap import DepthDynamics
from .contracts import EvidenceTier


@dataclass(frozen=True)
class LiquidityField:
    """Descriptive TRUE_DEPTH shape and resilience state.

    This object summarizes only displayed depth present in the supplied
    DepthDynamics window. It does not claim hidden liquidity, queue position,
    spoofing intent, or fill probability.
    """

    event_time_ns: int
    sequence: int
    levels: int
    near_ticks: int
    bid_total_depth: float
    ask_total_depth: float
    depth_imbalance: float
    bid_near_touch_depth: float
    ask_near_touch_depth: float
    near_touch_imbalance: float
    bid_near_touch_share: float
    ask_near_touch_share: float
    near_touch_share_gradient: float
    bid_distance_depth_correlation: float
    ask_distance_depth_correlation: float
    bid_dispersion_ticks: float
    ask_dispersion_ticks: float
    bid_near_persistence: float
    ask_near_persistence: float
    bid_near_replenishment: float
    ask_near_replenishment: float
    bid_near_cancellation: float
    ask_near_cancellation: float
    bid_near_resilience: float
    ask_near_resilience: float
    bid_centroid_ticks: float
    ask_centroid_ticks: float
    bid_migration_ticks: float
    ask_migration_ticks: float
    bid_concentration: float
    ask_concentration: float
    evidence_tier: EvidenceTier = EvidenceTier.TRUE_DEPTH


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite")
    return out


def _bounded_array(
    name: str,
    values: tuple[float, ...],
    *,
    levels: int,
    lower: float,
    upper: float,
) -> tuple[float, ...]:
    if not isinstance(values, tuple) or len(values) != levels:
        raise ValueError(f"{name} must contain exactly levels values")
    out = tuple(_finite(name, value) for value in values)
    if any(value < lower or value > upper for value in out):
        raise ValueError(f"{name} values must be within [{lower}, {upper}]")
    return out


def _depth_array(
    name: str,
    values: tuple[float, ...],
    *,
    levels: int,
) -> tuple[float, ...]:
    if not isinstance(values, tuple) or len(values) != levels:
        raise ValueError(f"{name} must contain exactly levels values")
    out = tuple(_finite(name, value) for value in values)
    if any(value < 0 for value in out):
        raise ValueError(f"{name} values must be non-negative")
    return out


def _centroid(values: tuple[float, ...]) -> float:
    total = sum(values)
    return sum(index * value for index, value in enumerate(values)) / total


def _concentration(values: tuple[float, ...]) -> float:
    total = sum(values)
    return sum((value / total) ** 2 for value in values)


def _dispersion(values: tuple[float, ...], centroid: float) -> float:
    total = sum(values)
    variance = sum(
        value * ((index - centroid) ** 2)
        for index, value in enumerate(values)
    ) / total
    return math.sqrt(max(0.0, variance))


def _distance_depth_correlation(values: tuple[float, ...]) -> float:
    if len(values) < 2:
        return 0.0
    x_mean = (len(values) - 1) / 2.0
    y_mean = sum(values) / len(values)
    x_var = sum((index - x_mean) ** 2 for index in range(len(values)))
    y_var = sum((value - y_mean) ** 2 for value in values)
    if x_var <= 0 or y_var <= 0:
        return 0.0
    covariance = sum(
        (index - x_mean) * (value - y_mean)
        for index, value in enumerate(values)
    )
    return max(-1.0, min(1.0, covariance / math.sqrt(x_var * y_var)))


def _mean(values: tuple[float, ...]) -> float:
    return sum(values) / len(values) if values else 0.0


def liquidity_field(
    dynamics: DepthDynamics,
    *,
    near_ticks: int = 3,
) -> LiquidityField:
    """Build a normalized liquidity-field descriptor from TRUE_DEPTH dynamics."""

    if not isinstance(dynamics, DepthDynamics):
        raise TypeError("dynamics must be DepthDynamics")
    if dynamics.evidence_tier is not EvidenceTier.TRUE_DEPTH:
        raise ValueError("liquidity field requires TRUE_DEPTH evidence")
    if isinstance(dynamics.levels, bool) or not isinstance(dynamics.levels, int) or dynamics.levels < 1:
        raise ValueError("dynamics.levels must be a positive integer")
    if isinstance(near_ticks, bool) or not isinstance(near_ticks, int):
        raise ValueError("near_ticks must be a positive integer")
    if near_ticks < 1 or near_ticks > dynamics.levels:
        raise ValueError("near_ticks must be between 1 and dynamics.levels")
    if isinstance(dynamics.spread_ticks, bool) or not isinstance(dynamics.spread_ticks, int) or dynamics.spread_ticks < 1:
        raise ValueError("spread_ticks must be a positive integer")
    tick_size = _finite("tick_size", dynamics.tick_size)
    if tick_size <= 0:
        raise ValueError("tick_size must be positive")

    bid_depth = _depth_array(
        "bid_depth_by_tick",
        dynamics.bid_depth_by_tick,
        levels=dynamics.levels,
    )
    ask_depth = _depth_array(
        "ask_depth_by_tick",
        dynamics.ask_depth_by_tick,
        levels=dynamics.levels,
    )
    bid_total = sum(bid_depth)
    ask_total = sum(ask_depth)
    if bid_total <= 0 or ask_total <= 0:
        raise ValueError("liquidity field requires positive two-sided displayed depth")

    bid_persistence = _bounded_array(
        "bid_persistence_by_tick",
        dynamics.bid_persistence_by_tick,
        levels=dynamics.levels,
        lower=0.0,
        upper=1.0,
    )
    ask_persistence = _bounded_array(
        "ask_persistence_by_tick",
        dynamics.ask_persistence_by_tick,
        levels=dynamics.levels,
        lower=0.0,
        upper=1.0,
    )
    bid_replenishment = _bounded_array(
        "bid_replenishment_rate_by_tick",
        dynamics.bid_replenishment_rate_by_tick,
        levels=dynamics.levels,
        lower=0.0,
        upper=1.0,
    )
    ask_replenishment = _bounded_array(
        "ask_replenishment_rate_by_tick",
        dynamics.ask_replenishment_rate_by_tick,
        levels=dynamics.levels,
        lower=0.0,
        upper=1.0,
    )
    bid_cancellation = _bounded_array(
        "bid_cancellation_rate_by_tick",
        dynamics.bid_cancellation_rate_by_tick,
        levels=dynamics.levels,
        lower=0.0,
        upper=1.0,
    )
    ask_cancellation = _bounded_array(
        "ask_cancellation_rate_by_tick",
        dynamics.ask_cancellation_rate_by_tick,
        levels=dynamics.levels,
        lower=0.0,
        upper=1.0,
    )

    expected_bid_centroid = _centroid(bid_depth)
    expected_ask_centroid = _centroid(ask_depth)
    expected_bid_concentration = _concentration(bid_depth)
    expected_ask_concentration = _concentration(ask_depth)
    if not math.isclose(
        _finite("bid_centroid_ticks", dynamics.bid_centroid_ticks),
        expected_bid_centroid,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        raise ValueError("bid centroid does not match depth tensor")
    if not math.isclose(
        _finite("ask_centroid_ticks", dynamics.ask_centroid_ticks),
        expected_ask_centroid,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        raise ValueError("ask centroid does not match depth tensor")
    if not math.isclose(
        _finite("bid_concentration", dynamics.bid_concentration),
        expected_bid_concentration,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        raise ValueError("bid concentration does not match depth tensor")
    if not math.isclose(
        _finite("ask_concentration", dynamics.ask_concentration),
        expected_ask_concentration,
        rel_tol=1e-9,
        abs_tol=1e-9,
    ):
        raise ValueError("ask concentration does not match depth tensor")

    bid_migration = _finite("bid_migration_ticks", dynamics.bid_migration_ticks)
    ask_migration = _finite("ask_migration_ticks", dynamics.ask_migration_ticks)

    total_depth = bid_total + ask_total
    depth_imbalance = (bid_total - ask_total) / total_depth

    bid_near = sum(bid_depth[:near_ticks])
    ask_near = sum(ask_depth[:near_ticks])
    near_total = bid_near + ask_near
    near_imbalance = (bid_near - ask_near) / near_total if near_total else 0.0
    bid_near_share = bid_near / bid_total
    ask_near_share = ask_near / ask_total

    bid_near_persistence = _mean(bid_persistence[:near_ticks])
    ask_near_persistence = _mean(ask_persistence[:near_ticks])
    bid_near_replenishment = _mean(bid_replenishment[:near_ticks])
    ask_near_replenishment = _mean(ask_replenishment[:near_ticks])
    bid_near_cancellation = _mean(bid_cancellation[:near_ticks])
    ask_near_cancellation = _mean(ask_cancellation[:near_ticks])

    return LiquidityField(
        event_time_ns=dynamics.event_time_ns,
        sequence=dynamics.sequence,
        levels=dynamics.levels,
        near_ticks=near_ticks,
        bid_total_depth=bid_total,
        ask_total_depth=ask_total,
        depth_imbalance=depth_imbalance,
        bid_near_touch_depth=bid_near,
        ask_near_touch_depth=ask_near,
        near_touch_imbalance=near_imbalance,
        bid_near_touch_share=bid_near_share,
        ask_near_touch_share=ask_near_share,
        near_touch_share_gradient=bid_near_share - ask_near_share,
        bid_distance_depth_correlation=_distance_depth_correlation(bid_depth),
        ask_distance_depth_correlation=_distance_depth_correlation(ask_depth),
        bid_dispersion_ticks=_dispersion(bid_depth, expected_bid_centroid),
        ask_dispersion_ticks=_dispersion(ask_depth, expected_ask_centroid),
        bid_near_persistence=bid_near_persistence,
        ask_near_persistence=ask_near_persistence,
        bid_near_replenishment=bid_near_replenishment,
        ask_near_replenishment=ask_near_replenishment,
        bid_near_cancellation=bid_near_cancellation,
        ask_near_cancellation=ask_near_cancellation,
        bid_near_resilience=bid_near_replenishment - bid_near_cancellation,
        ask_near_resilience=ask_near_replenishment - ask_near_cancellation,
        bid_centroid_ticks=expected_bid_centroid,
        ask_centroid_ticks=expected_ask_centroid,
        bid_migration_ticks=bid_migration,
        ask_migration_ticks=ask_migration,
        bid_concentration=expected_bid_concentration,
        ask_concentration=expected_ask_concentration,
        evidence_tier=EvidenceTier.TRUE_DEPTH,
    )
