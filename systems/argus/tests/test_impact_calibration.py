from __future__ import annotations

from dataclasses import replace

import pytest

from argus.contracts import BookLevel, BookSnapshot, EvidenceTier
from argus.impact import depth_impact_curve
from argus.impact_calibration import (
    RealizedExecution,
    calibrate_impact,
    summarize_impact_calibration,
)


def book():
    return BookSnapshot(
        event_time_ns=100,
        sequence=7,
        bids=(
            BookLevel(99.0, 10.0),
            BookLevel(98.0, 20.0),
        ),
        asks=(
            BookLevel(101.0, 8.0),
            BookLevel(102.0, 20.0),
        ),
    )


def curve(side=1):
    return depth_impact_curve(
        book(),
        side=side,
        sizes=(5.0, 15.0, 40.0),
        tick_size=1.0,
        capacity_threshold_ticks=(0.0, 1.0),
    )


def execution(
    execution_id,
    *,
    requested=15.0,
    filled=15.0,
    average=102.0,
    side=1,
    decision=110,
    completion=120,
):
    return RealizedExecution(
        execution_id=execution_id,
        decision_time_ns=decision,
        completion_time_ns=completion,
        side=side,
        requested_size=requested,
        filled_size=filled,
        average_price=average,
    )


def test_calibration_compares_realized_slippage_to_static_depth_prediction():
    c = curve()
    result = calibrate_impact(
        c,
        execution("x"),
    )

    predicted = (8.0 * 101.0 + 7.0 * 102.0) / 15.0 - 101.0
    assert result.execution_id == "x"
    assert result.curve_event_time_ns == 100
    assert result.curve_sequence == 7
    assert result.snapshot_age_ns == 10
    assert result.completion_latency_ns == 10
    assert result.requested_to_visible_ratio == pytest.approx(15.0 / 28.0)
    assert result.predicted_fill_fraction == pytest.approx(1.0)
    assert result.realized_fill_fraction == pytest.approx(1.0)
    assert result.fill_fraction_error == pytest.approx(0.0)
    assert result.predicted_average_slippage_ticks == pytest.approx(predicted)
    assert result.realized_average_slippage_ticks == pytest.approx(1.0)
    assert result.slippage_error_ticks == pytest.approx(1.0 - predicted)
    assert result.absolute_slippage_error_ticks == pytest.approx(
        1.0 - predicted
    )
    assert result.underpredicted_slippage is True
    assert result.predicted_book_exhausted is False
    assert result.realized_complete_fill is True
    assert result.evidence_tier is EvidenceTier.TRUE_DEPTH
    assert result.assumption == "static_visible_depth_only"
    assert result.execution_authorized is False
    assert result.production_decision_authorized is False


def test_zero_fill_keeps_fill_error_but_has_no_slippage_claim():
    result = calibrate_impact(
        curve(),
        execution(
            "zero",
            requested=5.0,
            filled=0.0,
            average=None,
        ),
    )

    assert result.predicted_fill_fraction == pytest.approx(1.0)
    assert result.realized_fill_fraction == pytest.approx(0.0)
    assert result.fill_fraction_error == pytest.approx(-1.0)
    assert result.realized_average_slippage_ticks is None
    assert result.slippage_error_ticks is None
    assert result.absolute_slippage_error_ticks is None
    assert result.underpredicted_slippage is None
    assert result.realized_complete_fill is False


def test_partial_realized_fill_is_distinct_from_predicted_book_exhaustion():
    c = curve()
    result = calibrate_impact(
        c,
        execution(
            "partial",
            requested=40.0,
            filled=20.0,
            average=101.6,
        ),
    )

    assert result.predicted_fill_fraction == pytest.approx(28.0 / 40.0)
    assert result.predicted_book_exhausted is True
    assert result.realized_fill_fraction == pytest.approx(0.5)
    assert result.realized_complete_fill is False
    assert result.fill_fraction_error == pytest.approx(0.5 - 28.0 / 40.0)


def test_sell_calibration_uses_directional_slippage_sign():
    c = curve(side=-1)
    result = calibrate_impact(
        c,
        execution(
            "sell",
            side=-1,
            requested=15.0,
            filled=15.0,
            average=98.0,
        ),
    )

    # Best bid is 99; selling at 98 is +1 tick of adverse slippage.
    assert result.realized_average_slippage_ticks == pytest.approx(1.0)
    assert result.slippage_error_ticks is not None


