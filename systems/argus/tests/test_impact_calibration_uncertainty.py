from __future__ import annotations

from dataclasses import replace
import math

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
)
from argus.impact_calibration_uncertainty import (
    create_prospective_bootstrap_plan,
    registered_bootstrap_uncertainty,
)


BROKER_COMMIT = "2" * 40
ICARUS_COMMIT = "1" * 40


def curve():
    book = BookSnapshot(
        event_time_ns=100,
        sequence=7,
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
    price=101.0,
    filled=5.0,
    decision=120,
    completion=130,
    observed=140,
):
    average = None if filled == 0 else price
    if kind is ExecutionEvidenceKind.BROKER_CONFIRMED:
        return create_execution_evidence_receipt(
            evidence_kind=kind,
            source_system="example-broker",
            source_repo="broker/example-adapter",
            source_commit=BROKER_COMMIT,
            source_run_id="broker-session",
            source_execution_id=execution_id,
            symbol="NQ",
            decision_time_ns=decision,
            completion_time_ns=completion,
            observed_time_ns=observed,
            side=1,
            requested_size=5.0,
            filled_size=filled,
            average_price=average,
            source_payload={"fill_id": execution_id, "filled": filled},
            broker_name="Example Broker",
            broker_order_id=f"order-{execution_id}",
            broker_fill_id=execution_id,
        )

    return create_execution_evidence_receipt(
        evidence_kind=kind,
        source_system="icarus-paper-emulator",
        source_repo="reppiks490/Icarus",
        source_commit=ICARUS_COMMIT,
        source_run_id="paper-session",
        source_execution_id=execution_id,
        symbol="NQ",
        decision_time_ns=decision,
        completion_time_ns=completion,
        observed_time_ns=observed,
        side=1,
        requested_size=5.0,
        filled_size=filled,
        average_price=average,
        source_payload={"paper_fill": execution_id, "filled": filled},
    )


def subject(execution_id, **kwargs):
    row = calibrate_lineaged_impact(
        curve(),
        receipt(execution_id, **kwargs),
    )
    return ImpactCalibrationStudySubject(
        row=row,
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
    )


def broker_manifest(*, min_observations=1):
    return create_impact_calibration_study_manifest(
        study_name="broker-bootstrap-study",
        created_time_ns=90,
        cohort_start_ns=110,
        cohort_end_ns=200,
        observation_cutoff_ns=250,
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
        symbols=("NQ",),
        evidence_kinds=(ExecutionEvidenceKind.BROKER_CONFIRMED,),
        execution_source_revisions=(
            ("broker/example-adapter", BROKER_COMMIT),
        ),
        min_observations_per_stratum=min_observations,
        max_snapshot_age_ns=50,
        max_completion_latency_ns=50,
    )


def broker_cohort():
    m = broker_manifest(min_observations=3)
    c = lock_impact_calibration_study_cohort(
        m,
        (
            subject("b0", price=101.0),
            subject("b1", price=102.0),
            subject("b2", price=103.0),
        ),
        lock_time_ns=260,
    )
    return m, c


def mixed_study():
    m = create_impact_calibration_study_manifest(
        study_name="mixed-bootstrap-study",
        created_time_ns=90,
        cohort_start_ns=110,
        cohort_end_ns=200,
        observation_cutoff_ns=250,
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
        symbols=("NQ",),
        evidence_kinds=(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
        ),
        execution_source_revisions=(
            ("broker/example-adapter", BROKER_COMMIT),
            ("reppiks490/Icarus", ICARUS_COMMIT),
        ),
        min_observations_per_stratum=2,
        max_snapshot_age_ns=50,
        max_completion_latency_ns=50,
    )
    c = lock_impact_calibration_study_cohort(
        m,
        (
            subject("b0", price=101.0),
            subject("b1", price=102.0),
            subject(
                "p0",
                kind=ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                price=101.5,
            ),
            subject(
                "p1",
                kind=ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                price=102.5,
            ),
        ),
        lock_time_ns=260,
    )
    return m, c


