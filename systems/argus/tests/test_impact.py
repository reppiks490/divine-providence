from __future__ import annotations

import pytest

from argus.contracts import BookLevel, BookSnapshot, EvidenceTier
from argus.impact import depth_impact_curve


def book(
    *,
    bids=((99.0, 10.0), (98.0, 20.0)),
    asks=((101.0, 8.0), (102.0, 20.0)),
    event_time_ns=123,
    sequence=7,
):
    return BookSnapshot(
        event_time_ns=event_time_ns,
        sequence=sequence,
        bids=tuple(BookLevel(price, size) for price, size in bids),
        asks=tuple(BookLevel(price, size) for price, size in asks),
    )


def test_buy_impact_curve_walks_visible_asks_deterministically():
    curve = depth_impact_curve(
        book(),
        side=1,
        sizes=(4.0, 8.0, 15.0, 40.0),
        tick_size=1.0,
        capacity_threshold_ticks=(0.0, 1.0, 2.0),
    )

    assert curve.evidence_tier is EvidenceTier.TRUE_DEPTH
    assert curve.event_time_ns == 123
    assert curve.sequence == 7
    assert curve.side == 1
    assert curve.best_bid == 99.0
    assert curve.best_ask == 101.0
    assert curve.spread_ticks == pytest.approx(2.0)
    assert curve.midprice == pytest.approx(100.0)
    assert curve.microprice == pytest.approx((101.0 * 10.0 + 99.0 * 8.0) / 18.0)
    assert curve.visible_opposite_size == pytest.approx(28.0)
    assert curve.capacity_at_marginal_ticks == (
        (0.0, 8.0),
        (1.0, 28.0),
        (2.0, 28.0),
    )

    p4, p8, p15, p40 = curve.points

    assert p4.filled_size == pytest.approx(4.0)
    assert p4.fill_fraction == pytest.approx(1.0)
    assert p4.average_price == pytest.approx(101.0)
    assert p4.marginal_price == pytest.approx(101.0)
    assert p4.consumed_levels == 1
    assert p4.average_slippage_ticks_from_best == pytest.approx(0.0)
    assert p4.marginal_displacement_ticks_from_best == pytest.approx(0.0)
    assert p4.implementation_shortfall_ticks_from_mid == pytest.approx(1.0)
    assert p4.book_exhausted is False

    assert p8.average_price == pytest.approx(101.0)
    assert p8.consumed_levels == 1

    assert p15.average_price == pytest.approx((8.0 * 101.0 + 7.0 * 102.0) / 15.0)
    assert p15.marginal_price == pytest.approx(102.0)
    assert p15.consumed_levels == 2
    assert p15.average_slippage_ticks_from_best == pytest.approx(7.0 / 15.0)
    assert p15.marginal_displacement_ticks_from_best == pytest.approx(1.0)
    assert p15.book_exhausted is False

    assert p40.filled_size == pytest.approx(28.0)
    assert p40.fill_fraction == pytest.approx(28.0 / 40.0)
    assert p40.average_price == pytest.approx((8.0 * 101.0 + 20.0 * 102.0) / 28.0)
    assert p40.marginal_price == pytest.approx(102.0)
    assert p40.consumed_levels == 2
    assert p40.book_exhausted is True

    assert [
        point.average_slippage_ticks_from_best for point in curve.points
    ] == sorted(
        point.average_slippage_ticks_from_best for point in curve.points
    )
    assert curve.assumption == "static_visible_depth_only"
    assert curve.execution_authorized is False
    assert curve.production_decision_authorized is False


def test_sell_impact_curve_walks_bids_with_positive_directional_slippage():
    curve = depth_impact_curve(
        book(),
        side=-1,
        sizes=(5.0, 15.0, 30.0),
        tick_size=1.0,
        capacity_threshold_ticks=(0.0, 1.0),
    )

    assert curve.visible_opposite_size == pytest.approx(30.0)
    assert curve.capacity_at_marginal_ticks == (
        (0.0, 10.0),
        (1.0, 30.0),
    )
    assert curve.points[0].average_price == pytest.approx(99.0)
    assert curve.points[0].average_slippage_ticks_from_best == pytest.approx(0.0)
    assert curve.points[1].average_price == pytest.approx(
        (10.0 * 99.0 + 5.0 * 98.0) / 15.0
    )
    assert curve.points[1].average_slippage_ticks_from_best == pytest.approx(5.0 / 15.0)
    assert curve.points[1].marginal_displacement_ticks_from_best == pytest.approx(1.0)
    assert curve.points[2].fill_fraction == pytest.approx(1.0)
    assert curve.points[2].book_exhausted is False


