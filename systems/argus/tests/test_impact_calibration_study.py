from __future__ import annotations

from dataclasses import replace

import pytest

from argus.contracts import BookLevel, BookSnapshot
from argus.execution_evidence import (
    ExecutionEvidenceKind,
    calibrate_lineaged_impact,
    create_execution_evidence_receipt,
)
from argus.impact import depth_impact_curve
from argus.impact_calibration_study import (
    ImpactCalibrationStudySubject,
    create_impact_calibration_study_manifest,
    lock_impact_calibration_study_cohort,
    registered_evidence_stratified_summary,
)


ICARUS_COMMIT = "1" * 40
BROKER_COMMIT = "2" * 40
IMPACT_REVISION = "argus-depth-impact-v1"
CALIBRATION_REVISION = "argus-impact-calibration-v1"


def curve(*, event_time_ns=100, sequence=7):
    book = BookSnapshot(
        event_time_ns=event_time_ns,
        sequence=sequence,
        bids=(BookLevel(99.0, 10.0), BookLevel(98.0, 20.0)),
        asks=(BookLevel(101.0, 8.0), BookLevel(102.0, 20.0)),
    )
    return depth_impact_curve(
        book,
        side=1,
        sizes=(5.0,),
        tick_size=1.0,
        capacity_threshold_ticks=(0.0, 1.0),
    )


def receipt(
    execution_id,
    *,
    kind=ExecutionEvidenceKind.BROKER_CONFIRMED,
    symbol="NQ",
    source_repo=None,
    source_commit=None,
    decision=120,
    completion=130,
    observed=140,
    price=101.5,
):
    if kind is ExecutionEvidenceKind.BROKER_CONFIRMED:
        repo = source_repo or "broker/example-adapter"
        commit = source_commit or BROKER_COMMIT
        return create_execution_evidence_receipt(
            evidence_kind=kind,
            source_system="example-broker",
            source_repo=repo,
            source_commit=commit,
            source_run_id="broker-session",
            source_execution_id=execution_id,
            symbol=symbol,
            decision_time_ns=decision,
            completion_time_ns=completion,
            observed_time_ns=observed,
            side=1,
            requested_size=5.0,
            filled_size=5.0,
            average_price=price,
            source_payload={"fill_id": execution_id, "qty": 5},
            broker_name="Example Broker",
            broker_order_id=f"order-{execution_id}",
            broker_fill_id=execution_id,
        )

    repo = source_repo or "reppiks490/Icarus"
    commit = source_commit or ICARUS_COMMIT
    return create_execution_evidence_receipt(
        evidence_kind=kind,
        source_system="icarus-paper-emulator",
        source_repo=repo,
        source_commit=commit,
        source_run_id="icarus-paper-run",
        source_execution_id=execution_id,
        symbol=symbol,
        decision_time_ns=decision,
        completion_time_ns=completion,
        observed_time_ns=observed,
        side=1,
        requested_size=5.0,
        filled_size=5.0,
        average_price=price,
        source_payload={"paper_fill": execution_id, "qty": 5},
    )


def subject(
    execution_id,
    *,
    kind=ExecutionEvidenceKind.BROKER_CONFIRMED,
    impact_revision=IMPACT_REVISION,
    calibration_revision=CALIBRATION_REVISION,
    curve_value=None,
    **receipt_kwargs,
):
    row = calibrate_lineaged_impact(
        curve_value or curve(),
        receipt(execution_id, kind=kind, **receipt_kwargs),
    )
    return ImpactCalibrationStudySubject(
        row=row,
        impact_model_revision=impact_revision,
        calibration_revision=calibration_revision,
    )


def manifest(**overrides):
    params = dict(
        study_name="prospective-impact-calibration",
        created_time_ns=90,
        cohort_start_ns=110,
        cohort_end_ns=200,
        observation_cutoff_ns=250,
        impact_model_revision=IMPACT_REVISION,
        calibration_revision=CALIBRATION_REVISION,
        symbols=("NQ",),
        evidence_kinds=(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
        ),
        execution_source_revisions=(
            ("broker/example-adapter", BROKER_COMMIT),
            ("reppiks490/Icarus", ICARUS_COMMIT),
        ),
        min_observations_per_stratum=1,
        max_snapshot_age_ns=50,
        max_completion_latency_ns=50,
    )
    params.update(overrides)
    return create_impact_calibration_study_manifest(**params)


def complete_subjects():
    return (
        subject("broker-1"),
        subject(
            "paper-1",
            kind=ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
        ),
    )


