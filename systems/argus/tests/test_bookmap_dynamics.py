from __future__ import annotations

import pytest

from argus.bookmap import depth_dynamics
from argus.contracts import BookLevel, BookSnapshot, EvidenceTier


def snapshot(
    time_ns,
    sequence,
    *,
    bids=((100.0, 10.0), (99.0, 20.0), (98.0, 10.0)),
    asks=((102.0, 10.0), (103.0, 20.0), (104.0, 10.0)),
):
    return BookSnapshot(
        event_time_ns=time_ns,
        sequence=sequence,
        bids=tuple(BookLevel(price, size) for price, size in bids),
        asks=tuple(BookLevel(price, size) for price, size in asks),
    )


def test_single_snapshot_depth_tensor_is_true_depth_and_deterministic():
    result = depth_dynamics([snapshot(10, 1)], tick_size=1.0, levels=4)

    assert result.evidence_tier is EvidenceTier.TRUE_DEPTH
    assert result.spread_ticks == 2
    assert result.bid_depth_by_tick == (10.0, 20.0, 10.0, 0.0)
    assert result.ask_depth_by_tick == (10.0, 20.0, 10.0, 0.0)
    assert result.bid_persistence_by_tick == (1.0, 1.0, 1.0, 0.0)
    assert result.ask_persistence_by_tick == (1.0, 1.0, 1.0, 0.0)
    assert result.bid_replenishment_rate_by_tick == (0.0, 0.0, 0.0, 0.0)
    assert result.bid_cancellation_rate_by_tick == (0.0, 0.0, 0.0, 0.0)
    assert result.bid_centroid_ticks == pytest.approx(1.0)
    assert result.ask_centroid_ticks == pytest.approx(1.0)
    assert result.bid_migration_ticks == 0.0
    assert result.ask_migration_ticks == 0.0
    assert result.bid_concentration == pytest.approx(0.375)
    assert result.ask_concentration == pytest.approx(0.375)


def test_replenishment_cancellation_and_migration_are_directional():
    first = snapshot(
        10,
        1,
        bids=((100.0, 10.0), (99.0, 10.0), (98.0, 20.0)),
        asks=((102.0, 10.0), (103.0, 20.0), (104.0, 10.0)),
    )
    second = snapshot(
        11,
        2,
        bids=((100.0, 10.0), (99.0, 20.0), (98.0, 10.0)),
        asks=((102.0, 10.0), (103.0, 10.0), (104.0, 20.0)),
    )

    result = depth_dynamics([first, second], tick_size=1.0, levels=3)

    assert result.bid_replenishment_rate_by_tick == pytest.approx((0.0, 0.5, 0.0))
    assert result.bid_cancellation_rate_by_tick == pytest.approx((0.0, 0.0, 0.5))
    assert result.ask_replenishment_rate_by_tick == pytest.approx((0.0, 0.0, 0.5))
    assert result.ask_cancellation_rate_by_tick == pytest.approx((0.0, 0.5, 0.0))
    assert result.bid_migration_ticks == pytest.approx(-0.25)
    assert result.ask_migration_ticks == pytest.approx(0.25)


def test_distance_to_touch_buckets_are_translation_invariant():
    first = snapshot(10, 1)
    shifted = snapshot(
        11,
        2,
        bids=((105.0, 10.0), (104.0, 20.0), (103.0, 10.0)),
        asks=((107.0, 10.0), (108.0, 20.0), (109.0, 10.0)),
    )

    result = depth_dynamics([first, shifted], tick_size=1.0, levels=4)

    assert result.bid_depth_by_tick == (10.0, 20.0, 10.0, 0.0)
    assert result.ask_depth_by_tick == (10.0, 20.0, 10.0, 0.0)
    assert result.bid_migration_ticks == pytest.approx(0.0)
    assert result.ask_migration_ticks == pytest.approx(0.0)
    assert result.bid_replenishment_rate_by_tick == (0.0, 0.0, 0.0, 0.0)
    assert result.ask_cancellation_rate_by_tick == (0.0, 0.0, 0.0, 0.0)


def test_persistence_marks_intermittent_liquidity_by_distance():
    first = snapshot(
        10,
        1,
        bids=((100.0, 10.0), (98.0, 10.0)),
        asks=((102.0, 10.0), (104.0, 10.0)),
    )
    second = snapshot(11, 2)

    result = depth_dynamics([first, second], tick_size=1.0, levels=3)

    assert result.bid_persistence_by_tick == pytest.approx((1.0, 0.5, 1.0))
    assert result.ask_persistence_by_tick == pytest.approx((1.0, 0.5, 1.0))


@pytest.mark.parametrize(
    "history, tick_size, levels, error",
    [
        ([snapshot(10, 1), snapshot(10, 1)], 1.0, 3, "strictly ordered"),
        ([snapshot(11, 2), snapshot(10, 1)], 1.0, 3, "strictly ordered"),
        ([snapshot(10, 1, bids=((100.0, 10.0), (99.5, 5.0)))], 1.0, 3, "tick_size"),
        ([snapshot(10, 1, bids=((100.0, 10.0), (100.0, 5.0)))], 1.0, 3, "duplicate bid"),
        ([snapshot(10, 1, bids=((100.0, -1.0),))], 1.0, 3, "positive size"),
        ([snapshot(10, 1)], 0.0, 3, "positive"),
        ([snapshot(10, 1)], 1.0, 0, "positive integer"),
    ],
)
def test_depth_dynamics_fails_closed_on_invalid_geometry(history, tick_size, levels, error):
    with pytest.raises((TypeError, ValueError), match=error):
        depth_dynamics(history, tick_size=tick_size, levels=levels)


def test_crossed_or_locked_snapshot_is_rejected():
    bad = snapshot(
        10,
        1,
        bids=((101.0, 10.0),),
        asks=((101.0, 10.0),),
    )
    with pytest.raises(ValueError, match="crossed/locked"):
        depth_dynamics([bad], tick_size=1.0)
