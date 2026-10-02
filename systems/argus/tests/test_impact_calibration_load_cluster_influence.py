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
from argus.impact_calibration_load_cluster_influence import (
    create_prospective_load_cluster_influence_plan,
    registered_load_cluster_influence_audit,
)
from argus.impact_calibration_load_cluster_transfer import (
    create_prospective_load_cluster_transfer_plan,
)
from argus.impact_calibration_study import (
    ImpactCalibrationStudySubject,
    create_impact_calibration_study_manifest,
    lock_impact_calibration_study_cohort,
)


BROKER_COMMIT = "2" * 40
ICARUS_COMMIT = "1" * 40
METRIC = "mean_slippage_error_ticks"
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


def receipt(kind, execution_id, *, price, run_id):
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
            filled_size=5.0,
            average_price=price,
            source_payload={"fill_id": execution_id},
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
        filled_size=5.0,
        average_price=price,
        source_payload={"paper_fill": execution_id},
    )


def subject(
    kind,
    execution_id,
    *,
    price,
    visible_size,
    sequence,
    run_id,
):
    return ImpactCalibrationStudySubject(
        row=calibrate_lineaged_impact(
            curve(visible_size=visible_size, sequence=sequence),
            receipt(
                kind,
                execution_id,
                price=price,
                run_id=run_id,
            ),
        ),
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
    )


def build_study(*, fragile_high=True, clusters_per_band=3):
    manifest = create_impact_calibration_study_manifest(
        study_name="load-cluster-influence",
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
        min_observations_per_stratum=clusters_per_band * 2,
        max_snapshot_age_ns=50,
        max_completion_latency_ns=50,
    )

    subjects = []
    seq = 10
    for index in range(clusters_per_band):
        subjects.append(
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                f"b-low-{index}",
                price=101.20 + index * 0.02,
                visible_size=50.0,
                sequence=seq,
                run_id=f"b-low-run-{index}",
            )
        )
        seq += 1
        subjects.append(
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                f"p-low-{index}",
                price=101.22 + index * 0.02,
                visible_size=50.0,
                sequence=seq,
                run_id=f"p-low-run-{index}",
            )
        )
        seq += 1

    for index in range(clusters_per_band):
        broker_price = 102.0
        if fragile_high and index == clusters_per_band - 1:
            broker_price = 105.0
        subjects.append(
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                f"b-high-{index}",
                price=broker_price,
                visible_size=10.0,
                sequence=seq,
                run_id=f"b-high-run-{index}",
            )
        )
        seq += 1
        subjects.append(
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                f"p-high-{index}",
                price=101.20,
                visible_size=10.0,
                sequence=seq,
                run_id=f"p-high-run-{index}",
            )
        )
        seq += 1

    cohort = lock_impact_calibration_study_cohort(
        manifest,
        tuple(subjects),
        lock_time_ns=260,
    )

    transfer_plan = create_prospective_load_cluster_transfer_plan(
        manifest,
        created_time_ns=95,
        load_bands=BANDS,
        metrics=(METRIC,),
        tolerances={
            ("low-load", METRIC): 3.0,
            ("high-load", METRIC): 5.0,
        },
        confidence_alpha=0.05,
        bootstrap_replicates=200,
        bootstrap_seed=7,
        min_clusters_per_kind_per_band=2,
        min_metric_observations_per_kind_per_band=2,
    )
    return manifest, cohort, transfer_plan


def influence_plan(
    manifest,
    transfer_plan,
    *,
    low_tolerance=0.25,
    high_tolerance=0.75,
    min_after=2,
):
    return create_prospective_load_cluster_influence_plan(
        manifest,
        transfer_plan,
        created_time_ns=96,
        min_clusters_after_drop_per_kind=min_after,
        max_abs_shift_tolerances={
            ("low-load", METRIC): low_tolerance,
            ("high-load", METRIC): high_tolerance,
        },
    )