def test_capacity_is_marginal_price_capacity_not_average_slippage_capacity():
    curve = depth_impact_curve(
        book(asks=((101.0, 1.0), (102.0, 99.0))),
        side=1,
        sizes=(50.0,),
        tick_size=1.0,
        capacity_threshold_ticks=(0.0, 1.0),
    )

    assert curve.capacity_at_marginal_ticks == ((0.0, 1.0), (1.0, 100.0))
    assert curve.points[0].average_slippage_ticks_from_best == pytest.approx(49.0 / 50.0)
    assert curve.points[0].marginal_displacement_ticks_from_best == pytest.approx(1.0)


def test_microprice_reference_uses_top_level_size_asymmetry():
    curve = depth_impact_curve(
        book(
            bids=((99.0, 30.0),),
            asks=((101.0, 10.0),),
        ),
        side=1,
        sizes=(1.0,),
        tick_size=1.0,
    )

    assert curve.microprice == pytest.approx(100.5)
    assert curve.points[0].implementation_shortfall_ticks_from_microprice == pytest.approx(0.5)


@pytest.mark.parametrize(
    "bad_book, tick_size, error",
    [
        (book(bids=((99.0, 10.0), (99.0, 5.0))), 1.0, "duplicate bid"),
        (book(asks=((101.0, 8.0), (101.0, 2.0))), 1.0, "duplicate ask"),
        (book(bids=((99.5, 10.0),)), 1.0, "aligned to tick_size"),
        (book(bids=((101.0, 10.0),), asks=((101.0, 8.0),)), 1.0, "crossed/locked"),
        (book(bids=((99.0, 0.0),)), 1.0, "positive"),
        (book(asks=((101.0, float("nan")),)), 1.0, "finite"),
        (book(event_time_ns=-1), 1.0, "non-negative"),
        (book(sequence=-1), 1.0, "non-negative"),
    ],
)
def test_depth_impact_curve_rejects_invalid_books(bad_book, tick_size, error):
    with pytest.raises((TypeError, ValueError), match=error):
        depth_impact_curve(
            bad_book,
            side=1,
            sizes=(1.0,),
            tick_size=tick_size,
        )


@pytest.mark.parametrize("side", [0, 2, True])
def test_invalid_side_fails_closed(side):
    with pytest.raises(ValueError, match="side"):
        depth_impact_curve(
            book(),
            side=side,
            sizes=(1.0,),
            tick_size=1.0,
        )


@pytest.mark.parametrize(
    "sizes, error",
    [
        ((), "required"),
        ((0.0,), "positive"),
        ((1.0, 1.0), "strictly increasing"),
        ((2.0, 1.0), "strictly increasing"),
        ((float("inf"),), "finite"),
    ],
)
def test_invalid_size_grid_fails_closed(sizes, error):
    with pytest.raises((TypeError, ValueError), match=error):
        depth_impact_curve(
            book(),
            side=1,
            sizes=sizes,
            tick_size=1.0,
        )


@pytest.mark.parametrize(
    "thresholds, error",
    [
        ((), "required"),
        ((-1.0,), "non-negative"),
        ((0.0, 0.0), "strictly increasing"),
        ((2.0, 1.0), "strictly increasing"),
        ((float("nan"),), "finite"),
    ],
)
def test_invalid_capacity_threshold_grid_fails_closed(thresholds, error):
    with pytest.raises((TypeError, ValueError), match=error):
        depth_impact_curve(
            book(),
            side=1,
            sizes=(1.0,),
            tick_size=1.0,
            capacity_threshold_ticks=thresholds,
        )


@pytest.mark.parametrize("tick_size", [0.0, -1.0, float("nan"), True])
def test_invalid_tick_size_fails_closed(tick_size):
    with pytest.raises((TypeError, ValueError), match="tick_size"):
        depth_impact_curve(
            book(),
            side=1,
            sizes=(1.0,),
            tick_size=tick_size,
        )


def test_quarter_tick_book_is_supported_when_geometry_is_valid():
    curve = depth_impact_curve(
        book(
            bids=((100.00, 4.0), (99.75, 6.0)),
            asks=((100.25, 5.0), (100.50, 7.0)),
        ),
        side=1,
        sizes=(5.0, 10.0),
        tick_size=0.25,
        capacity_threshold_ticks=(0.0, 1.0),
    )

    assert curve.spread_ticks == pytest.approx(1.0)
    assert curve.capacity_at_marginal_ticks == ((0.0, 5.0), (1.0, 12.0))
    assert curve.points[1].marginal_displacement_ticks_from_best == pytest.approx(1.0)
