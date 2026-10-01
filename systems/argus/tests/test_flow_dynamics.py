from __future__ import annotations

import math

import pytest

from argus.contracts import EvidenceTier, Trade
from argus.flow_dynamics import flow_dynamics


def test_explicit_flow_dynamics_are_true_trade_and_causal():
    trades = [
        Trade(0, 100.0, 2.0, 1, 1),
        Trade(1_000_000_000, 101.0, 3.0, 1, 2),
        Trade(2_000_000_000, 100.0, 1.0, -1, 3),
    ]

    result = flow_dynamics(trades, tick_size=1.0)

    assert result.evidence_tier is EvidenceTier.TRUE_TRADE
    assert result.event_time_ns == 2_000_000_000
    assert result.sequence == 3
    assert result.trade_count == 3
    assert result.buy_count == 2
    assert result.sell_count == 1
    assert result.unresolved_count == 0
    assert result.buy_volume == pytest.approx(5.0)
    assert result.sell_volume == pytest.approx(1.0)
    assert result.unresolved_volume == 0.0
    assert result.signed_volume == pytest.approx(4.0)
    assert result.total_volume == pytest.approx(6.0)
    assert result.imbalance == pytest.approx(4.0 / 6.0)
    assert result.volume_concentration == pytest.approx(14.0 / 36.0)
    assert result.price_range_ticks == pytest.approx(1.0)
    assert result.net_price_change_ticks == pytest.approx(0.0)
    assert result.path_length_ticks == pytest.approx(2.0)
    assert result.directional_efficiency == pytest.approx(0.0)
    assert result.flow_price_alignment == pytest.approx(0.0)
    assert result.pressure_without_displacement == pytest.approx(4.0 / 6.0)
    assert result.side_flip_rate == pytest.approx(0.5)
    assert result.max_same_side_run_volume_fraction == pytest.approx(5.0 / 6.0)
    assert result.buy_vwap == pytest.approx(100.6)
    assert result.sell_vwap == pytest.approx(100.0)
    assert result.aggressor_vwap_gap_ticks == pytest.approx(0.6)
    assert result.duration_ns == 2_000_000_000
    assert result.trade_rate_per_second == pytest.approx(1.5)
    assert result.volume_rate_per_second == pytest.approx(3.0)


def test_any_missing_aggressor_side_downgrades_entire_result():
    trades = [
        Trade(10, 100.0, 1.0, None, 0),
        Trade(11, 101.0, 2.0, None, 0),
        Trade(12, 100.0, 3.0, None, 0),
    ]

    result = flow_dynamics(trades, tick_size=1.0)

    assert result.evidence_tier is EvidenceTier.INFERRED_TRADE
    assert result.buy_count == 1
    assert result.sell_count == 1
    assert result.unresolved_count == 1
    assert result.buy_volume == pytest.approx(2.0)
    assert result.sell_volume == pytest.approx(3.0)
    assert result.unresolved_volume == pytest.approx(1.0)
    assert result.signed_volume == pytest.approx(-1.0)
    assert result.total_volume == pytest.approx(6.0)


def test_inference_can_be_disabled_fail_closed():
    trades = [Trade(1, 100.0, 1.0, None, 0)]
    with pytest.raises(ValueError, match="explicit aggressor side"):
        flow_dynamics(trades, tick_size=1.0, allow_inferred=False)


def test_pressure_without_displacement_exposes_one_sided_flow_with_zero_net_move():
    trades = [
        Trade(1, 100.0, 1.0, 1, 1),
        Trade(2, 101.0, 1.0, 1, 2),
        Trade(3, 100.0, 1.0, 1, 3),
    ]

    result = flow_dynamics(trades, tick_size=1.0)

    assert result.imbalance == pytest.approx(1.0)
    assert result.net_price_change_ticks == pytest.approx(0.0)
    assert result.path_length_ticks == pytest.approx(2.0)
    assert result.directional_efficiency == pytest.approx(0.0)
    assert result.pressure_without_displacement == pytest.approx(1.0)


