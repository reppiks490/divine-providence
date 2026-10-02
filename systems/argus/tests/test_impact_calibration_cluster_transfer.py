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
from argus.impact_calibration_cluster_transfer import (
    create_prospective_cluster_transfer_plan,
    registered_cluster_transfer_compatibility,
)
from argus.impact_calibration_study import (
    ImpactCalibrationStudySubject,
    create_impact_calibration_study_manifest,
    lock_impact_calibration_study_cohort,
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
            source_payload={
                "fill_id": execution_id,
                "run_id": run_id,
                "filled": filled,
            },
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
        source_payload={
            "paper_fill": execution_id,
            "run_id": run_id,
            "filled": filled,
        },
    )


def subject(kind, execution_id, *, price, run_id, filled=5.0):
    return ImpactCalibrationStudySubject(
        row=calibrate_lineaged_impact(
            curve(),
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
        study_name="cluster-transfer",
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
    c = lock_impact_calibration_study_cohort(
        m,
        (
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-a-0",
                price=101.5,
                run_id="broker-session-a",
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-a-1",
                price=102.0,
                run_id="broker-session-a",
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-b-0",
                price=102.5,
                run_id="broker-session-b",
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-b-1",
                price=103.0,
                run_id="broker-session-b",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-a-0",
                price=101.1,
                run_id="paper-session-a",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-a-1",
                price=101.2,
                run_id="paper-session-a",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-b-0",
                price=101.3,
                run_id="paper-session-b",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-b-1",
                price=101.4,
                run_id="paper-session-b",
            ),
        ),
        lock_time_ns=260,
    )
    return m, c


def plan(
    m,
    *,
    metric="mean_slippage_error_ticks",
    tolerance=0.5,
    seed=7,
):
    return create_prospective_cluster_transfer_plan(
        m,
        created_time_ns=95,
        metrics=(metric,),
        tolerances={metric: tolerance},
        confidence_alpha=0.05,
        bootstrap_replicates=400,
        bootstrap_seed=seed,
        min_clusters_per_kind=2,
        min_metric_observations_per_kind=2,
    )


def test_cluster_plan_is_prospective_content_addressed_and_deterministic():
    m = manifest()
    first = plan(m, seed=7)
    same = plan(m, seed=7)
    changed_seed = plan(m, seed=8)
    changed_tolerance = plan(m, tolerance=1.0)

    assert first == same
    assert first.plan_id.startswith(
        "impact-calibration-cluster-transfer-plan:"
    )
    assert first.schema_version == (
        "argus-impact-calibration-cluster-transfer-plan-v1"
    )
    assert first.cluster_field == "source_run_id"
    assert first.execution_authorized is False
    assert first.production_decision_authorized is False
    assert changed_seed.plan_id != first.plan_id
    assert changed_tolerance.plan_id != first.plan_id


def test_cluster_plan_requires_both_evidence_kinds_and_pre_registration():
    broker_only = manifest(
        evidence_kinds=(ExecutionEvidenceKind.BROKER_CONFIRMED,)
    )
    with pytest.raises(ValueError, match="requires both"):
        plan(broker_only)

    m = manifest()
    with pytest.raises(ValueError, match="cannot predate manifest"):
        create_prospective_cluster_transfer_plan(
            m,
            created_time_ns=89,
            metrics=("mean_slippage_error_ticks",),
            tolerances={"mean_slippage_error_ticks": 0.5},
            bootstrap_replicates=200,
        )

    with pytest.raises(ValueError, match="at or before cohort_start"):
        create_prospective_cluster_transfer_plan(
            m,
            created_time_ns=111,
            metrics=("mean_slippage_error_ticks",),
            tolerances={"mean_slippage_error_ticks": 0.5},
            bootstrap_replicates=200,
        )

    with pytest.raises(ValueError, match="min_clusters_per_kind"):
        create_prospective_cluster_transfer_plan(
            m,
            created_time_ns=95,
            metrics=("mean_slippage_error_ticks",),
            tolerances={"mean_slippage_error_ticks": 0.5},
            bootstrap_replicates=200,
            min_clusters_per_kind=1,
        )


def test_cluster_transfer_detects_paper_optimism_and_preserves_clusters():
    m, c = study()
    p = plan(m, tolerance=0.5)

    result = registered_cluster_transfer_compatibility(p, m, c)
    row = result.results[0]

    assert row.metric == "mean_slippage_error_ticks"
    assert row.cluster_field == "source_run_id"
    assert row.broker_cluster_count == 2
    assert row.paper_cluster_count == 2
    assert row.broker_observation_count == 4
    assert row.paper_observation_count == 4
    assert row.broker_estimate == pytest.approx(1.25)
    assert row.paper_estimate == pytest.approx(0.25)
    assert row.paper_minus_broker == pytest.approx(-1.0)
    assert row.lower <= row.paper_minus_broker <= row.upper
    assert row.within_tolerance is False
    assert result.all_within_tolerance is False
    assert result.execution_authorized is False
    assert result.production_decision_authorized is False


def test_cluster_transfer_is_deterministic_for_same_plan_and_cohort():
    m, c = study()
    p = plan(m, tolerance=2.0, seed=123)

    first = registered_cluster_transfer_compatibility(p, m, c)
    second = registered_cluster_transfer_compatibility(p, m, c)

    assert first == second
    assert first.results[0].method == (
        "deterministic_two_sample_cluster_percentile"
    )
    assert first.results[0].bootstrap_replicates == 400


def test_cluster_minimum_prevents_pseudoreplication_from_one_run():
    m = manifest()
    c = lock_impact_calibration_study_cohort(
        m,
        (
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b0",
                price=101.5,
                run_id="one-broker-run",
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b1",
                price=102.0,
                run_id="one-broker-run",
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b2",
                price=102.5,
                run_id="one-broker-run",
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b3",
                price=103.0,
                run_id="one-broker-run",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p0",
                price=101.1,
                run_id="one-paper-run",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p1",
                price=101.2,
                run_id="one-paper-run",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p2",
                price=101.3,
                run_id="one-paper-run",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p3",
                price=101.4,
                run_id="one-paper-run",
            ),
        ),
        lock_time_ns=260,
    )
    p = plan(m)

    with pytest.raises(
        ValueError,
        match="eligible source_run_id clusters.*broker=1, paper=1",
    ):
        registered_cluster_transfer_compatibility(p, m, c)


