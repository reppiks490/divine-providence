from __future__ import annotations

from dataclasses import replace
import math

import pytest

from argus.contracts import EvidenceTier
from argus.orderblock_lifecycle import OrderBlockState
from argus.orderblock_survival import (
    KaplanMeierCurve,
    KaplanMeierPoint,
    OrderBlockSurvivalRecord,
    kaplan_meier,
)
from argus.survival_uncertainty import (
    kaplan_meier_uncertainty,
    uncertainty_at,
)


def record(block_id, duration, *, invalidated):
    return OrderBlockSurvivalRecord(
        block_id=block_id,
        direction=1,
        evidence_tier=EvidenceTier.TRUE_DEPTH,
        duration_ns=duration,
        invalidated=invalidated,
        test_count=0,
        rejection_count=0,
        max_penetration_fraction=0.0,
        terminal_state=(
            OrderBlockState.INVALIDATED
            if invalidated
            else OrderBlockState.EXPIRED
        ),
    )


def example_curve():
    return kaplan_meier(
        (
            record("a", 1, invalidated=True),
            record("b", 2, invalidated=False),
            record("c", 3, invalidated=True),
            record("d", 3, invalidated=False),
            record("e", 4, invalidated=True),
        )
    )


def test_greenwood_variance_and_nelson_aalen_are_deterministic():
    band = kaplan_meier_uncertainty(example_curve(), alpha=0.05)

    assert band.alpha == pytest.approx(0.05)
    assert band.confidence_level == pytest.approx(0.95)
    assert band.records == 5
    assert band.invalidations == 3
    assert band.censored == 2
    assert [point.duration_ns for point in band.points] == [1, 2, 3, 4]

    p1, p2, p3, p4 = band.points

    expected_g1 = 1.0 / (5.0 * 4.0)
    assert p1.survival_probability == pytest.approx(0.8)
    assert p1.greenwood_variance == pytest.approx(0.8**2 * expected_g1)
    assert p1.standard_error == pytest.approx(
        math.sqrt(0.8**2 * expected_g1)
    )
    assert p1.cumulative_hazard == pytest.approx(1.0 / 5.0)

    # Censor-only time does not change Greenwood variance or cumulative hazard.
    assert p2.greenwood_variance == pytest.approx(p1.greenwood_variance)
    assert p2.cumulative_hazard == pytest.approx(p1.cumulative_hazard)

    expected_g3 = expected_g1 + 1.0 / (3.0 * 2.0)
    expected_s3 = 0.8 * (2.0 / 3.0)
    assert p3.greenwood_variance == pytest.approx(
        expected_s3**2 * expected_g3
    )
    assert p3.cumulative_hazard == pytest.approx(1.0 / 5.0 + 1.0 / 3.0)

    # Final n=d event drives KM survival to zero. The public uncertainty point
    # is a degenerate [0,0] boundary rather than an infinite Greenwood value.
    assert p4.survival_probability == pytest.approx(0.0)
    assert p4.greenwood_variance == pytest.approx(0.0)
    assert p4.standard_error == pytest.approx(0.0)
    assert p4.lower_confidence == pytest.approx(0.0)
    assert p4.upper_confidence == pytest.approx(0.0)
    assert p4.cumulative_hazard == pytest.approx(
        1.0 / 5.0 + 1.0 / 3.0 + 1.0
    )


def test_pointwise_loglog_intervals_are_bounded_and_contain_estimate():
    band = kaplan_meier_uncertainty(example_curve())
    for point in band.points:
        assert 0.0 <= point.lower_confidence <= 1.0
        assert 0.0 <= point.upper_confidence <= 1.0
        assert point.lower_confidence <= point.upper_confidence
        assert (
            point.lower_confidence - 1e-12
            <= point.survival_probability
            <= point.upper_confidence + 1e-12
        )
        assert point.greenwood_variance >= 0.0
        assert point.standard_error >= 0.0
        assert point.cumulative_hazard >= 0.0


def test_more_conservative_alpha_produces_wider_nonboundary_interval():
    curve = example_curve()
    band95 = kaplan_meier_uncertainty(curve, alpha=0.05)
    band99 = kaplan_meier_uncertainty(curve, alpha=0.01)

    p95 = band95.points[0]
    p99 = band99.points[0]

    assert p99.lower_confidence <= p95.lower_confidence
    assert p99.upper_confidence >= p95.upper_confidence
    assert (
        p99.upper_confidence - p99.lower_confidence
        > p95.upper_confidence - p95.lower_confidence
    )


