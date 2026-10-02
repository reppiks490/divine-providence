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
)
from argus.impact_calibration_load_cluster_influence_research_export import (
    export_registered_load_cluster_influence,
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
            source_system="synthetic-contract-fixture-broker",
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
            source_payload={
                "synthetic_contract_fixture": True,
                "fill_id": execution_id,
            },
            broker_name="Synthetic Contract Fixture Broker",
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
        source_payload={
            "synthetic_contract_fixture": True,
            "paper_fill": execution_id,
        },
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


def study():
    manifest = create_impact_calibration_study_manifest(
        study_name="influence-export-fixture",
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
        min_observations_per_stratum=6,
        max_snapshot_age_ns=50,
        max_completion_latency_ns=50,
    )

    rows = []
    seq = 10
    for index in range(3):
        rows.append(
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                f"b-low-{index}",
                price=101.2 + index * 0.02,
                visible_size=50.0,
                sequence=seq,
                run_id=f"b-low-{index}",
            )
        )
        seq += 1
        rows.append(
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                f"p-low-{index}",
                price=101.22 + index * 0.02,
                visible_size=50.0,
                sequence=seq,
                run_id=f"p-low-{index}",
            )
        )
        seq += 1

    for index, broker_price in enumerate((102.0, 102.0, 105.0)):
        rows.append(
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                f"b-high-{index}",
                price=broker_price,
                visible_size=10.0,
                sequence=seq,
                run_id=f"b-high-{index}",
            )
        )
        seq += 1
        rows.append(
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                f"p-high-{index}",
                price=101.2,
                visible_size=10.0,
                sequence=seq,
                run_id=f"p-high-{index}",
            )
        )
        seq += 1

    cohort = lock_impact_calibration_study_cohort(
        manifest,
        tuple(rows),
        lock_time_ns=260,
    )

    transfer_plan = create_prospective_load_cluster_transfer_plan(
        manifest,
        created_time_ns=95,
        load_bands=(
            ("low-load", 0.0, 0.30),
            ("high-load", 0.30, None),
        ),
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

    influence_plan = create_prospective_load_cluster_influence_plan(
        manifest,
        transfer_plan,
        created_time_ns=96,
        min_clusters_after_drop_per_kind=2,
        max_abs_shift_tolerances={
            ("low-load", METRIC): 0.25,
            ("high-load", METRIC): 0.75,
        },
    )
    return influence_plan, transfer_plan, manifest, cohort


def test_export_preserves_identity_and_sensitivity_boundary():
    influence_plan, transfer_plan, manifest, cohort = study()

    packet = export_registered_load_cluster_influence(
        influence_plan,
        transfer_plan,
        manifest,
        cohort,
        source_id="argus",
        representation_id="load-cluster-influence",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )

    assert packet["contract_version"] == (
        "argus-impact-calibration-load-cluster-influence-research-v1"
    )
    assert packet["kind"] == (
        "argus_impact_calibration_load_cluster_influence"
    )
    assert packet["manifest_id"] == manifest.manifest_id
    assert packet["cohort_id"] == cohort.cohort_id
    assert packet["load_cluster_transfer_plan_id"] == transfer_plan.plan_id
    assert packet["influence_plan_id"] == influence_plan.plan_id
    assert packet["cluster_field"] == "source_run_id"
    assert packet["min_metric_observations_per_kind_per_band"] == 2
    assert packet["sensitivity_method"] == (
        "leave_one_source_run_cluster_out"
    )
    assert packet["formal_influence_theorem"] is False
    assert packet["jackknife_confidence_interval"] is False
    assert packet["hypothesis_test"] is False
    assert packet["multiplicity_adjusted"] is False
    assert packet["causal_effect_estimate"] is False
    assert packet["paper_evidence_promoted"] is False
    assert packet["broker_substitution_authorized"] is False
    assert packet["advisory_only"] is True
    assert packet["execution_authorized"] is False
    assert packet["production_authorized"] is False
    assert packet["production_decision_authorized"] is False
    assert packet["all_stable_under_leave_one_cluster"] is False

    rows = {
        row["band_label"]: row
        for row in packet["influence_results"]
    }
    assert rows["low-load"]["stable_under_leave_one_cluster"] is True
    assert rows["high-load"]["stable_under_leave_one_cluster"] is False
    assert rows["high-load"]["worst_evidence_kind"] == "BROKER_CONFIRMED"
    assert rows["high-load"]["worst_source_run_id"] == "b-high-2"


def test_export_lineage_is_deterministic_and_representation_sensitive():
    influence_plan, transfer_plan, manifest, cohort = study()

    first = export_registered_load_cluster_influence(
        influence_plan,
        transfer_plan,
        manifest,
        cohort,
        source_id="argus",
        representation_id="load-cluster-influence",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )
    same = export_registered_load_cluster_influence(
        influence_plan,
        transfer_plan,
        manifest,
        cohort,
        source_id="argus",
        representation_id="load-cluster-influence",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )
    changed = export_registered_load_cluster_influence(
        influence_plan,
        transfer_plan,
        manifest,
        cohort,
        source_id="argus",
        representation_id="load-cluster-influence-v2",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )

    assert first == same
    assert first["lineage_id"].startswith(
        "argus-impact-load-cluster-influence-research:"
    )
    assert first["lineage_id"] != changed["lineage_id"]


def test_export_clock_and_tamper_checks_fail_closed():
    influence_plan, transfer_plan, manifest, cohort = study()

    with pytest.raises(ValueError, match="cohort lock_time_ns"):
        export_registered_load_cluster_influence(
            influence_plan,
            transfer_plan,
            manifest,
            cohort,
            source_id="argus",
            representation_id="load-cluster-influence",
            publication_time_ns=259,
            ingestion_time_ns=280,
        )

    with pytest.raises(ValueError, match="ingestion_time_ns"):
        export_registered_load_cluster_influence(
            influence_plan,
            transfer_plan,
            manifest,
            cohort,
            source_id="argus",
            representation_id="load-cluster-influence",
            publication_time_ns=270,
            ingestion_time_ns=269,
        )

    with pytest.raises(ValueError, match="plan_id"):
        export_registered_load_cluster_influence(
            replace(
                influence_plan,
                max_abs_shift_tolerances=(
                    ("low-load", METRIC, 9.0),
                    ("high-load", METRIC, 0.75),
                ),
            ),
            transfer_plan,
            manifest,
            cohort,
            source_id="argus",
            representation_id="load-cluster-influence",
            publication_time_ns=270,
            ingestion_time_ns=280,
        )