def test_zero_fill_clusters_do_not_create_slippage_observations():
    m = manifest()
    c = lock_impact_calibration_study_cohort(
        m,
        (
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-a-fill",
                price=101.5,
                run_id="b-a",
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-a-zero",
                price=101.0,
                run_id="b-a",
                filled=0.0,
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-b-zero-0",
                price=101.0,
                run_id="b-b",
                filled=0.0,
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-b-zero-1",
                price=101.0,
                run_id="b-b",
                filled=0.0,
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-a-fill",
                price=101.2,
                run_id="p-a",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-a-zero",
                price=101.0,
                run_id="p-a",
                filled=0.0,
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-b-zero-0",
                price=101.0,
                run_id="p-b",
                filled=0.0,
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-b-zero-1",
                price=101.0,
                run_id="p-b",
                filled=0.0,
            ),
        ),
        lock_time_ns=260,
    )
    p = plan(m)

    with pytest.raises(
        ValueError,
        match="eligible source_run_id clusters.*broker=1, paper=1",
    ):
        registered_cluster_transfer_compatibility(p, m, c)


def test_fill_fraction_cluster_transfer_can_use_zero_fill_rows():
    m = manifest()
    c = lock_impact_calibration_study_cohort(
        m,
        (
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-a-fill",
                price=101.5,
                run_id="b-a",
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-a-zero",
                price=101.0,
                run_id="b-a",
                filled=0.0,
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-b-fill",
                price=101.5,
                run_id="b-b",
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-b-zero",
                price=101.0,
                run_id="b-b",
                filled=0.0,
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-a-fill",
                price=101.5,
                run_id="p-a",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-a-zero",
                price=101.0,
                run_id="p-a",
                filled=0.0,
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-b-fill",
                price=101.5,
                run_id="p-b",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-b-zero",
                price=101.0,
                run_id="p-b",
                filled=0.0,
            ),
        ),
        lock_time_ns=260,
    )
    p = plan(
        m,
        metric="mean_fill_fraction_error",
        tolerance=0.25,
    )

    result = registered_cluster_transfer_compatibility(p, m, c)
    row = result.results[0]

    assert row.broker_cluster_count == 2
    assert row.paper_cluster_count == 2
    assert row.broker_observation_count == 4
    assert row.paper_observation_count == 4
    assert row.paper_minus_broker == pytest.approx(0.0)
    assert row.within_tolerance is True
    assert result.all_within_tolerance is True


