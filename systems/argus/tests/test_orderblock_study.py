from __future__ import annotations

import pytest

from argus.contracts import EvidenceTier
from argus.orderblock_lifecycle import OrderBlockState
from argus.orderblock_study import (
    OrderBlockStudySubject,
    create_prospective_manifest,
    lock_study_cohort,
    registered_evidence_strata,
    registered_kaplan_meier,
)
from argus.orderblock_survival import OrderBlockSurvivalRecord


REVISION = "argus-orderblock-lifecycle:ebab6ea2"


def manifest(**overrides):
    params = dict(
        study_name="prospective-nq-order-block-survival",
        created_time_ns=90,
        cohort_start_ns=100,
        cohort_end_ns=200,
        followup_cutoff_ns=300,
        lifecycle_revision=REVISION,
        asset_ids=("NQ", "ES"),
        evidence_tiers=(EvidenceTier.TRUE_DEPTH, EvidenceTier.TRUE_TRADE),
        directions=(-1, 1),
        analysis_horizon_ns=50,
        analysis_plan=("kaplan_meier", "evidence_tier_strata"),
    )
    params.update(overrides)
    return create_prospective_manifest(**params)


def record(
    block_id,
    *,
    duration=20,
    invalidated=True,
    tier=EvidenceTier.TRUE_DEPTH,
    direction=1,
    tests=1,
):
    return OrderBlockSurvivalRecord(
        block_id=block_id,
        direction=direction,
        evidence_tier=tier,
        duration_ns=duration,
        invalidated=invalidated,
        test_count=tests,
        rejection_count=0,
        max_penetration_fraction=0.2,
        terminal_state=(
            OrderBlockState.INVALIDATED if invalidated else OrderBlockState.EXPIRED
        ),
    )


def subject(
    block_id,
    *,
    asset="NQ",
    confirmation=120,
    revision=REVISION,
    **record_kwargs,
):
    return OrderBlockStudySubject(
        record=record(block_id, **record_kwargs),
        asset_id=asset,
        confirmation_time_ns=confirmation,
        lifecycle_revision=revision,
    )


def test_manifest_identity_is_canonical_across_input_order():
    first = manifest(
        asset_ids=("NQ", "ES"),
        evidence_tiers=(EvidenceTier.TRUE_DEPTH, EvidenceTier.TRUE_TRADE),
        directions=(1, -1),
        analysis_plan=("evidence_tier_strata", "kaplan_meier"),
    )
    second = manifest(
        asset_ids=("ES", "NQ", "ES"),
        evidence_tiers=(EvidenceTier.TRUE_TRADE, EvidenceTier.TRUE_DEPTH),
        directions=(-1, 1, -1),
        analysis_plan=("kaplan_meier", "evidence_tier_strata"),
    )

    assert first == second
    assert first.asset_ids == ("ES", "NQ")
    assert first.evidence_tiers == (
        EvidenceTier.TRUE_TRADE,
        EvidenceTier.TRUE_DEPTH,
    )
    assert first.directions == (-1, 1)


def test_manifest_must_be_locked_before_cohort_starts():
    with pytest.raises(ValueError, match="created at or before"):
        manifest(created_time_ns=101)


def test_manifest_time_geometry_fails_closed():
    with pytest.raises(ValueError, match="cohort_start_ns"):
        manifest(cohort_start_ns=200, cohort_end_ns=200)
    with pytest.raises(ValueError, match="followup_cutoff_ns"):
        manifest(followup_cutoff_ns=199)
    with pytest.raises(ValueError, match="analysis_horizon_ns"):
        manifest(analysis_horizon_ns=0)


def test_manifest_contract_values_fail_closed():
    with pytest.raises(ValueError, match="asset_id"):
        manifest(asset_ids=("",))
    with pytest.raises(ValueError, match="evidence tier"):
        manifest(evidence_tiers=())
    with pytest.raises(TypeError, match="EvidenceTier"):
        manifest(evidence_tiers=("TRUE_DEPTH",))
    with pytest.raises(ValueError, match="directions"):
        manifest(directions=(0,))
    with pytest.raises(ValueError, match="unsupported analysis"):
        manifest(analysis_plan=("kaplan_meier", "peek_at_results_first"))


def test_cohort_applies_all_predeclared_inclusion_rules():
    locked = lock_study_cohort(
        manifest(),
        (
            subject("included"),
            subject("wrong-revision", revision="other"),
            subject("wrong-asset", asset="BTC"),
            subject("wrong-tier", tier=EvidenceTier.CANDLE_PROXY),
            subject("wrong-direction", direction=1),
            subject("too-early", confirmation=99),
            subject("too-late", confirmation=200),
        ),
    )

    # wrong-direction still matches the default +/-1 manifest and is included.
    assert locked.included_block_ids == ("included", "wrong-direction")
    assert locked.exclusions == (
        ("too-early", "confirmation_before_cohort"),
        ("too-late", "confirmation_at_or_after_cohort_end"),
        ("wrong-asset", "asset_not_in_manifest"),
        ("wrong-revision", "lifecycle_revision_mismatch"),
        ("wrong-tier", "evidence_tier_not_in_manifest"),
    )