def test_manifest_is_deterministic_and_pins_design_choices():
    first = manifest()
    same = manifest()
    changed_source = manifest(
        execution_source_revisions=(
            ("broker/example-adapter", "3" * 40),
            ("reppiks490/Icarus", ICARUS_COMMIT),
        )
    )
    changed_minimum = manifest(min_observations_per_stratum=2)

    assert first == same
    assert first.manifest_id.startswith("impact-calibration-study:")
    assert first.schema_version == "argus-impact-calibration-study-v1"
    assert first.execution_authorized is False
    assert first.production_decision_authorized is False
    assert changed_source.manifest_id != first.manifest_id
    assert changed_minimum.manifest_id != first.manifest_id


def test_manifest_must_be_registered_before_cohort_and_pin_real_shas():
    with pytest.raises(ValueError, match="created at or before"):
        manifest(created_time_ns=111)

    with pytest.raises(ValueError, match="before cohort_end"):
        manifest(cohort_start_ns=200, cohort_end_ns=200)

    with pytest.raises(ValueError, match="at or after cohort_end"):
        manifest(observation_cutoff_ns=199)

    with pytest.raises(ValueError, match="40-character"):
        manifest(
            execution_source_revisions=(
                ("broker/example-adapter", "short"),
            ),
            evidence_kinds=(ExecutionEvidenceKind.BROKER_CONFIRMED,),
        )

    with pytest.raises(ValueError, match="positive integer"):
        manifest(min_observations_per_stratum=0)


def test_lock_cannot_happen_before_predeclared_observation_cutoff():
    m = manifest()

    with pytest.raises(ValueError, match="before observation_cutoff"):
        lock_impact_calibration_study_cohort(
            m,
            complete_subjects(),
            lock_time_ns=249,
        )

    cohort = lock_impact_calibration_study_cohort(
        m,
        complete_subjects(),
        lock_time_ns=250,
    )
    assert cohort.lock_time_ns == 250


def test_registered_summary_keeps_broker_and_paper_strata_separate():
    m = manifest()
    cohort = lock_impact_calibration_study_cohort(
        m,
        complete_subjects(),
        lock_time_ns=260,
    )
    strata = registered_evidence_stratified_summary(m, cohort)

    assert cohort.broker_confirmed_count == 1
    assert cohort.paper_emulator_count == 1
    assert cohort.included_lineage_ids == tuple(
        sorted(cohort.included_lineage_ids)
    )
    assert [row.evidence_kind for row in strata] == [
        ExecutionEvidenceKind.BROKER_CONFIRMED,
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
    ]
    assert [row.observations for row in strata] == [1, 1]
    assert strata[0].broker_confirmed is True
    assert strata[1].broker_confirmed is False


def test_source_revision_symbol_and_timing_are_predeclared_filters():
    m = manifest(
        evidence_kinds=(ExecutionEvidenceKind.BROKER_CONFIRMED,),
        execution_source_revisions=(
            ("broker/example-adapter", BROKER_COMMIT),
        ),
    )
    good = subject("good")
    wrong_revision = subject(
        "wrong-revision",
        source_commit="4" * 40,
    )
    wrong_symbol = subject("wrong-symbol", symbol="ES")
    too_early = subject("too-early", decision=109)
    observed_late = subject(
        "observed-late",
        decision=150,
        completion=160,
        observed=251,
    )

    cohort = lock_impact_calibration_study_cohort(
        m,
        (
            good,
            wrong_revision,
            wrong_symbol,
            too_early,
            observed_late,
        ),
        lock_time_ns=260,
    )

    reasons = dict(cohort.exclusions)
    assert len(cohort.subjects) == 1
    assert reasons[wrong_revision.row.lineage_id] == (
        "execution_source_revision_not_in_manifest"
    )
    assert reasons[wrong_symbol.row.lineage_id] == "symbol_not_in_manifest"
    assert reasons[too_early.row.lineage_id] == "decision_before_cohort"
    assert reasons[observed_late.row.lineage_id] == (
        "execution_observed_after_cutoff"
    )


def test_revision_and_latency_filters_are_locked_before_results():
    m = manifest(
        evidence_kinds=(ExecutionEvidenceKind.BROKER_CONFIRMED,),
        execution_source_revisions=(
            ("broker/example-adapter", BROKER_COMMIT),
        ),
        max_snapshot_age_ns=25,
        max_completion_latency_ns=15,
    )
    good = subject("good")
    wrong_impact = subject(
        "wrong-impact",
        impact_revision="different-impact",
    )
    wrong_calibration = subject(
        "wrong-calibration",
        calibration_revision="different-calibration",
    )
    stale_snapshot = subject(
        "stale-snapshot",
        decision=130,
        completion=140,
        observed=150,
    )
    slow_completion = subject(
        "slow-completion",
        decision=120,
        completion=140,
        observed=150,
    )

    cohort = lock_impact_calibration_study_cohort(
        m,
        (
            good,
            wrong_impact,
            wrong_calibration,
            stale_snapshot,
            slow_completion,
        ),
        lock_time_ns=260,
    )
    reasons = dict(cohort.exclusions)

    assert reasons[wrong_impact.row.lineage_id] == (
        "impact_model_revision_mismatch"
    )
    assert reasons[wrong_calibration.row.lineage_id] == (
        "calibration_revision_mismatch"
    )
    assert reasons[stale_snapshot.row.lineage_id] == (
        "snapshot_age_exceeds_manifest"
    )
    assert reasons[slow_completion.row.lineage_id] == (
        "completion_latency_exceeds_manifest"
    )