def test_plan_is_prospective_content_addressed_and_deterministic():
    manifest, _, transfer_plan = build_study()
    first = influence_plan(manifest, transfer_plan)
    same = influence_plan(manifest, transfer_plan)
    changed = influence_plan(
        manifest,
        transfer_plan,
        high_tolerance=1.5,
    )

    assert first == same
    assert first.plan_id.startswith(
        "impact-calibration-load-cluster-influence-plan:"
    )
    assert first.schema_version == (
        "argus-impact-calibration-load-cluster-influence-plan-v1"
    )
    assert first.load_cluster_transfer_plan_id == transfer_plan.plan_id
    assert first.execution_authorized is False
    assert first.production_decision_authorized is False
    assert changed.plan_id != first.plan_id


def test_plan_must_be_registered_before_cohort_and_cover_every_cell():
    manifest, _, transfer_plan = build_study()

    with pytest.raises(ValueError, match="cannot predate manifest"):
        create_prospective_load_cluster_influence_plan(
            manifest,
            transfer_plan,
            created_time_ns=89,
            min_clusters_after_drop_per_kind=2,
            max_abs_shift_tolerances={
                ("low-load", METRIC): 0.25,
                ("high-load", METRIC): 0.75,
            },
        )

    with pytest.raises(ValueError, match="cannot predate load-cluster"):
        create_prospective_load_cluster_influence_plan(
            manifest,
            transfer_plan,
            created_time_ns=94,
            min_clusters_after_drop_per_kind=2,
            max_abs_shift_tolerances={
                ("low-load", METRIC): 0.25,
                ("high-load", METRIC): 0.75,
            },
        )

    with pytest.raises(ValueError, match="at or before cohort_start"):
        create_prospective_load_cluster_influence_plan(
            manifest,
            transfer_plan,
            created_time_ns=111,
            min_clusters_after_drop_per_kind=2,
            max_abs_shift_tolerances={
                ("low-load", METRIC): 0.25,
                ("high-load", METRIC): 0.75,
            },
        )

    with pytest.raises(ValueError, match="exactly one value"):
        create_prospective_load_cluster_influence_plan(
            manifest,
            transfer_plan,
            created_time_ns=96,
            min_clusters_after_drop_per_kind=2,
            max_abs_shift_tolerances={
                ("low-load", METRIC): 0.25,
            },
        )


def test_influence_audit_exposes_one_run_dominating_high_load_result():
    manifest, cohort, transfer_plan = build_study(
        fragile_high=True,
    )
    plan = influence_plan(
        manifest,
        transfer_plan,
        low_tolerance=0.25,
        high_tolerance=0.75,
    )

    audit = registered_load_cluster_influence_audit(
        plan,
        transfer_plan,
        manifest,
        cohort,
    )
    rows = {row.band_label: row for row in audit.results}

    low = rows["low-load"]
    high = rows["high-load"]

    assert low.broker_cluster_count == 3
    assert low.paper_cluster_count == 3
    assert low.leave_one_evaluations == 6
    assert low.stable_under_leave_one_cluster is True

    assert high.broker_cluster_count == 3
    assert high.paper_cluster_count == 3
    assert high.leave_one_evaluations == 6
    assert high.max_abs_leave_one_cluster_shift == pytest.approx(1.0)
    assert high.max_allowed_abs_shift == pytest.approx(0.75)
    assert high.worst_evidence_kind is (
        ExecutionEvidenceKind.BROKER_CONFIRMED
    )
    assert high.worst_source_run_id == "b-high-run-2"
    assert high.stable_under_leave_one_cluster is False

    assert audit.all_stable_under_leave_one_cluster is False
    assert audit.execution_authorized is False
    assert audit.production_decision_authorized is False


def test_balanced_clusters_are_stable_under_predeclared_shift_limit():
    manifest, cohort, transfer_plan = build_study(
        fragile_high=False,
    )
    plan = influence_plan(
        manifest,
        transfer_plan,
        low_tolerance=0.25,
        high_tolerance=0.25,
    )

    audit = registered_load_cluster_influence_audit(
        plan,
        transfer_plan,
        manifest,
        cohort,
    )

    assert all(
        row.stable_under_leave_one_cluster
        for row in audit.results
    )
    assert audit.all_stable_under_leave_one_cluster is True


