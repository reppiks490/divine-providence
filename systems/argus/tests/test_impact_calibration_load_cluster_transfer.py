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
from argus.impact_calibration_load_cluster_transfer import (
    create_prospective_load_cluster_transfer_plan,
    registered_load_cluster_transfer_compatibility,
)
from argus.impact_calibration_study import (
    ImpactCalibrationStudySubject,
    create_impact_calibration_study_manifest,
    lock_impact_calibration_study_cohort,
)


BROKER_COMMIT = "2" * 40
ICARUS_COMMIT = "1" * 40

BANDS = (
    ("low-load", 0.0, 0.30),
    ("high-load", 0.30, None),
)


def curve(*, visible_size, sequence):
    first = visible_size * 0.4
    second = visible_size - first
    book = BookSnapshot(
        event_time_ns=100,
        sequence=sequence,
        bids=(BookLevel(99.0, 10.0), BookLevel(98.0, 20.0)),
        asks=(BookLevel(101.0, first), BookLevel(102.0, second)),
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
    price,
    run_id,
    filled=5.0,
):
    average = None if filled == 0 else price
    if kind is ExecutionEvidenceKind.BROKER_CONFIRMED:
        return create_execution_evidence_receipt(
            evidence_kind=kind,
            source_system="example-broker",
            source_repo="broker/example-adapter",
            source_commit=BROKER_COMMIT,
            source_run_id=run_id,
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
        source_run_id=run_id,
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


def subject(
    kind,
    execution_id,
    *,
    price,
    visible_size,
    sequence,
    run_id,
    filled=5.0,
):
    return ImpactCalibrationStudySubject(
        row=calibrate_lineaged_impact(
            curve(visible_size=visible_size, sequence=sequence),
            receipt(
                kind,
                execution_id,
                price=price,
                run_id=run_id,
                filled=filled,
            ),
        ),
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
    )


def manifest(*, min_observations=4, evidence_kinds=None):
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
        study_name="load-cluster-transfer",
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


def study():
    m = manifest()
    subjects = (
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-low-a",
            price=101.20,
            visible_size=50.0,
            sequence=10,
            run_id="b-low-run-a",
        ),
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-low-b",
            price=101.30,
            visible_size=50.0,
            sequence=11,
            run_id="b-low-run-b",
        ),
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-high-a",
            price=102.00,
            visible_size=10.0,
            sequence=12,
            run_id="b-high-run-a",
        ),
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-high-b",
            price=103.00,
            visible_size=10.0,
            sequence=13,
            run_id="b-high-run-b",
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-low-a",
            price=101.25,
            visible_size=50.0,
            sequence=20,
            run_id="p-low-run-a",
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-low-b",
            price=101.35,
            visible_size=50.0,
            sequence=21,
            run_id="p-low-run-b",
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-high-a",
            price=101.10,
            visible_size=10.0,
            sequence=22,
            run_id="p-high-run-a",
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-high-b",
            price=101.20,
            visible_size=10.0,
            sequence=23,
            run_id="p-high-run-b",
        ),
    )
    c = lock_impact_calibration_study_cohort(
        m,
        subjects,
        lock_time_ns=260,
    )
    return m, c


def plan(
    m,
    *,
    metric="mean_slippage_error_ticks",
    seed=7,
    low_tolerance=0.20,
    high_tolerance=0.50,
):
    return create_prospective_load_cluster_transfer_plan(
        m,
        created_time_ns=95,
        load_bands=BANDS,
        metrics=(metric,),
        tolerances={
            ("low-load", metric): low_tolerance,
            ("high-load", metric): high_tolerance,
        },
        confidence_alpha=0.05,
        bootstrap_replicates=400,
        bootstrap_seed=seed,
        min_clusters_per_kind_per_band=2,
        min_metric_observations_per_kind_per_band=2,
    )


def test_plan_is_prospective_content_addressed_and_deterministic():
    m = manifest()
    first = plan(m, seed=7)
    same = plan(m, seed=7)
    changed_seed = plan(m, seed=8)
    changed_tolerance = plan(m, high_tolerance=0.75)

    assert first == same
    assert first.plan_id.startswith(
        "impact-calibration-load-cluster-transfer-plan:"
    )
    assert first.schema_version == (
        "argus-impact-calibration-load-cluster-transfer-plan-v1"
    )
    assert first.cluster_field == "source_run_id"
    assert first.execution_authorized is False
    assert first.production_decision_authorized is False
    assert changed_seed.plan_id != first.plan_id
    assert changed_tolerance.plan_id != first.plan_id


