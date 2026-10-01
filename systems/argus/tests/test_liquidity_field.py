from __future__ import annotations

import math

import pytest

from argus.bookmap import DepthDynamics
from argus.contracts import EvidenceTier
from argus.liquidity_field import liquidity_field


def _centroid(values):
    total = sum(values)
    return sum(index * value for index, value in enumerate(values)) / total


def _concentration(values):
    total = sum(values)
    return sum((value / total) ** 2 for value in values)


def dynamics(
    *,
    bid=(40.0, 30.0, 20.0, 10.0),
    ask=(10.0, 20.0, 30.0, 40.0),
    bid_persistence=(0.9, 0.8, 0.7, 0.6),
    ask_persistence=(0.6, 0.7, 0.8, 0.9),
    bid_replenishment=(0.4, 0.2, 0.1, 0.0),
    ask_replenishment=(0.1, 0.1, 0.2, 0.2),
    bid_cancellation=(0.1, 0.1, 0.2, 0.2),
    ask_cancellation=(0.2, 0.4, 0.1, 0.0),
    evidence_tier=EvidenceTier.TRUE_DEPTH,
    bid_centroid=None,
    ask_centroid=None,
    bid_concentration=None,
    ask_concentration=None,
):
    levels = len(bid)
    if bid_centroid is None:
        bid_centroid = _centroid(bid) if sum(bid) else 0.0
    if ask_centroid is None:
        ask_centroid = _centroid(ask) if sum(ask) else 0.0
    if bid_concentration is None:
        bid_concentration = _concentration(bid) if sum(bid) else 0.0
    if ask_concentration is None:
        ask_concentration = _concentration(ask) if sum(ask) else 0.0
    return DepthDynamics(
        event_time_ns=100,
        sequence=9,
        tick_size=1.0,
        levels=levels,
        spread_ticks=1,
        bid_depth_by_tick=tuple(bid),
        ask_depth_by_tick=tuple(ask),
        bid_persistence_by_tick=tuple(bid_persistence),
        ask_persistence_by_tick=tuple(ask_persistence),
        bid_replenishment_rate_by_tick=tuple(bid_replenishment),
        ask_replenishment_rate_by_tick=tuple(ask_replenishment),
        bid_cancellation_rate_by_tick=tuple(bid_cancellation),
        ask_cancellation_rate_by_tick=tuple(ask_cancellation),
        bid_centroid_ticks=bid_centroid,
        ask_centroid_ticks=ask_centroid,
        bid_migration_ticks=-0.25,
        ask_migration_ticks=0.5,
        bid_concentration=bid_concentration,
        ask_concentration=ask_concentration,
        evidence_tier=evidence_tier,
    )


def test_liquidity_field_describes_near_touch_shape_and_resilience():
    result = liquidity_field(dynamics(), near_ticks=2)

    assert result.evidence_tier is EvidenceTier.TRUE_DEPTH
    assert result.event_time_ns == 100
    assert result.sequence == 9
    assert result.levels == 4
    assert result.near_ticks == 2
    assert result.bid_total_depth == pytest.approx(100.0)
    assert result.ask_total_depth == pytest.approx(100.0)
    assert result.depth_imbalance == pytest.approx(0.0)
    assert result.bid_near_touch_depth == pytest.approx(70.0)
    assert result.ask_near_touch_depth == pytest.approx(30.0)
    assert result.near_touch_imbalance == pytest.approx(0.4)
    assert result.bid_near_touch_share == pytest.approx(0.7)
    assert result.ask_near_touch_share == pytest.approx(0.3)
    assert result.near_touch_share_gradient == pytest.approx(0.4)
    assert result.bid_distance_depth_correlation == pytest.approx(-1.0)
    assert result.ask_distance_depth_correlation == pytest.approx(1.0)
    assert result.bid_dispersion_ticks == pytest.approx(1.0)
    assert result.ask_dispersion_ticks == pytest.approx(1.0)
    assert result.bid_near_persistence == pytest.approx(0.85)
    assert result.ask_near_persistence == pytest.approx(0.65)
    assert result.bid_near_replenishment == pytest.approx(0.3)
    assert result.ask_near_replenishment == pytest.approx(0.1)
    assert result.bid_near_cancellation == pytest.approx(0.1)
    assert result.ask_near_cancellation == pytest.approx(0.3)
    assert result.bid_near_resilience == pytest.approx(0.2)
    assert result.ask_near_resilience == pytest.approx(-0.2)
    assert result.bid_centroid_ticks == pytest.approx(1.0)
    assert result.ask_centroid_ticks == pytest.approx(2.0)
    assert result.bid_migration_ticks == pytest.approx(-0.25)
    assert result.ask_migration_ticks == pytest.approx(0.5)
    assert result.bid_concentration == pytest.approx(0.30)
    assert result.ask_concentration == pytest.approx(0.30)