def test_flow_price_alignment_is_signed_by_realized_direction():
    up = flow_dynamics(
        [
            Trade(1, 100.0, 1.0, 1, 1),
            Trade(2, 101.0, 1.0, 1, 2),
        ],
        tick_size=1.0,
    )
    down_against_buying = flow_dynamics(
        [
            Trade(1, 101.0, 1.0, 1, 1),
            Trade(2, 100.0, 1.0, 1, 2),
        ],
        tick_size=1.0,
    )

    assert up.flow_price_alignment == pytest.approx(1.0)
    assert down_against_buying.flow_price_alignment == pytest.approx(-1.0)
    assert up.directional_efficiency == pytest.approx(1.0)
    assert down_against_buying.directional_efficiency == pytest.approx(1.0)


def test_same_side_run_and_flip_rate_capture_flow_texture():
    trades = [
        Trade(1, 100.0, 2.0, 1, 1),
        Trade(2, 100.0, 3.0, 1, 2),
        Trade(3, 100.0, 1.0, -1, 3),
        Trade(4, 100.0, 2.0, 1, 4),
    ]

    result = flow_dynamics(trades, tick_size=1.0)

    assert result.side_flip_rate == pytest.approx(2.0 / 3.0)
    assert result.max_same_side_run_volume_fraction == pytest.approx(5.0 / 8.0)


def test_zero_duration_window_keeps_rates_finite_and_zero():
    trades = [
        Trade(10, 100.0, 1.0, 1, 0),
        Trade(10, 100.0, 2.0, -1, 0),
    ]

    result = flow_dynamics(trades, tick_size=1.0)

    assert result.duration_ns == 0
    assert result.trade_rate_per_second == 0.0
    assert result.volume_rate_per_second == 0.0
    assert math.isfinite(result.imbalance)


@pytest.mark.parametrize(
    "trades, tick_size, error",
    [
        ([], 1.0, "at least one trade"),
        ([Trade(1, 100.0, 1.0, 1, 1)], 0.0, "positive"),
        ([Trade(2, 100.0, 1.0, 1, 1), Trade(1, 100.0, 1.0, 1, 2)], 1.0, "ordered"),
        ([Trade(1, 100.0, 1.0, 1, 2), Trade(2, 101.0, 1.0, 1, 2)], 1.0, "strictly increasing"),
        ([Trade(1, 100.5, 1.0, 1, 1)], 1.0, "tick_size"),
        ([Trade(1, float("nan"), 1.0, 1, 1)], 1.0, "finite and positive"),
        ([Trade(1, 100.0, 0.0, 1, 1)], 1.0, "finite and positive"),
        ([Trade(1, 100.0, 1.0, 2, 1)], 1.0, "side"),
    ],
)
def test_flow_dynamics_fail_closed_on_invalid_inputs(trades, tick_size, error):
    with pytest.raises((TypeError, ValueError), match=error):
        flow_dynamics(trades, tick_size=tick_size)


def test_all_reported_bounded_metrics_stay_in_range():
    result = flow_dynamics(
        [
            Trade(1, 100.0, 1.0, -1, 1),
            Trade(2, 101.0, 2.0, 1, 2),
            Trade(3, 100.0, 4.0, -1, 3),
            Trade(4, 102.0, 8.0, 1, 4),
        ],
        tick_size=1.0,
    )

    assert -1.0 <= result.imbalance <= 1.0
    assert 0.0 <= result.volume_concentration <= 1.0
    assert 0.0 <= result.directional_efficiency <= 1.0
    assert -1.0 <= result.flow_price_alignment <= 1.0
    assert 0.0 <= result.pressure_without_displacement <= 1.0
    assert 0.0 <= result.side_flip_rate <= 1.0
    assert 0.0 <= result.max_same_side_run_volume_fraction <= 1.0