def test_plan_requires_both_evidence_kinds_and_pre_registration():
    broker_only = manifest(
        evidence_kinds=(ExecutionEvidenceKind.BROKER_CONFIRMED,)
    )

    with pytest.raises(ValueError, match="requires both"):
        plan(broker_only)

    m = manifest()
    with pytest.raises(ValueError, match="at or before"):
        create_prospective_load_cluster_transfer_plan(
            m,
            created_time_ns=111,
            load_bands=BANDS,
            metrics=("mean_slippage_error_ticks",),
            tolerances={
                ("low-load", "mean_slippage_error_ticks"): 1.0,
                ("high-load", "mean_slippage_error_ticks"): 1.0,
            },
            bootstrap_replicates=200,
            min_clusters_per_kind_per_band=2,
            min_metric_observations_per_kind_per_band=2,
        )


def test_plan_requires_exhaustive_contiguous_load_bands():
    m = manifest()
    kwargs = dict(
        created_time_ns=95,
        metrics=("mean_slippage_error_ticks",),
        bootstrap_replicates=200,
        min_clusters_per_kind_per_band=2,
        min_metric_observations_per_kind_per_band=2,
    )

    with pytest.raises(ValueError, match="begin at ratio 0.0"):
        create_prospective_load_cluster_transfer_plan(
            m,
            load_bands=(("x", 0.1, None),),
            tolerances={("x", "mean_slippage_error_ticks"): 1.0},
            **kwargs,
        )

    with pytest.raises(ValueError, match="contiguous"):
        create_prospective_load_cluster_transfer_plan(
            m,
            load_bands=(("a", 0.0, 0.2), ("b", 0.3, None)),
            tolerances={
                ("a", "mean_slippage_error_ticks"): 1.0,
                ("b", "mean_slippage_error_ticks"): 1.0,
            },
            **kwargs,
        )


def test_load_cluster_transfer_detects_high_load_paper_optimism():
    m, c = study()
    p = plan(m)

    result = registered_load_cluster_transfer_compatibility(
        p,
        m,
        c,
    )
    rows = {
        (row.band_label, row.metric): row
        for row in result.results
    }

    low = rows[("low-load", "mean_slippage_error_ticks")]
    high = rows[("high-load", "mean_slippage_error_ticks")]

    assert low.broker_cluster_count == 2
    assert low.paper_cluster_count == 2
    assert low.broker_observation_count == 2
    assert low.paper_observation_count == 2
    assert low.broker_estimate == pytest.approx(0.25)
    assert low.paper_estimate == pytest.approx(0.30)
    assert low.paper_minus_broker == pytest.approx(0.05)
    assert low.within_tolerance is True

    assert high.broker_cluster_count == 2
    assert high.paper_cluster_count == 2
    assert high.broker_estimate == pytest.approx(1.30)
    assert high.paper_estimate == pytest.approx(-0.05)
    assert high.paper_minus_broker == pytest.approx(-1.35)
    assert high.within_tolerance is False

    assert result.all_within_tolerance is False
    assert result.execution_authorized is False
    assert result.production_decision_authorized is False


def test_many_fills_in_one_run_do_not_satisfy_cluster_minimum():
    m = manifest()
    subjects = (
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-low-0",
            price=101.2,
            visible_size=50.0,
            sequence=30,
            run_id="b-low-only",
        ),
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-low-1",
            price=101.3,
            visible_size=50.0,
            sequence=31,
            run_id="b-low-only",
        ),
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-high-0",
            price=102.0,
            visible_size=10.0,
            sequence=32,
            run_id="b-high-a",
        ),
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-high-1",
            price=102.5,
            visible_size=10.0,
            sequence=33,
            run_id="b-high-b",
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-low-0",
            price=101.2,
            visible_size=50.0,
            sequence=40,
            run_id="p-low-only",
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-low-1",
            price=101.3,
            visible_size=50.0,
            sequence=41,
            run_id="p-low-only",
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-high-0",
            price=101.5,
            visible_size=10.0,
            sequence=42,
            run_id="p-high-a",
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-high-1",
            price=101.75,
            visible_size=10.0,
            sequence=43,
            run_id="p-high-b",
        ),
    )
    c = lock_impact_calibration_study_cohort(
        m,
        subjects,
        lock_time_ns=260,
    )

    with pytest.raises(
        ValueError,
        match="low-load mean_slippage_error_ticks.*clusters.*broker=1, paper=1",
    ):
        registered_load_cluster_transfer_compatibility(
            plan(m),
            m,
            c,
        )