def test_uniform_depth_has_zero_distance_correlation():
    uniform = (25.0, 25.0, 25.0, 25.0)
    result = liquidity_field(
        dynamics(
            bid=uniform,
            ask=uniform,
        ),
        near_ticks=2,
    )

    assert result.bid_distance_depth_correlation == 0.0
    assert result.ask_distance_depth_correlation == 0.0
    assert result.depth_imbalance == 0.0
    assert result.near_touch_share_gradient == 0.0


def test_one_level_book_has_zero_shape_correlation_and_dispersion():
    one = dynamics(
        bid=(10.0,),
        ask=(20.0,),
        bid_persistence=(1.0,),
        ask_persistence=(1.0,),
        bid_replenishment=(0.0,),
        ask_replenishment=(0.0,),
        bid_cancellation=(0.0,),
        ask_cancellation=(0.0,),
    )
    result = liquidity_field(one, near_ticks=1)

    assert result.bid_distance_depth_correlation == 0.0
    assert result.ask_distance_depth_correlation == 0.0
    assert result.bid_dispersion_ticks == 0.0
    assert result.ask_dispersion_ticks == 0.0
    assert result.bid_near_touch_share == 1.0
    assert result.ask_near_touch_share == 1.0


@pytest.mark.parametrize("near_ticks", [0, -1, 5, True])
def test_near_touch_window_must_fit_depth_tensor(near_ticks):
    with pytest.raises(ValueError, match="near_ticks"):
        liquidity_field(dynamics(), near_ticks=near_ticks)


def test_non_true_depth_evidence_is_rejected():
    with pytest.raises(ValueError, match="TRUE_DEPTH"):
        liquidity_field(
            dynamics(evidence_tier=EvidenceTier.INFERRED_TRADE),
            near_ticks=2,
        )


def test_depth_tensor_lengths_are_fail_closed():
    bad = dynamics()
    bad = DepthDynamics(
        **{
            **bad.__dict__,
            "bid_depth_by_tick": (40.0, 30.0, 20.0),
        }
    )
    with pytest.raises(ValueError, match="bid_depth_by_tick"):
        liquidity_field(bad, near_ticks=2)


def test_tampered_centroid_is_rejected():
    with pytest.raises(ValueError, match="bid centroid"):
        liquidity_field(
            dynamics(bid_centroid=999.0),
            near_ticks=2,
        )


def test_tampered_concentration_is_rejected():
    with pytest.raises(ValueError, match="ask concentration"):
        liquidity_field(
            dynamics(ask_concentration=0.99),
            near_ticks=2,
        )


def test_out_of_range_temporal_rates_are_rejected():
    bad = dynamics(
        bid_replenishment=(1.1, 0.2, 0.1, 0.0),
    )
    with pytest.raises(ValueError, match="bid_replenishment_rate_by_tick"):
        liquidity_field(bad, near_ticks=2)


def test_positive_two_sided_depth_is_required():
    bad = dynamics(
        bid=(0.0, 0.0, 0.0, 0.0),
        bid_centroid=0.0,
        bid_concentration=0.0,
    )
    with pytest.raises(ValueError, match="positive two-sided"):
        liquidity_field(bad, near_ticks=2)


def test_all_normalized_outputs_are_bounded():
    result = liquidity_field(dynamics(), near_ticks=3)

    assert -1.0 <= result.depth_imbalance <= 1.0
    assert -1.0 <= result.near_touch_imbalance <= 1.0
    assert 0.0 <= result.bid_near_touch_share <= 1.0
    assert 0.0 <= result.ask_near_touch_share <= 1.0
    assert -1.0 <= result.near_touch_share_gradient <= 1.0
    assert -1.0 <= result.bid_distance_depth_correlation <= 1.0
    assert -1.0 <= result.ask_distance_depth_correlation <= 1.0
    assert 0.0 <= result.bid_near_persistence <= 1.0
    assert 0.0 <= result.ask_near_persistence <= 1.0
    assert 0.0 <= result.bid_near_replenishment <= 1.0
    assert 0.0 <= result.ask_near_replenishment <= 1.0
    assert 0.0 <= result.bid_near_cancellation <= 1.0
    assert 0.0 <= result.ask_near_cancellation <= 1.0
    assert -1.0 <= result.bid_near_resilience <= 1.0
    assert -1.0 <= result.ask_near_resilience <= 1.0
    assert math.isfinite(result.bid_dispersion_ticks)
    assert math.isfinite(result.ask_dispersion_ticks)
