from __future__ import annotations

import math

import pytest

from argus.contracts import EvidenceTier
from argus.orderblocks import score_order_block
from argus.orderblock_lifecycle import (
    OrderBlockLifecycleConfig,
    OrderBlockObservation,
    OrderBlockState,
    advance_order_block,
    confirm_order_block,
    create_order_block_lifecycle,
)
from argus.orderblock_survival import (
    OrderBlockSurvivalRecord,
    kaplan_meier,
    record_from_lifecycle,
    survival_by_evidence_tier,
    survival_by_test_count,
    survival_probability_at,
)


def candidate(tier=EvidenceTier.TRUE_DEPTH):
    return score_order_block(
        direction=1,
        lower=99.0,
        upper=100.0,
        origin_time_ns=0,
        displacement_atr=2.4,
        signed_flow_alignment=0.8,
        depth_vacuum=0.8,
        revisit_rejection=0.8,
        evidence_tier=tier,
    )


def invalidated_lifecycle():
    lifecycle = create_order_block_lifecycle(candidate())
    lifecycle = confirm_order_block(lifecycle, at_time_ns=1)
    lifecycle = advance_order_block(
        lifecycle,
        OrderBlockObservation(event_time_ns=2, low=99.8, high=100.2, close=100.1),
    )
    return advance_order_block(
        lifecycle,
        OrderBlockObservation(event_time_ns=5, low=98.5, high=99.5, close=98.9),
    )


def expired_lifecycle():
    cfg = OrderBlockLifecycleConfig(max_age_ns=10)
    lifecycle = create_order_block_lifecycle(candidate())
    lifecycle = confirm_order_block(lifecycle, at_time_ns=1, config=cfg)
    return advance_order_block(
        lifecycle,
        OrderBlockObservation(event_time_ns=10, low=100.5, high=101.0, close=100.8),
        config=cfg,
    )


def record(
    block_id,
    duration,
    *,
    invalidated,
    tier=EvidenceTier.TRUE_DEPTH,
    tests=0,
    rejections=0,
    penetration=0.0,
):
    return OrderBlockSurvivalRecord(
        block_id=block_id,
        direction=1,
        evidence_tier=tier,
        duration_ns=duration,
        invalidated=invalidated,
        test_count=tests,
        rejection_count=rejections,
        max_penetration_fraction=penetration,
        terminal_state=(
            OrderBlockState.INVALIDATED if invalidated else OrderBlockState.EXPIRED
        ),
    )


def test_terminal_lifecycle_converts_to_survival_record():
    lifecycle = invalidated_lifecycle()
    result = record_from_lifecycle(lifecycle)

    assert result.block_id == lifecycle.block_id
    assert result.duration_ns == 4
    assert result.invalidated is True
    assert result.test_count == 2
    assert result.rejection_count == 1
    assert result.terminal_state is OrderBlockState.INVALIDATED
    assert result.evidence_tier is EvidenceTier.TRUE_DEPTH


def test_expiry_is_right_censored():
    lifecycle = expired_lifecycle()
    result = record_from_lifecycle(lifecycle)

    assert result.duration_ns == 9
    assert result.invalidated is False
    assert result.terminal_state is OrderBlockState.EXPIRED


def test_unconfirmed_expiry_is_not_valid_post_confirmation_survival_data():
    cfg = OrderBlockLifecycleConfig(max_age_ns=2)
    lifecycle = create_order_block_lifecycle(candidate())
    lifecycle = confirm_order_block(lifecycle, at_time_ns=2, config=cfg)
    assert lifecycle.state is OrderBlockState.EXPIRED
    assert lifecycle.confirmation_time_ns is None

    with pytest.raises(ValueError, match="confirmed"):
        record_from_lifecycle(lifecycle)


def test_kaplan_meier_handles_events_and_censoring_at_same_time():
    rows = (
        record("a", 1, invalidated=True),
        record("b", 2, invalidated=False),
        record("c", 3, invalidated=True),
        record("d", 3, invalidated=False),
        record("e", 4, invalidated=True),
    )

    curve = kaplan_meier(rows)

    assert curve.records == 5
    assert curve.invalidations == 3
    assert curve.censored == 2
    assert [point.duration_ns for point in curve.points] == [1, 2, 3, 4]

    p1, p2, p3, p4 = curve.points
    assert (p1.at_risk, p1.invalidations, p1.censored) == (5, 1, 0)
    assert p1.survival_probability == pytest.approx(0.8)

    assert (p2.at_risk, p2.invalidations, p2.censored) == (4, 0, 1)
    assert p2.survival_probability == pytest.approx(0.8)

    assert (p3.at_risk, p3.invalidations, p3.censored) == (3, 1, 1)
    assert p3.survival_probability == pytest.approx(0.8 * (2.0 / 3.0))

    assert (p4.at_risk, p4.invalidations, p4.censored) == (1, 1, 0)
    assert p4.survival_probability == pytest.approx(0.0)

    assert curve.median_survival_ns == 4
    assert curve.restricted_mean_survival_ns == pytest.approx(
        1.0 + 0.8 + 0.8 + 0.8 * (2.0 / 3.0)
    )


