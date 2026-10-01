from __future__ import annotations

from dataclasses import replace

import pytest

from argus.contracts import EvidenceTier, Trade
from argus.flow_events import AggressiveRun, aggressive_runs, select_sweep_like_runs


def test_explicit_aggressive_runs_segment_by_side():
    trades = [
        Trade(0, 100.0, 1.0, 1, 1),
        Trade(1, 101.0, 2.0, 1, 2),
        Trade(2, 102.0, 3.0, 1, 3),
        Trade(3, 102.0, 2.0, -1, 4),
        Trade(4, 101.0, 2.0, -1, 5),
    ]

    runs = aggressive_runs(trades, tick_size=1.0)

    assert len(runs) == 2
    buy, sell = runs

    assert buy.side == 1
    assert buy.trade_count == 3
    assert buy.total_volume == pytest.approx(6.0)
    assert buy.vwap == pytest.approx(608.0 / 6.0)
    assert buy.start_price == 100.0
    assert buy.end_price == 102.0
    assert buy.min_price == 100.0
    assert buy.max_price == 102.0
    assert buy.distinct_price_levels == 3
    assert buy.aligned_travel_ticks == pytest.approx(2.0)
    assert buy.range_ticks == pytest.approx(2.0)
    assert buy.path_length_ticks == pytest.approx(2.0)
    assert buy.directional_efficiency == pytest.approx(1.0)
    assert buy.duration_ns == 2
    assert buy.max_interarrival_ns == 1
    assert buy.volume_concentration == pytest.approx(14.0 / 36.0)
    assert buy.evidence_tier is EvidenceTier.TRUE_TRADE

    assert sell.side == -1
    assert sell.trade_count == 2
    assert sell.aligned_travel_ticks == pytest.approx(1.0)
    assert sell.directional_efficiency == pytest.approx(1.0)
    assert sell.evidence_tier is EvidenceTier.TRUE_TRADE


def test_unresolved_tick_rule_side_breaks_run_and_inference_downgrades_run():
    trades = [
        Trade(0, 100.0, 1.0, None, 0),
        Trade(1, 101.0, 1.0, None, 0),
        Trade(2, 102.0, 1.0, 1, 0),
    ]

    runs = aggressive_runs(trades, tick_size=1.0)

    assert len(runs) == 1
    run = runs[0]
    assert run.side == 1
    assert run.trade_count == 2
    assert run.start_price == 101.0
    assert run.end_price == 102.0
    assert run.evidence_tier is EvidenceTier.INFERRED_TRADE


def test_inference_can_be_disabled_fail_closed():
    with pytest.raises(ValueError, match="explicit aggressor side"):
        aggressive_runs(
            [Trade(1, 100.0, 1.0, None, 0)],
            tick_size=1.0,
            allow_inferred=False,
        )


def test_allow_inferred_requires_boolean():
    with pytest.raises(TypeError, match="allow_inferred"):
        aggressive_runs(
            [Trade(1, 100.0, 1.0, 1, 1)],
            tick_size=1.0,
            allow_inferred="yes",
        )


def test_empty_input_has_no_runs():
    assert aggressive_runs([], tick_size=1.0) == ()


def test_sweep_like_filter_is_descriptive_and_configurable():
    run = aggressive_runs(
        [
            Trade(0, 100.0, 1.0, 1, 1),
            Trade(1, 101.0, 1.0, 1, 2),
            Trade(2, 100.0, 1.0, 1, 3),
            Trade(3, 102.0, 1.0, 1, 4),
        ],
        tick_size=1.0,
    )[0]

    selected = select_sweep_like_runs(
        (run,),
        min_trade_count=4,
        min_distinct_price_levels=3,
        min_aligned_travel_ticks=2.0,
        min_directional_efficiency=0.5,
        max_duration_ns=3,
        require_true_trade=True,
    )

    assert selected == (run,)
    assert run.path_length_ticks == pytest.approx(4.0)
    assert run.directional_efficiency == pytest.approx(0.5)


def test_flat_same_side_run_is_not_multi_level_sweep_like():
    run = aggressive_runs(
        [
            Trade(0, 100.0, 1.0, 1, 1),
            Trade(1, 100.0, 1.0, 1, 2),
        ],
        tick_size=1.0,
    )[0]

    assert select_sweep_like_runs((run,)) == ()


def test_true_trade_requirement_filters_inferred_run():
    run = aggressive_runs(
        [
            Trade(0, 100.0, 1.0, 1, 0),
            Trade(1, 101.0, 1.0, None, 0),
            Trade(2, 102.0, 1.0, None, 0),
        ],
        tick_size=1.0,
    )[0]
    assert run.evidence_tier is EvidenceTier.INFERRED_TRADE

    permissive = select_sweep_like_runs(
        (run,),
        min_trade_count=3,
        min_distinct_price_levels=3,
        min_aligned_travel_ticks=2.0,
        min_directional_efficiency=1.0,
        require_true_trade=False,
    )
    strict = select_sweep_like_runs(
        (run,),
        min_trade_count=3,
        min_distinct_price_levels=3,
        min_aligned_travel_ticks=2.0,
        min_directional_efficiency=1.0,
        require_true_trade=True,
    )

    assert permissive == (run,)
    assert strict == ()


