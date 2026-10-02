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
from argus.impact_calibration_tail_transfer import (
    create_prospective_tail_transfer_plan,
    registered_tail_transfer_compatibility,
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
    kind,
    execution_id,
    *,
    price=101.0,
    filled=5.0,
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
            decision_time_ns=120,
            completion_time_ns=130,
            observed_time_ns=140,
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
        decision_time_ns=120,
        completion_time_ns=130,
        observed_time_ns=140,
        side=1,
        requested_size=5.0,
        filled_size=filled,
        average_price=average,
        source_payload={"paper_fill": execution_id, "filled": filled},
    )


def subject(kind, execution_id, **kwargs):
    return ImpactCalibrationStudySubject(
        row=calibrate_lineaged_impact(
            curve(),
            receipt(kind, execution_id, **kwargs),
        ),
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
    )


def manifest(*, min_observations=3, evidence_kinds=None):
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
        study_name="tail-transfer",
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
    m = manifest(min_observations=3)
    broker_fills = broker_fills or [5.0] * len(broker_prices)
    paper_fills = paper_fills or [5.0] * len(paper_prices)
    subjects = []

    for i, (price, filled) in enumerate(zip(broker_prices, broker_fills)):
        subjects.append(
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                f"b{i}",
                price=price,
                filled=filled,
            )
        )
    for i, (price, filled) in enumerate(zip(paper_prices, paper_fills)):
        subjects.append(
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                f"p{i}",
                price=price,
                filled=filled,
            )
        )

    c = lock_impact_calibration_study_cohort(
        m,
        tuple(subjects),
        lock_time_ns=260,
    )
    return m, c


def plan(
    m,
    *,
    metric="slippage_error_ticks",
    quantile_tolerances=((0.50, 1.0), (0.90, 1.0)),
    seed=7,
    minimum=3,
):
    return create_prospective_tail_transfer_plan(
        m,
        created_time_ns=95,
        metric=metric,
        quantile_tolerances=quantile_tolerances,
        confidence_alpha=0.05,
        bootstrap_replicates=400,
        bootstrap_seed=seed,
        min_metric_observations_per_kind=minimum,
    )


def test_tail_plan_is_prospective_content_addressed_and_deterministic():
    m = manifest()
    first = plan(m, seed=7)
    same = plan(m, seed=7)
    changed_seed = plan(m, seed=8)
    changed_tolerance = plan(
        m,
        quantile_tolerances=((0.50, 0.5), (0.90, 1.0)),
    )

    assert first == same
    assert first.plan_id.startswith(
        "impact-calibration-tail-transfer-plan:"
    )
    assert first.schema_version == (
        "argus-impact-calibration-tail-transfer-plan-v1"
    )
    assert first.execution_authorized is False
    assert first.production_decision_authorized is False
    assert changed_seed.plan_id != first.plan_id
    assert changed_tolerance.plan_id != first.plan_id


def test_tail_plan_requires_both_evidence_classes_and_valid_policy():
    broker_only = manifest(
        evidence_kinds=(ExecutionEvidenceKind.BROKER_CONFIRMED,)
    )

    with pytest.raises(ValueError, match="requires both"):
        plan(broker_only)

    m = manifest()
    with pytest.raises(ValueError, match="cannot predate manifest"):
        create_prospective_tail_transfer_plan(
            m,
            created_time_ns=89,
            metric="slippage_error_ticks",
            quantile_tolerances=((0.9, 1.0),),
            bootstrap_replicates=200,
        )

    with pytest.raises(ValueError, match="at or before cohort_start"):
        create_prospective_tail_transfer_plan(
            m,
            created_time_ns=111,
            metric="slippage_error_ticks",
            quantile_tolerances=((0.9, 1.0),),
            bootstrap_replicates=200,
        )

    with pytest.raises(ValueError, match="unsupported tail transfer metric"):
        create_prospective_tail_transfer_plan(
            m,
            created_time_ns=95,
            metric="profit_factor",
            quantile_tolerances=((0.9, 1.0),),
            bootstrap_replicates=200,
        )

    with pytest.raises(ValueError, match="strictly between 0 and 1"):
        create_prospective_tail_transfer_plan(
            m,
            created_time_ns=95,
            metric="slippage_error_ticks",
            quantile_tolerances=((1.0, 1.0),),
            bootstrap_replicates=200,
        )

    with pytest.raises(ValueError, match="duplicate quantiles"):
        create_prospective_tail_transfer_plan(
            m,
            created_time_ns=95,
            metric="slippage_error_ticks",
            quantile_tolerances=((0.9, 1.0), (0.9, 2.0)),
            bootstrap_replicates=200,
        )

    with pytest.raises(ValueError, match="at least 3"):
        create_prospective_tail_transfer_plan(
            m,
            created_time_ns=95,
            metric="slippage_error_ticks",
            quantile_tolerances=((0.9, 1.0),),
            bootstrap_replicates=200,
            min_metric_observations_per_kind=2,
        )