def test_source_run_id_collision_across_source_lineage_fails_closed():
    other_commit = "3" * 40
    m = create_impact_calibration_study_manifest(
        study_name="cluster-source-lineage-collision",
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
            ("broker/other-adapter", other_commit),
            ("reppiks490/Icarus", ICARUS_COMMIT),
        ),
        min_observations_per_stratum=2,
        max_snapshot_age_ns=50,
        max_completion_latency_ns=50,
    )

    def broker_subject(execution_id, repo, commit, run_id):
        receipt_value = create_execution_evidence_receipt(
            evidence_kind=ExecutionEvidenceKind.BROKER_CONFIRMED,
            source_system="example-broker",
            source_repo=repo,
            source_commit=commit,
            source_run_id=run_id,
            source_execution_id=execution_id,
            symbol="NQ",
            decision_time_ns=120,
            completion_time_ns=130,
            observed_time_ns=140,
            side=1,
            requested_size=5.0,
            filled_size=5.0,
            average_price=101.5,
            source_payload={"fill_id": execution_id, "run_id": run_id},
            broker_name="Example Broker",
            broker_order_id=f"order-{execution_id}",
            broker_fill_id=execution_id,
        )
        return ImpactCalibrationStudySubject(
            row=calibrate_lineaged_impact(curve(), receipt_value),
            impact_model_revision="impact-v1",
            calibration_revision="calibration-v1",
        )

    c = lock_impact_calibration_study_cohort(
        m,
        (
            broker_subject(
                "b-a",
                "broker/example-adapter",
                BROKER_COMMIT,
                "reused-run",
            ),
            broker_subject(
                "b-b",
                "broker/other-adapter",
                other_commit,
                "reused-run",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-a",
                price=101.2,
                run_id="paper-a",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-b",
                price=101.3,
                run_id="paper-b",
            ),
        ),
        lock_time_ns=260,
    )
    p = create_prospective_cluster_transfer_plan(
        m,
        created_time_ns=95,
        metrics=("mean_slippage_error_ticks",),
        tolerances={"mean_slippage_error_ticks": 1.0},
        confidence_alpha=0.05,
        bootstrap_replicates=200,
        bootstrap_seed=7,
        min_clusters_per_kind=2,
        min_metric_observations_per_kind=2,
    )

    with pytest.raises(
        ValueError,
        match="source_run_id collision across execution-source lineage",
    ):
        registered_cluster_transfer_compatibility(p, m, c)


def test_cluster_plan_and_cohort_tampering_fail_closed():
    m, c = study()
    p = plan(m)

    with pytest.raises(ValueError, match="plan_id"):
        registered_cluster_transfer_compatibility(
            replace(
                p,
                tolerances=(("mean_slippage_error_ticks", 9.0),),
            ),
            m,
            c,
        )

    with pytest.raises(ValueError, match="broker_confirmed_count"):
        registered_cluster_transfer_compatibility(
            p,
            m,
            replace(c, broker_confirmed_count=99),
        )

    with pytest.raises(ValueError, match="different manifest"):
        registered_cluster_transfer_compatibility(
            replace(p, manifest_id="wrong"),
            m,
            c,
        )


def test_cluster_plan_authority_escalation_is_rejected():
    m, c = study()
    p = plan(m)

    with pytest.raises(ValueError, match="carries authority"):
        registered_cluster_transfer_compatibility(
            replace(p, execution_authorized=True),
            m,
            c,
        )