def test_direction_filter_can_be_predeclared():
    locked = lock_study_cohort(
        manifest(directions=(1,)),
        (
            subject("long", direction=1),
            subject("short", direction=-1),
        ),
    )
    assert locked.included_block_ids == ("long",)
    assert locked.exclusions == (("short", "direction_not_in_manifest"),)


def test_followup_is_administratively_censored_at_predeclared_horizon():
    locked = lock_study_cohort(
        manifest(analysis_horizon_ns=50),
        (
            subject("late-event", confirmation=120, duration=100, invalidated=True),
            subject("early-event", confirmation=130, duration=20, invalidated=True),
            subject("natural-censor", confirmation=140, duration=30, invalidated=False),
        ),
    )

    rows = {row.block_id: row for row in locked.records}

    assert rows["late-event"].duration_ns == 50
    assert rows["late-event"].invalidated is False
    assert rows["late-event"].terminal_state is OrderBlockState.EXPIRED

    assert rows["early-event"].duration_ns == 20
    assert rows["early-event"].invalidated is True

    assert rows["natural-censor"].duration_ns == 30
    assert rows["natural-censor"].invalidated is False
    assert locked.administrative_censored == 1


def test_followup_cutoff_can_be_tighter_than_analysis_horizon():
    locked = lock_study_cohort(
        manifest(
            cohort_end_ns=200,
            followup_cutoff_ns=210,
            analysis_horizon_ns=1000,
        ),
        (
            subject("near-end", confirmation=190, duration=50, invalidated=True),
        ),
    )
    row = locked.records[0]
    assert row.duration_ns == 20
    assert row.invalidated is False
    assert locked.administrative_censored == 1


def test_event_exactly_at_followup_cap_remains_observed():
    locked = lock_study_cohort(
        manifest(analysis_horizon_ns=50),
        (
            subject("exact", confirmation=120, duration=50, invalidated=True),
        ),
    )
    row = locked.records[0]
    assert row.duration_ns == 50
    assert row.invalidated is True
    assert locked.administrative_censored == 0


def test_cohort_identity_is_independent_of_subject_input_order():
    m = manifest()
    first = lock_study_cohort(
        m,
        (subject("b"), subject("a")),
    )
    second = lock_study_cohort(
        m,
        (subject("a"), subject("b")),
    )

    assert first.cohort_id == second.cohort_id
    assert first.included_block_ids == ("a", "b")


def test_duplicate_subject_block_ids_fail_closed():
    with pytest.raises(ValueError, match="duplicate block_id"):
        lock_study_cohort(
            manifest(),
            (subject("same"), subject("same")),
        )


def test_malformed_record_cannot_hide_behind_exclusion():
    bad = OrderBlockStudySubject(
        record=OrderBlockSurvivalRecord(
            block_id="bad",
            direction=1,
            evidence_tier=EvidenceTier.CANDLE_PROXY,
            duration_ns=-1,
            invalidated=True,
            test_count=0,
            rejection_count=0,
            max_penetration_fraction=0.0,
            terminal_state=OrderBlockState.INVALIDATED,
        ),
        asset_id="BTC",
        confirmation_time_ns=120,
        lifecycle_revision="wrong",
    )

    with pytest.raises(ValueError, match="duration_ns"):
        lock_study_cohort(manifest(), (bad,))


def test_no_matching_subjects_fail_closed():
    with pytest.raises(ValueError, match="no study subjects"):
        lock_study_cohort(
            manifest(),
            (subject("btc", asset="BTC"),),
        )


def test_registered_analysis_requires_manifest_and_predeclaration():
    m = manifest()
    cohort = lock_study_cohort(
        m,
        (
            subject("event", duration=20, invalidated=True),
            subject("censor", duration=30, invalidated=False),
        ),
    )

    curve = registered_kaplan_meier(m, cohort)
    assert curve.records == 2
    assert curve.invalidations == 1

    strata = registered_evidence_strata(m, cohort)
    assert [item.label for item in strata] == ["TRUE_DEPTH"]

    no_strata = manifest(analysis_plan=("kaplan_meier",))
    with pytest.raises(ValueError, match="not predeclared"):
        registered_evidence_strata(no_strata, cohort)

    no_km = manifest(analysis_plan=("evidence_tier_strata",))
    with pytest.raises(ValueError, match="not predeclared"):
        registered_kaplan_meier(no_km, cohort)


def test_cohort_cannot_be_reused_under_different_manifest():
    first_manifest = manifest(study_name="first")
    cohort = lock_study_cohort(first_manifest, (subject("x"),))
    second_manifest = manifest(study_name="second")

    with pytest.raises(ValueError, match="not locked under"):
        registered_kaplan_meier(second_manifest, cohort)