def test_summary_reports_signed_and_absolute_calibration_error():
    c = curve()
    first = calibrate_impact(
        c,
        execution("a"),
    )
    second = calibrate_impact(
        c,
        execution(
            "b",
            requested=5.0,
            filled=5.0,
            average=101.0,
            decision=115,
            completion=125,
        ),
    )
    third = calibrate_impact(
        c,
        execution(
            "c",
            requested=5.0,
            filled=0.0,
            average=None,
            decision=120,
            completion=130,
        ),
    )

    summary = summarize_impact_calibration((first, second, third))

    assert summary.observations == 3
    assert summary.realized_fill_observations == 2
    assert summary.slippage_observations == 2
    assert summary.complete_fill_observations == 2
    assert summary.mean_snapshot_age_ns == pytest.approx(15.0)
    assert summary.mean_completion_latency_ns == pytest.approx(10.0)
    assert summary.mean_fill_fraction_error == pytest.approx(-1.0 / 3.0)
    assert summary.mean_absolute_fill_fraction_error == pytest.approx(1.0 / 3.0)
    assert summary.mean_slippage_error_ticks is not None
    assert summary.mean_absolute_slippage_error_ticks is not None
    assert summary.root_mean_squared_slippage_error_ticks is not None
    assert summary.slippage_underprediction_rate == pytest.approx(0.5)
    assert summary.execution_authorized is False
    assert summary.production_decision_authorized is False


@pytest.mark.parametrize(
    "bad,error",
    [
        (
            execution(
                "bad-side",
                side=-1,
            ),
            "side does not match",
        ),
        (
            execution(
                "early",
                decision=99,
                completion=120,
            ),
            "cannot precede impact snapshot",
        ),
        (
            execution(
                "unknown-size",
                requested=14.0,
                filled=14.0,
                average=102.0,
            ),
            "match exactly one",
        ),
        (
            execution(
                "overfill",
                requested=5.0,
                filled=6.0,
                average=101.0,
            ),
            "filled_size cannot exceed",
        ),
        (
            execution(
                "zero-price",
                requested=5.0,
                filled=0.0,
                average=101.0,
            ),
            "zero-fill",
        ),
        (
            execution(
                "time-reversal",
                decision=120,
                completion=119,
            ),
            "completion_time_ns",
        ),
    ],
)
def test_invalid_realized_execution_fails_closed(bad, error):
    with pytest.raises((TypeError, ValueError), match=error):
        calibrate_impact(curve(), bad)


def test_tampered_curve_evidence_and_point_math_fail_closed():
    c = curve()

    proxy = replace(c, evidence_tier=EvidenceTier.CANDLE_PROXY)
    with pytest.raises(ValueError, match="TRUE_DEPTH"):
        calibrate_impact(proxy, execution("proxy"))

    points = list(c.points)
    points[1] = replace(
        points[1],
        average_slippage_ticks_from_best=999.0,
    )
    tampered = replace(c, points=tuple(points))
    with pytest.raises(ValueError, match="average slippage"):
        calibrate_impact(tampered, execution("tampered"))


def test_summary_rejects_duplicates_and_empty_input():
    obs = calibrate_impact(curve(), execution("same"))

    with pytest.raises(ValueError, match="duplicate execution_id"):
        summarize_impact_calibration((obs, obs))

    with pytest.raises(ValueError, match="at least one"):
        summarize_impact_calibration(())


def test_summary_rejects_tampered_observation_math():
    obs = calibrate_impact(curve(), execution("tamper-summary"))

    bad_fill = replace(obs, fill_fraction_error=99.0)
    with pytest.raises(ValueError, match="fill_fraction_error"):
        summarize_impact_calibration((bad_fill,))

    bad_slippage = replace(obs, slippage_error_ticks=99.0)
    with pytest.raises(ValueError, match="slippage_error_ticks"):
        summarize_impact_calibration((bad_slippage,))

    bad_complete = replace(obs, realized_complete_fill=False)
    with pytest.raises(ValueError, match="realized_complete_fill"):
        summarize_impact_calibration((bad_complete,))