def test_zero_fill_rows_do_not_create_slippage_clusters():
    m = manifest()
    subjects = (
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-low-fill",
            price=101.2,
            visible_size=50.0,
            sequence=50,
            run_id="b-low-a",
        ),
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-low-zero",
            price=101.0,
            visible_size=50.0,
            sequence=51,
            run_id="b-low-b",
            filled=0.0,
        ),
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-high-a",
            price=102.0,
            visible_size=10.0,
            sequence=52,
            run_id="b-high-a",
        ),
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-high-b",
            price=102.5,
            visible_size=10.0,
            sequence=53,
            run_id="b-high-b",
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-low-fill",
            price=101.2,
            visible_size=50.0,
            sequence=60,
            run_id="p-low-a",
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-low-zero",
            price=101.0,
            visible_size=50.0,
            sequence=61,
            run_id="p-low-b",
            filled=0.0,
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-high-a",
            price=101.5,
            visible_size=10.0,
            sequence=62,
            run_id="p-high-a",
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-high-b",
            price=101.75,
            visible_size=10.0,
            sequence=63,
            run_id="p-high-b",
        ),
    )
    c = lock_impact_calibration_study_cohort(
        m,
        subjects,
        lock_time_ns=260,
    )

    with pytest.raises(
        ValueError,
        match="low-load mean_slippage_error_ticks.*clusters.*broker=1, paper=1",
    ):
        registered_load_cluster_transfer_compatibility(
            plan(m),
            m,
            c,
        )


def test_fill_fraction_metric_can_use_zero_fill_clusters():
    m = manifest()
    subjects = (
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-low-fill",
            price=101.2,
            visible_size=50.0,
            sequence=70,
            run_id="b-low-a",
        ),
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-low-zero",
            price=101.0,
            visible_size=50.0,
            sequence=71,
            run_id="b-low-b",
            filled=0.0,
        ),
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-high-fill",
            price=102.0,
            visible_size=10.0,
            sequence=72,
            run_id="b-high-a",
        ),
        subject(
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            "b-high-zero",
            price=101.0,
            visible_size=10.0,
            sequence=73,
            run_id="b-high-b",
            filled=0.0,
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-low-fill",
            price=101.2,
            visible_size=50.0,
            sequence=80,
            run_id="p-low-a",
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-low-zero",
            price=101.0,
            visible_size=50.0,
            sequence=81,
            run_id="p-low-b",
            filled=0.0,
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-high-fill",
            price=102.0,
            visible_size=10.0,
            sequence=82,
            run_id="p-high-a",
        ),
        subject(
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
            "p-high-zero",
            price=101.0,
            visible_size=10.0,
            sequence=83,
            run_id="p-high-b",
            filled=0.0,
        ),
    )
    c = lock_impact_calibration_study_cohort(
        m,
        subjects,
        lock_time_ns=260,
    )
    p = plan(
        m,
        metric="mean_fill_fraction_error",
        low_tolerance=0.25,
        high_tolerance=0.25,
    )

    result = registered_load_cluster_transfer_compatibility(
        p,
        m,
        c,
    )

    assert len(result.results) == 2
    assert all(row.broker_cluster_count == 2 for row in result.results)
    assert all(row.paper_cluster_count == 2 for row in result.results)
    assert all(
        row.paper_minus_broker == pytest.approx(0.0)
        for row in result.results
    )
    assert result.all_within_tolerance is True


def test_same_plan_and_cohort_are_deterministic():
    m, c = study()
    p = plan(m, seed=123)

    first = registered_load_cluster_transfer_compatibility(
        p,
        m,
        c,
    )
    second = registered_load_cluster_transfer_compatibility(
        p,
        m,
        c,
    )

    assert first == second
    assert all(
        row.method
        == "deterministic_load_stratified_two_sample_cluster_percentile"
        for row in first.results
    )


def test_plan_and_cohort_tampering_fail_closed():
    m, c = study()
    p = plan(m)

    with pytest.raises(ValueError, match="plan_id"):
        registered_load_cluster_transfer_compatibility(
            replace(
                p,
                tolerances=(
                    ("low-load", "mean_slippage_error_ticks", 9.0),
                    ("high-load", "mean_slippage_error_ticks", 0.5),
                ),
            ),
            m,
            c,
        )

    with pytest.raises(ValueError, match="broker_confirmed_count"):
        registered_load_cluster_transfer_compatibility(
            p,
            m,
            replace(c, broker_confirmed_count=99),
        )

    with pytest.raises(ValueError, match="different manifest"):
        registered_load_cluster_transfer_compatibility(
            replace(p, manifest_id="wrong"),
            m,
            c,
        )


def test_authority_escalation_is_rejected():
    m, c = study()
    p = plan(m)

    with pytest.raises(ValueError, match="carries authority"):
        registered_load_cluster_transfer_compatibility(
            replace(p, execution_authorized=True),
            m,
            c,
        )