def test_minimum_remaining_clusters_fails_closed():
    manifest, cohort, transfer_plan = build_study(
        fragile_high=False,
        clusters_per_band=2,
    )
    plan = influence_plan(
        manifest,
        transfer_plan,
        min_after=2,
    )

    with pytest.raises(
        ValueError,
        match="leaves fewer than 2 broker clusters",
    ):
        registered_load_cluster_influence_audit(
            plan,
            transfer_plan,
            manifest,
            cohort,
        )


def test_influence_plan_cannot_relax_parent_cluster_floor():
    manifest, _, transfer_plan = build_study(
        fragile_high=False,
        clusters_per_band=3,
    )
    transfer_plan = replace(
        transfer_plan,
        min_clusters_per_kind_per_band=3,
    )

    # Re-content-addressing is intentionally not available by mutation; build a
    # valid parent plan with the stricter floor instead.
    transfer_plan = create_prospective_load_cluster_transfer_plan(
        manifest,
        created_time_ns=95,
        load_bands=BANDS,
        metrics=(METRIC,),
        tolerances={
            ("low-load", METRIC): 3.0,
            ("high-load", METRIC): 5.0,
        },
        confidence_alpha=0.05,
        bootstrap_replicates=200,
        bootstrap_seed=7,
        min_clusters_per_kind_per_band=3,
        min_metric_observations_per_kind_per_band=2,
    )

    with pytest.raises(
        ValueError,
        match="cannot be below the parent.*min_clusters_per_kind_per_band",
    ):
        create_prospective_load_cluster_influence_plan(
            manifest,
            transfer_plan,
            created_time_ns=96,
            min_clusters_after_drop_per_kind=2,
            max_abs_shift_tolerances={
                ("low-load", METRIC): 0.25,
                ("high-load", METRIC): 0.75,
            },
        )


def test_leave_one_cluster_preserves_transfer_observation_floor():
    manifest, cohort, _ = build_study(
        fragile_high=False,
        clusters_per_band=3,
    )
    transfer_plan = create_prospective_load_cluster_transfer_plan(
        manifest,
        created_time_ns=95,
        load_bands=BANDS,
        metrics=(METRIC,),
        tolerances={
            ("low-load", METRIC): 3.0,
            ("high-load", METRIC): 5.0,
        },
        confidence_alpha=0.05,
        bootstrap_replicates=200,
        bootstrap_seed=7,
        min_clusters_per_kind_per_band=2,
        min_metric_observations_per_kind_per_band=3,
    )
    plan = influence_plan(
        manifest,
        transfer_plan,
        min_after=2,
    )

    with pytest.raises(
        ValueError,
        match="low-load mean_slippage_error_ticks leaves fewer than 3 "
        "broker observations after one-cluster deletion",
    ):
        registered_load_cluster_influence_audit(
            plan,
            transfer_plan,
            manifest,
            cohort,
        )


def test_plan_transfer_plan_and_cohort_tampering_fail_closed():
    manifest, cohort, transfer_plan = build_study()
    plan = influence_plan(manifest, transfer_plan)

    with pytest.raises(ValueError, match="plan_id"):
        registered_load_cluster_influence_audit(
            replace(
                plan,
                max_abs_shift_tolerances=(
                    ("low-load", METRIC, 9.0),
                    ("high-load", METRIC, 0.75),
                ),
            ),
            transfer_plan,
            manifest,
            cohort,
        )

    with pytest.raises(ValueError, match="different load-cluster"):
        registered_load_cluster_influence_audit(
            replace(
                plan,
                load_cluster_transfer_plan_id="wrong",
            ),
            transfer_plan,
            manifest,
            cohort,
        )

    with pytest.raises(ValueError, match="broker_confirmed_count"):
        registered_load_cluster_influence_audit(
            plan,
            transfer_plan,
            manifest,
            replace(cohort, broker_confirmed_count=99),
        )


def test_authority_escalation_is_rejected():
    manifest, cohort, transfer_plan = build_study()
    plan = influence_plan(manifest, transfer_plan)

    with pytest.raises(ValueError, match="carries authority"):
        registered_load_cluster_influence_audit(
            replace(plan, execution_authorized=True),
            transfer_plan,
            manifest,
            cohort,
        )