def test_every_declared_evidence_stratum_must_meet_minimum():
    m = manifest(min_observations_per_stratum=1)

    with pytest.raises(ValueError, match="insufficient observations"):
        lock_impact_calibration_study_cohort(
            m,
            (subject("broker-only"),),
            lock_time_ns=260,
        )

    m_two = manifest(
        evidence_kinds=(ExecutionEvidenceKind.BROKER_CONFIRMED,),
        execution_source_revisions=(
            ("broker/example-adapter", BROKER_COMMIT),
        ),
        min_observations_per_stratum=2,
    )
    with pytest.raises(ValueError, match="insufficient observations"):
        lock_impact_calibration_study_cohort(
            m_two,
            (subject("only-one"),),
            lock_time_ns=260,
        )


def test_same_execution_receipt_cannot_be_counted_against_two_curves():
    r = receipt("same")
    first = ImpactCalibrationStudySubject(
        row=calibrate_lineaged_impact(curve(), r),
        impact_model_revision=IMPACT_REVISION,
        calibration_revision=CALIBRATION_REVISION,
    )
    second = ImpactCalibrationStudySubject(
        row=calibrate_lineaged_impact(
            curve(event_time_ns=101, sequence=8),
            r,
        ),
        impact_model_revision=IMPACT_REVISION,
        calibration_revision=CALIBRATION_REVISION,
    )

    m = manifest(
        evidence_kinds=(ExecutionEvidenceKind.BROKER_CONFIRMED,),
        execution_source_revisions=(
            ("broker/example-adapter", BROKER_COMMIT),
        ),
    )
    with pytest.raises(ValueError, match="duplicate execution receipt"):
        lock_impact_calibration_study_cohort(
            m,
            (first, second),
            lock_time_ns=260,
        )


def test_cohort_tampering_breaks_identity_or_membership():
    m = manifest()
    cohort = lock_impact_calibration_study_cohort(
        m,
        complete_subjects(),
        lock_time_ns=260,
    )

    with pytest.raises(ValueError, match="broker_confirmed_count"):
        registered_evidence_stratified_summary(
            m,
            replace(cohort, broker_confirmed_count=99),
        )

    with pytest.raises(ValueError, match="lock_time_ns"):
        registered_evidence_stratified_summary(
            m,
            replace(cohort, lock_time_ns=249),
        )

    changed_subject = replace(
        cohort.subjects[0],
        impact_model_revision="after-the-fact",
    )
    tampered = replace(
        cohort,
        subjects=(changed_subject, cohort.subjects[1]),
    )
    with pytest.raises(ValueError, match="impact model revision"):
        registered_evidence_stratified_summary(m, tampered)


def test_cohort_rejects_unknown_exclusion_reason():
    m = manifest(
        evidence_kinds=(ExecutionEvidenceKind.BROKER_CONFIRMED,),
        execution_source_revisions=(
            ("broker/example-adapter", BROKER_COMMIT),
        ),
    )
    good = subject("good")
    excluded = subject("excluded", symbol="ES")
    cohort = lock_impact_calibration_study_cohort(
        m,
        (good, excluded),
        lock_time_ns=260,
    )
    bad = replace(
        cohort,
        exclusions=((excluded.row.lineage_id, "invented_reason"),),
    )

    with pytest.raises(ValueError, match="unknown exclusion reason"):
        registered_evidence_stratified_summary(m, bad)


def test_authority_escalation_is_rejected():
    m = manifest()
    cohort = lock_impact_calibration_study_cohort(
        m,
        complete_subjects(),
        lock_time_ns=260,
    )

    with pytest.raises(ValueError, match="manifest carries authority"):
        registered_evidence_stratified_summary(
            replace(m, execution_authorized=True),
            cohort,
        )

    with pytest.raises(ValueError, match="cohort carries authority"):
        registered_evidence_stratified_summary(
            m,
            replace(cohort, production_decision_authorized=True),
        )