def test_all_censored_curve_never_claims_observed_median():
    curve = kaplan_meier(
        (
            record("a", 1, invalidated=False),
            record("b", 2, invalidated=False),
        )
    )

    assert [p.survival_probability for p in curve.points] == [1.0, 1.0]
    assert curve.median_survival_ns is None
    assert curve.restricted_mean_survival_ns == pytest.approx(2.0)


def test_survival_probability_at_is_stepwise():
    curve = kaplan_meier(
        (
            record("a", 5, invalidated=True),
            record("b", 10, invalidated=False),
        )
    )

    assert survival_probability_at(curve, duration_ns=0) == pytest.approx(1.0)
    assert survival_probability_at(curve, duration_ns=4) == pytest.approx(1.0)
    assert survival_probability_at(curve, duration_ns=5) == pytest.approx(0.5)
    assert survival_probability_at(curve, duration_ns=100) == pytest.approx(0.5)


def test_evidence_tier_strata_are_kept_separate():
    strata = survival_by_evidence_tier(
        (
            record("proxy", 1, invalidated=True, tier=EvidenceTier.CANDLE_PROXY),
            record("l2a", 2, invalidated=False, tier=EvidenceTier.TRUE_DEPTH),
            record("l2b", 3, invalidated=True, tier=EvidenceTier.TRUE_DEPTH),
        )
    )

    assert [item.label for item in strata] == ["CANDLE_PROXY", "TRUE_DEPTH"]
    assert strata[0].curve.records == 1
    assert strata[1].curve.records == 2


def test_final_test_count_strata_are_explicitly_retrospective():
    strata = survival_by_test_count(
        (
            record("zero", 1, invalidated=False, tests=0),
            record("one", 2, invalidated=True, tests=1),
            record("two", 3, invalidated=True, tests=2),
            record("three", 4, invalidated=False, tests=3),
        )
    )

    assert [item.label for item in strata] == ["tests=0", "tests=1", "tests>=2"]
    assert [item.curve.records for item in strata] == [1, 1, 2]


def test_duplicate_block_ids_fail_closed():
    rows = (
        record("same", 1, invalidated=True),
        record("same", 2, invalidated=False),
    )
    with pytest.raises(ValueError, match="duplicate block_id"):
        kaplan_meier(rows)


@pytest.mark.parametrize(
    "bad, error",
    [
        (
            OrderBlockSurvivalRecord(
                block_id="x",
                direction=1,
                evidence_tier=EvidenceTier.TRUE_DEPTH,
                duration_ns=-1,
                invalidated=True,
                test_count=0,
                rejection_count=0,
                max_penetration_fraction=0.0,
                terminal_state=OrderBlockState.INVALIDATED,
            ),
            "duration_ns",
        ),
        (
            OrderBlockSurvivalRecord(
                block_id="x",
                direction=1,
                evidence_tier=EvidenceTier.TRUE_DEPTH,
                duration_ns=1,
                invalidated=True,
                test_count=0,
                rejection_count=1,
                max_penetration_fraction=0.0,
                terminal_state=OrderBlockState.INVALIDATED,
            ),
            "rejection_count",
        ),
        (
            OrderBlockSurvivalRecord(
                block_id="x",
                direction=1,
                evidence_tier=EvidenceTier.TRUE_DEPTH,
                duration_ns=1,
                invalidated=True,
                test_count=0,
                rejection_count=0,
                max_penetration_fraction=float("nan"),
                terminal_state=OrderBlockState.INVALIDATED,
            ),
            "max_penetration_fraction",
        ),
        (
            OrderBlockSurvivalRecord(
                block_id="x",
                direction=1,
                evidence_tier=EvidenceTier.TRUE_DEPTH,
                duration_ns=1,
                invalidated=False,
                test_count=0,
                rejection_count=0,
                max_penetration_fraction=0.0,
                terminal_state=OrderBlockState.INVALIDATED,
            ),
            "terminal_state",
        ),
    ],
)
def test_invalid_survival_records_fail_closed(bad, error):
    with pytest.raises((TypeError, ValueError), match=error):
        kaplan_meier((bad,))


def test_empty_study_fails_closed():
    with pytest.raises(ValueError, match="at least one"):
        kaplan_meier(())


def test_probability_query_validation():
    curve = kaplan_meier((record("x", 1, invalidated=False),))
    with pytest.raises(ValueError, match="duration_ns"):
        survival_probability_at(curve, duration_ns=-1)
    with pytest.raises(TypeError, match="curve"):
        survival_probability_at({}, duration_ns=1)


def test_rmst_remains_finite_with_zero_duration_event():
    curve = kaplan_meier(
        (
            record("a", 0, invalidated=True),
            record("b", 1, invalidated=False),
        )
    )
    assert curve.points[0].duration_ns == 0
    assert math.isfinite(curve.restricted_mean_survival_ns)