def test_bootstrap_plan_is_prospective_content_addressed_and_deterministic():
    m = broker_manifest()
    first = create_prospective_bootstrap_plan(
        m,
        created_time_ns=95,
        bootstrap_replicates=200,
        bootstrap_seed=42,
    )
    same = create_prospective_bootstrap_plan(
        m,
        created_time_ns=95,
        bootstrap_replicates=200,
        bootstrap_seed=42,
    )
    changed_seed = create_prospective_bootstrap_plan(
        m,
        created_time_ns=95,
        bootstrap_replicates=200,
        bootstrap_seed=43,
    )
    changed_alpha = create_prospective_bootstrap_plan(
        m,
        created_time_ns=95,
        confidence_alpha=0.10,
        bootstrap_replicates=200,
        bootstrap_seed=42,
    )

    assert first == same
    assert first.plan_id.startswith("impact-calibration-bootstrap-plan:")
    assert first.schema_version == "argus-impact-calibration-bootstrap-plan-v1"
    assert first.execution_authorized is False
    assert first.production_decision_authorized is False
    assert changed_seed.plan_id != first.plan_id
    assert changed_alpha.plan_id != first.plan_id


def test_bootstrap_plan_must_be_registered_before_cohort_and_fail_bad_policy():
    m = broker_manifest()

    with pytest.raises(ValueError, match="at or before cohort_start"):
        create_prospective_bootstrap_plan(
            m,
            created_time_ns=111,
            bootstrap_replicates=200,
        )

    with pytest.raises(ValueError, match="between 200 and 10000"):
        create_prospective_bootstrap_plan(
            m,
            created_time_ns=95,
            bootstrap_replicates=199,
        )

    with pytest.raises(ValueError, match="at least 2"):
        create_prospective_bootstrap_plan(
            m,
            created_time_ns=95,
            bootstrap_replicates=200,
            min_metric_observations=1,
        )

    with pytest.raises(ValueError, match="unsupported bootstrap metrics"):
        create_prospective_bootstrap_plan(
            m,
            created_time_ns=95,
            bootstrap_replicates=200,
            metrics=("profit_factor",),
        )

    with pytest.raises(ValueError, match="confidence_alpha"):
        create_prospective_bootstrap_plan(
            m,
            created_time_ns=95,
            confidence_alpha=1.0,
            bootstrap_replicates=200,
        )


def test_registered_bootstrap_is_deterministic_and_matches_point_estimates():
    m, c = broker_cohort()
    plan = create_prospective_bootstrap_plan(
        m,
        created_time_ns=95,
        bootstrap_replicates=400,
        bootstrap_seed=12345,
        metrics=(
            "mean_slippage_error_ticks",
            "mean_absolute_slippage_error_ticks",
            "root_mean_squared_slippage_error_ticks",
            "slippage_underprediction_rate",
        ),
    )

    first = registered_bootstrap_uncertainty(plan, m, c)
    second = registered_bootstrap_uncertainty(plan, m, c)

    assert first == second
    assert len(first) == 1
    stratum = first[0]
    assert stratum.evidence_kind is ExecutionEvidenceKind.BROKER_CONFIRMED
    assert stratum.market_fill_confirmed is True
    assert stratum.broker_confirmed is True
    assert stratum.observations == 3
    assert stratum.execution_authorized is False
    assert stratum.production_decision_authorized is False

    intervals = {row.metric: row for row in stratum.intervals}
    assert intervals["mean_slippage_error_ticks"].estimate == pytest.approx(1.0)
    assert intervals["mean_absolute_slippage_error_ticks"].estimate == pytest.approx(1.0)
    assert intervals["root_mean_squared_slippage_error_ticks"].estimate == pytest.approx(
        math.sqrt(5.0 / 3.0)
    )
    assert intervals["slippage_underprediction_rate"].estimate == pytest.approx(
        2.0 / 3.0
    )

    for interval in intervals.values():
        assert interval.lower <= interval.upper
        assert interval.confidence_level == pytest.approx(0.95)
        assert interval.alpha == pytest.approx(0.05)
        assert interval.sample_size == 3
        assert interval.bootstrap_replicates == 400
        assert interval.method == "deterministic_nonparametric_percentile"