def test_duration_filter_rejects_slow_run():
    run = aggressive_runs(
        [
            Trade(0, 100.0, 1.0, 1, 1),
            Trade(10, 101.0, 1.0, 1, 2),
        ],
        tick_size=1.0,
    )[0]

    assert select_sweep_like_runs(
        (run,),
        max_duration_ns=9,
    ) == ()


@pytest.mark.parametrize(
    "kwargs, error",
    [
        ({"min_trade_count": 1}, "min_trade_count"),
        ({"min_distinct_price_levels": 1}, "min_distinct_price_levels"),
        ({"min_aligned_travel_ticks": -1}, "min_aligned_travel_ticks"),
        ({"min_directional_efficiency": 1.1}, "min_directional_efficiency"),
        ({"max_duration_ns": -1}, "max_duration_ns"),
    ],
)
def test_invalid_sweep_like_criteria_fail_closed(kwargs, error):
    with pytest.raises((TypeError, ValueError), match=error):
        select_sweep_like_runs((), **kwargs)


def test_require_true_trade_must_be_boolean():
    with pytest.raises(TypeError, match="require_true_trade"):
        select_sweep_like_runs((), require_true_trade="yes")


def test_run_input_validation_reuses_flow_dynamics_guards():
    with pytest.raises(ValueError, match="ordered"):
        aggressive_runs(
            [
                Trade(2, 101.0, 1.0, 1, 1),
                Trade(1, 100.0, 1.0, 1, 2),
            ],
            tick_size=1.0,
        )

    with pytest.raises(ValueError, match="tick_size"):
        aggressive_runs(
            [Trade(1, 100.5, 1.0, 1, 1)],
            tick_size=1.0,
        )


def _valid_manual_run():
    return aggressive_runs(
        [
            Trade(1, 100.0, 1.0, 1, 1),
            Trade(2, 101.0, 2.0, 1, 2),
        ],
        tick_size=1.0,
    )[0]


@pytest.mark.parametrize(
    "change, error",
    [
        ({"side": 0}, "run.side"),
        ({"trade_count": 0}, "trade_count"),
        ({"distinct_price_levels": 3}, "distinct_price_levels"),
        ({"end_event_time_ns": 0}, "event time"),
        ({"start_sequence": 3, "end_sequence": 2}, "sequence"),
        ({"duration_ns": 999}, "duration_ns"),
        ({"max_interarrival_ns": 2}, "max_interarrival_ns"),
        ({"total_volume": 0.0}, "total_volume"),
        ({"vwap": float("nan")}, "vwap"),
        ({"min_price": 102.0}, "min_price"),
        ({"start_price": 999.0}, "start_price"),
        ({"end_price": 999.0}, "end_price"),
        ({"aligned_travel_ticks": 2.0}, "aligned travel"),
        ({"range_ticks": 2.0}, "run range"),
        ({"directional_efficiency": 1.1}, "directional_efficiency"),
        ({"directional_efficiency": 0.5}, "must match"),
        ({"volume_concentration": 1.1}, "volume_concentration"),
        ({"volume_concentration": 0.1}, "finite-run minimum"),
        ({"evidence_tier": EvidenceTier.TRUE_DEPTH}, "aggressive run evidence"),
    ],
)
def test_sweep_filter_rejects_malformed_manual_runs(change, error):
    run = replace(_valid_manual_run(), **change)
    with pytest.raises((TypeError, ValueError), match=error):
        select_sweep_like_runs((run,))


def test_sweep_filter_rejects_non_run_values():
    with pytest.raises(TypeError, match="AggressiveRun"):
        select_sweep_like_runs(("not-a-run",))


def test_single_trade_manual_run_requires_zero_interarrival():
    run = AggressiveRun(
        side=1,
        start_event_time_ns=1,
        end_event_time_ns=1,
        start_sequence=1,
        end_sequence=1,
        trade_count=1,
        total_volume=1.0,
        vwap=100.0,
        start_price=100.0,
        end_price=100.0,
        min_price=100.0,
        max_price=100.0,
        distinct_price_levels=1,
        aligned_travel_ticks=0.0,
        range_ticks=0.0,
        path_length_ticks=0.0,
        directional_efficiency=0.0,
        duration_ns=0,
        max_interarrival_ns=1,
        volume_concentration=1.0,
        evidence_tier=EvidenceTier.TRUE_TRADE,
    )
    with pytest.raises(ValueError, match="zero max_interarrival"):
        select_sweep_like_runs((run,))