def test_tail_transfer_detects_paper_optimism_at_upper_quantiles():
    m, c = cohort_for(
        broker_prices=(101.0, 102.0, 104.0, 106.0),
        paper_prices=(101.0, 101.5, 102.0, 102.5),
    )
    p = plan(
        m,
        quantile_tolerances=((0.90, 1.0),),
        minimum=3,
    )

    result = registered_tail_transfer_compatibility(p, m, c)
    row = result.quantiles[0]

    assert row.quantile == pytest.approx(0.90)
    assert row.broker_quantile == pytest.approx(4.4)
    assert row.paper_quantile == pytest.approx(1.35)
    assert row.paper_minus_broker == pytest.approx(-3.05)
    assert row.broker_sample_size == 4
    assert row.paper_sample_size == 4
    assert row.lower <= row.paper_minus_broker <= row.upper
    assert row.within_tolerance is False
    assert result.all_within_tolerance is False
    assert result.execution_authorized is False
    assert result.production_decision_authorized is False


def test_identical_tail_distributions_fit_a_wide_predeclared_tolerance():
    m, c = cohort_for(
        broker_prices=(101.0, 101.5, 102.0, 102.5),
        paper_prices=(101.0, 101.5, 102.0, 102.5),
    )
    p = plan(
        m,
        quantile_tolerances=((0.50, 2.0), (0.90, 2.0)),
    )

    result = registered_tail_transfer_compatibility(p, m, c)

    assert len(result.quantiles) == 2
    assert all(
        row.paper_minus_broker == pytest.approx(0.0)
        for row in result.quantiles
    )
    assert all(row.within_tolerance for row in result.quantiles)
    assert result.all_within_tolerance is True


def test_absolute_slippage_error_tail_uses_absolute_values():
    m, c = cohort_for(
        broker_prices=(100.0, 101.0, 102.0, 103.0),
        paper_prices=(100.5, 101.0, 101.5, 102.0),
    )
    p = plan(
        m,
        metric="absolute_slippage_error_ticks",
        quantile_tolerances=((0.50, 2.0),),
    )

    result = registered_tail_transfer_compatibility(p, m, c)
    row = result.quantiles[0]

    assert row.broker_quantile == pytest.approx(1.0)
    assert row.paper_quantile == pytest.approx(0.5)
    assert row.paper_minus_broker == pytest.approx(-0.5)


def test_zero_fill_rows_are_not_invented_as_tail_slippage():
    m, c = cohort_for(
        broker_prices=(101.0, 102.0, 101.0),
        paper_prices=(101.0, 102.0, 101.0),
        broker_fills=(5.0, 5.0, 0.0),
        paper_fills=(5.0, 5.0, 0.0),
    )
    p = plan(
        m,
        quantile_tolerances=((0.90, 1.0),),
        minimum=3,
    )

    with pytest.raises(ValueError, match="got broker=2, paper=2"):
        registered_tail_transfer_compatibility(p, m, c)


def test_tail_transfer_is_deterministic_for_same_plan_and_cohort():
    m, c = cohort_for(
        broker_prices=(101.0, 102.0, 103.0, 104.0),
        paper_prices=(101.25, 101.75, 102.25, 102.75),
    )
    p = plan(
        m,
        quantile_tolerances=((0.50, 3.0), (0.90, 3.0)),
        seed=123,
    )

    first = registered_tail_transfer_compatibility(p, m, c)
    second = registered_tail_transfer_compatibility(p, m, c)

    assert first == second
    assert all(
        row.method == "deterministic_two_sample_quantile_percentile"
        for row in first.quantiles
    )
    assert all(row.bootstrap_replicates == 400 for row in first.quantiles)


def test_tail_plan_and_cohort_tampering_fail_closed():
    m, c = cohort_for(
        broker_prices=(101.0, 102.0, 103.0),
        paper_prices=(101.5, 101.75, 102.0),
    )
    p = plan(m, quantile_tolerances=((0.90, 2.0),))

    with pytest.raises(ValueError, match="predates manifest"):
        registered_tail_transfer_compatibility(
            replace(p, created_time_ns=89),
            m,
            c,
        )

    with pytest.raises(ValueError, match="plan_id"):
        registered_tail_transfer_compatibility(
            replace(
                p,
                quantile_tolerances=((0.90, 99.0),),
            ),
            m,
            c,
        )

    with pytest.raises(ValueError, match="broker_confirmed_count"):
        registered_tail_transfer_compatibility(
            p,
            m,
            replace(c, broker_confirmed_count=99),
        )

    with pytest.raises(ValueError, match="different manifest"):
        registered_tail_transfer_compatibility(
            replace(p, manifest_id="wrong"),
            m,
            c,
        )


def test_tail_plan_authority_escalation_is_rejected():
    m, c = cohort_for(
        broker_prices=(101.0, 102.0, 103.0),
        paper_prices=(101.5, 101.75, 102.0),
    )
    p = plan(m, quantile_tolerances=((0.90, 2.0),))

    with pytest.raises(ValueError, match="carries authority"):
        registered_tail_transfer_compatibility(
            replace(p, execution_authorized=True),
            m,
            c,
        )