def test_bootstrap_never_pools_broker_and_paper_strata():
    m, c = mixed_study()
    plan = create_prospective_bootstrap_plan(
        m,
        created_time_ns=95,
        bootstrap_replicates=200,
        bootstrap_seed=7,
        metrics=("mean_slippage_error_ticks",),
    )

    strata = registered_bootstrap_uncertainty(plan, m, c)

    assert [row.evidence_kind for row in strata] == [
        ExecutionEvidenceKind.BROKER_CONFIRMED,
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
    ]
    assert [row.observations for row in strata] == [2, 2]
    assert strata[0].broker_confirmed is True
    assert strata[1].broker_confirmed is False
    assert strata[0].intervals[0].sample_size == 2
    assert strata[1].intervals[0].sample_size == 2


def test_slippage_metrics_require_predeclared_minimum_eligible_observations():
    m = create_impact_calibration_study_manifest(
        study_name="paper-missing-slippage",
        created_time_ns=90,
        cohort_start_ns=110,
        cohort_end_ns=200,
        observation_cutoff_ns=250,
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
        symbols=("NQ",),
        evidence_kinds=(ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,),
        execution_source_revisions=(
            ("reppiks490/Icarus", ICARUS_COMMIT),
        ),
        min_observations_per_stratum=2,
    )
    c = lock_impact_calibration_study_cohort(
        m,
        (
            subject(
                "p-fill",
                kind=ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                price=101.5,
            ),
            subject(
                "p-zero",
                kind=ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                filled=0.0,
            ),
        ),
        lock_time_ns=260,
    )
    plan = create_prospective_bootstrap_plan(
        m,
        created_time_ns=95,
        bootstrap_replicates=200,
        min_metric_observations=2,
        metrics=("mean_slippage_error_ticks",),
    )

    with pytest.raises(ValueError, match="has 1 eligible observations"):
        registered_bootstrap_uncertainty(plan, m, c)


def test_fill_error_metrics_can_use_zero_fill_observations():
    m = create_impact_calibration_study_manifest(
        study_name="paper-fill-error",
        created_time_ns=90,
        cohort_start_ns=110,
        cohort_end_ns=200,
        observation_cutoff_ns=250,
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
        symbols=("NQ",),
        evidence_kinds=(ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,),
        execution_source_revisions=(
            ("reppiks490/Icarus", ICARUS_COMMIT),
        ),
        min_observations_per_stratum=2,
    )
    c = lock_impact_calibration_study_cohort(
        m,
        (
            subject(
                "p-fill",
                kind=ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                price=101.5,
            ),
            subject(
                "p-zero",
                kind=ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                filled=0.0,
            ),
        ),
        lock_time_ns=260,
    )
    plan = create_prospective_bootstrap_plan(
        m,
        created_time_ns=95,
        bootstrap_replicates=200,
        min_metric_observations=2,
        metrics=(
            "mean_fill_fraction_error",
            "mean_absolute_fill_fraction_error",
        ),
    )

    strata = registered_bootstrap_uncertainty(plan, m, c)
    intervals = {row.metric: row for row in strata[0].intervals}
    assert intervals["mean_fill_fraction_error"].sample_size == 2
    assert intervals["mean_fill_fraction_error"].estimate == pytest.approx(-0.5)
    assert intervals["mean_absolute_fill_fraction_error"].estimate == pytest.approx(
        0.5
    )


def test_plan_and_cohort_tampering_fail_closed_before_resampling():
    m, c = broker_cohort()
    plan = create_prospective_bootstrap_plan(
        m,
        created_time_ns=95,
        bootstrap_replicates=200,
        metrics=("mean_slippage_error_ticks",),
    )

    with pytest.raises(ValueError, match="plan_id"):
        registered_bootstrap_uncertainty(
            replace(plan, bootstrap_seed=99),
            m,
            c,
        )

    with pytest.raises(ValueError, match="broker_confirmed_count"):
        registered_bootstrap_uncertainty(
            plan,
            m,
            replace(c, broker_confirmed_count=99),
        )

    with pytest.raises(ValueError, match="different manifest"):
        registered_bootstrap_uncertainty(
            replace(plan, manifest_id="not-the-study"),
            m,
            c,
        )


def test_bootstrap_plan_authority_escalation_is_rejected():
    m, c = broker_cohort()
    plan = create_prospective_bootstrap_plan(
        m,
        created_time_ns=95,
        bootstrap_replicates=200,
        metrics=("mean_slippage_error_ticks",),
    )

    with pytest.raises(ValueError, match="carries authority"):
        registered_bootstrap_uncertainty(
            replace(plan, execution_authorized=True),
            m,
            c,
        )
