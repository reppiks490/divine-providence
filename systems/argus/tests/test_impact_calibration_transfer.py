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
)
from argus.impact_calibration_transfer import (
    create_prospective_transfer_plan,
    registered_transfer_compatibility,
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
    kind,
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


def subject(execution_id, *, kind, **kwargs):
    return ImpactCalibrationStudySubject(
        row=calibrate_lineaged_impact(
            curve(),
            receipt(execution_id, kind=kind, **kwargs),
        ),
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
    )


def manifest(*, min_observations=2, evidence_kinds=None):
    kinds = evidence_kinds or (
        ExecutionEvidenceKind.BROKER_CONFIRMED,
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
    )
    revisions = []
    if ExecutionEvidenceKind.BROKER_CONFIRMED in kinds:
        revisions.append(("broker/example-adapter", BROKER_COMMIT))
    if ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR in kinds:
        revisions.append(("reppiks490/Icarus", ICARUS_COMMIT))

    return create_impact_calibration_study_manifest(
        study_name="paper-broker-transfer",
        created_time_ns=90,
        cohort_start_ns=110,
        cohort_end_ns=200,
        observation_cutoff_ns=250,
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
        symbols=("NQ",),
        evidence_kinds=kinds,
        execution_source_revisions=tuple(revisions),
        min_observations_per_stratum=min_observations,
        max_snapshot_age_ns=50,
        max_completion_latency_ns=50,
    )


def cohort_for(
    broker_prices,
    paper_prices,
    *,
    broker_fills=None,
    paper_fills=None,
):
    m = manifest(min_observations=2)
    subjects = []
    broker_fills = broker_fills or [5.0] * len(broker_prices)
    paper_fills = paper_fills or [5.0] * len(paper_prices)

    for index, (price, filled) in enumerate(
        zip(broker_prices, broker_fills)
    ):
        subjects.append(
            subject(
                f"b{index}",
                kind=ExecutionEvidenceKind.BROKER_CONFIRMED,
                price=price,
                filled=filled,
            )
        )
    for index, (price, filled) in enumerate(
        zip(paper_prices, paper_fills)
    ):
        subjects.append(
            subject(
                f"p{index}",
                kind=ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                price=price,
                filled=filled,
            )
        )

    cohort = lock_impact_calibration_study_cohort(
        m,
        tuple(subjects),
        lock_time_ns=260,
    )
    return m, cohort


def plan(
    m,
    *,
    tolerance=0.5,
    metrics=("mean_slippage_error_ticks",),
    seed=7,
):
    return create_prospective_transfer_plan(
        m,
        created_time_ns=95,
        confidence_alpha=0.05,
        bootstrap_replicates=400,
        bootstrap_seed=seed,
        min_metric_observations_per_kind=2,
        metrics=metrics,
        tolerances={metric: tolerance for metric in metrics},
    )


def test_transfer_plan_is_prospective_content_addressed_and_deterministic():
    m = manifest()
    first = plan(m, seed=7)
    same = plan(m, seed=7)
    changed_seed = plan(m, seed=8)
    changed_tolerance = plan(m, tolerance=0.25)

    assert first == same
    assert first.plan_id.startswith("impact-calibration-transfer-plan:")
    assert first.schema_version == "argus-impact-calibration-transfer-plan-v1"
    assert first.execution_authorized is False
    assert first.production_decision_authorized is False
    assert changed_seed.plan_id != first.plan_id
    assert changed_tolerance.plan_id != first.plan_id


def test_transfer_plan_requires_both_evidence_classes_and_pre_registration():
    broker_only = manifest(
        evidence_kinds=(ExecutionEvidenceKind.BROKER_CONFIRMED,)
    )

    with pytest.raises(ValueError, match="requires both"):
        create_prospective_transfer_plan(
            broker_only,
            created_time_ns=95,
            bootstrap_replicates=200,
            metrics=("mean_slippage_error_ticks",),
            tolerances={"mean_slippage_error_ticks": 0.5},
        )

    m = manifest()
    with pytest.raises(ValueError, match="cannot predate manifest"):
        create_prospective_transfer_plan(
            m,
            created_time_ns=89,
            bootstrap_replicates=200,
            metrics=("mean_slippage_error_ticks",),
            tolerances={"mean_slippage_error_ticks": 0.5},
        )

    with pytest.raises(ValueError, match="at or before cohort_start"):
        create_prospective_transfer_plan(
            m,
            created_time_ns=111,
            bootstrap_replicates=200,
            metrics=("mean_slippage_error_ticks",),
            tolerances={"mean_slippage_error_ticks": 0.5},
        )

    with pytest.raises(ValueError, match="exactly one value"):
        create_prospective_transfer_plan(
            m,
            created_time_ns=95,
            bootstrap_replicates=200,
            metrics=("mean_slippage_error_ticks",),
            tolerances={},
        )


def test_transfer_detects_paper_optimism_without_pooling_evidence():
    m, c = cohort_for(
        broker_prices=(102.0, 103.0),
        paper_prices=(101.1, 101.2),
    )
    p = plan(m, tolerance=0.5)

    result = registered_transfer_compatibility(p, m, c)
    metric = result.metrics[0]

    assert metric.metric == "mean_slippage_error_ticks"
    assert metric.broker_estimate == pytest.approx(1.5)
    assert metric.paper_estimate == pytest.approx(0.15)
    assert metric.paper_minus_broker == pytest.approx(-1.35)
    assert metric.broker_sample_size == 2
    assert metric.paper_sample_size == 2
    assert metric.lower <= metric.paper_minus_broker <= metric.upper
    assert metric.tolerance == pytest.approx(0.5)
    assert metric.within_tolerance is False
    assert result.all_within_tolerance is False
    assert result.execution_authorized is False
    assert result.production_decision_authorized is False


def test_transfer_can_meet_a_predeclared_wide_compatibility_tolerance():
    m, c = cohort_for(
        broker_prices=(101.2, 101.3),
        paper_prices=(101.25, 101.35),
    )
    p = plan(m, tolerance=0.5)

    result = registered_transfer_compatibility(p, m, c)
    metric = result.metrics[0]

    assert metric.paper_minus_broker == pytest.approx(0.05)
    assert metric.lower >= -0.5
    assert metric.upper <= 0.5
    assert metric.within_tolerance is True
    assert result.all_within_tolerance is True


def test_transfer_is_deterministic_for_same_plan_and_cohort():
    m, c = cohort_for(
        broker_prices=(101.0, 102.0, 103.0),
        paper_prices=(101.5, 101.75, 102.0),
    )
    p = plan(
        m,
        tolerance=2.0,
        metrics=(
            "mean_slippage_error_ticks",
            "mean_absolute_slippage_error_ticks",
            "root_mean_squared_slippage_error_ticks",
            "slippage_underprediction_rate",
        ),
        seed=123,
    )

    first = registered_transfer_compatibility(p, m, c)
    second = registered_transfer_compatibility(p, m, c)

    assert first == second
    assert [row.metric for row in first.metrics] == list(p.metrics)
    assert all(row.bootstrap_replicates == 400 for row in first.metrics)
    assert all(
        row.method == "deterministic_two_sample_percentile"
        for row in first.metrics
    )


def test_zero_fill_does_not_become_slippage_and_minimum_fails_closed():
    m, c = cohort_for(
        broker_prices=(101.5, 101.0),
        paper_prices=(101.5, 101.0),
        broker_fills=(5.0, 0.0),
        paper_fills=(5.0, 0.0),
    )
    p = plan(m, tolerance=1.0)

    with pytest.raises(ValueError, match="got broker=1, paper=1"):
        registered_transfer_compatibility(p, m, c)


def test_fill_fraction_transfer_can_include_zero_fill_rows():
    m, c = cohort_for(
        broker_prices=(101.5, 101.0),
        paper_prices=(101.5, 101.0),
        broker_fills=(5.0, 0.0),
        paper_fills=(5.0, 0.0),
    )
    p = plan(
        m,
        tolerance=0.25,
        metrics=(
            "mean_fill_fraction_error",
            "mean_absolute_fill_fraction_error",
        ),
    )

    result = registered_transfer_compatibility(p, m, c)

    assert len(result.metrics) == 2
    assert all(row.broker_sample_size == 2 for row in result.metrics)
    assert all(row.paper_sample_size == 2 for row in result.metrics)
    assert all(row.paper_minus_broker == pytest.approx(0.0) for row in result.metrics)
    assert result.all_within_tolerance is True


def test_transfer_plan_and_cohort_tampering_fail_closed():
    m, c = cohort_for(
        broker_prices=(102.0, 103.0),
        paper_prices=(101.5, 101.75),
    )
    p = plan(m, tolerance=1.0)

    with pytest.raises(ValueError, match="plan_id"):
        registered_transfer_compatibility(
            replace(
                p,
                tolerances=(("mean_slippage_error_ticks", 9.0),),
            ),
            m,
            c,
        )

    with pytest.raises(ValueError, match="broker_confirmed_count"):
        registered_transfer_compatibility(
            p,
            m,
            replace(c, broker_confirmed_count=99),
        )

    with pytest.raises(ValueError, match="different manifest"):
        registered_transfer_compatibility(
            replace(p, manifest_id="wrong"),
            m,
            c,
        )


def test_transfer_plan_authority_escalation_is_rejected():
    m, c = cohort_for(
        broker_prices=(102.0, 103.0),
        paper_prices=(101.5, 101.75),
    )
    p = plan(m, tolerance=1.0)

    with pytest.raises(ValueError, match="carries authority"):
        registered_transfer_compatibility(
            replace(p, execution_authorized=True),
            m,
            c,
        )