def test_all_censored_curve_stays_at_one_with_zero_uncertainty_and_hazard():
    curve = kaplan_meier(
        (
            record("a", 1, invalidated=False),
            record("b", 2, invalidated=False),
        )
    )
    band = kaplan_meier_uncertainty(curve)

    assert [point.survival_probability for point in band.points] == [1.0, 1.0]
    assert all(point.greenwood_variance == 0.0 for point in band.points)
    assert all(point.standard_error == 0.0 for point in band.points)
    assert all(point.lower_confidence == 1.0 for point in band.points)
    assert all(point.upper_confidence == 1.0 for point in band.points)
    assert all(point.cumulative_hazard == 0.0 for point in band.points)


def test_uncertainty_at_is_stepwise_and_none_before_first_point():
    band = kaplan_meier_uncertainty(example_curve())

    assert uncertainty_at(band, duration_ns=0) is None
    assert uncertainty_at(band, duration_ns=1) == band.points[0]
    assert uncertainty_at(band, duration_ns=2) == band.points[1]
    assert uncertainty_at(band, duration_ns=100) == band.points[-1]


@pytest.mark.parametrize("alpha", [0.0, 1.0, -0.1, 1.1, float("nan")])
def test_invalid_alpha_values_fail_closed(alpha):
    with pytest.raises(ValueError, match="alpha"):
        kaplan_meier_uncertainty(example_curve(), alpha=alpha)


@pytest.mark.parametrize("alpha", [True, "0.05", None])
def test_invalid_alpha_types_fail_closed(alpha):
    with pytest.raises(TypeError, match="alpha"):
        kaplan_meier_uncertainty(example_curve(), alpha=alpha)


def test_curve_type_and_query_validation_fail_closed():
    with pytest.raises(TypeError, match="curve"):
        kaplan_meier_uncertainty({})

    band = kaplan_meier_uncertainty(example_curve())
    with pytest.raises(TypeError, match="band"):
        uncertainty_at({}, duration_ns=1)
    with pytest.raises(ValueError, match="duration_ns"):
        uncertainty_at(band, duration_ns=-1)


def test_tampered_at_risk_accounting_is_rejected():
    curve = example_curve()
    points = list(curve.points)
    points[1] = replace(points[1], at_risk=999)
    bad = replace(curve, points=tuple(points))

    with pytest.raises(ValueError, match="at-risk"):
        kaplan_meier_uncertainty(bad)


def test_tampered_survival_recurrence_is_rejected():
    curve = example_curve()
    points = list(curve.points)
    points[0] = replace(points[0], survival_probability=0.9)
    bad = replace(curve, points=tuple(points))

    with pytest.raises(ValueError, match="survival recurrence"):
        kaplan_meier_uncertainty(bad)


def test_tampered_totals_and_rmst_are_rejected():
    curve = example_curve()

    with pytest.raises(ValueError, match="counts"):
        kaplan_meier_uncertainty(replace(curve, invalidations=2))

    with pytest.raises(ValueError, match="restricted_mean"):
        kaplan_meier_uncertainty(
            replace(curve, restricted_mean_survival_ns=999.0)
        )


def test_nonincreasing_durations_and_invalid_point_removals_are_rejected():
    curve = example_curve()

    repeated_time = list(curve.points)
    repeated_time[1] = replace(
        repeated_time[1],
        duration_ns=repeated_time[0].duration_ns,
    )
    with pytest.raises(ValueError, match="strictly increasing"):
        kaplan_meier_uncertainty(
            replace(curve, points=tuple(repeated_time))
        )

    impossible = KaplanMeierCurve(
        records=1,
        invalidations=1,
        censored=0,
        points=(
            KaplanMeierPoint(
                duration_ns=1,
                at_risk=1,
                invalidations=1,
                censored=1,
                survival_probability=0.0,
            ),
        ),
        median_survival_ns=1,
        restricted_mean_survival_ns=1.0,
    )
    with pytest.raises(ValueError, match="removals exceed"):
        kaplan_meier_uncertainty(impossible)


def test_zero_duration_event_keeps_outputs_finite():
    curve = kaplan_meier(
        (
            record("a", 0, invalidated=True),
            record("b", 1, invalidated=False),
        )
    )
    band = kaplan_meier_uncertainty(curve)
    first = band.points[0]

    assert first.duration_ns == 0
    assert math.isfinite(first.greenwood_variance)
    assert math.isfinite(first.standard_error)
    assert math.isfinite(first.cumulative_hazard)
