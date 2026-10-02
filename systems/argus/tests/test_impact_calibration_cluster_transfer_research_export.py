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
)
from argus.impact_calibration_cluster_transfer_research_export import (
    export_registered_cluster_transfer,
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
                "run_id": run_id,
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
            "run_id": run_id,
        },
    )


def subject(kind, execution_id, *, price, run_id):
    return ImpactCalibrationStudySubject(
        row=calibrate_lineaged_impact(
            curve(),
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
        study_name="cluster-export-contract-fixture",
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
        min_observations_per_stratum=4,
        max_snapshot_age_ns=50,
        max_completion_latency_ns=50,
    )
    cohort = lock_impact_calibration_study_cohort(
        manifest,
        (
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-a-0",
                price=101.5,
                run_id="broker-a",
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-a-1",
                price=102.0,
                run_id="broker-a",
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-b-0",
                price=102.5,
                run_id="broker-b",
            ),
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "b-b-1",
                price=103.0,
                run_id="broker-b",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-a-0",
                price=101.1,
                run_id="paper-a",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-a-1",
                price=101.2,
                run_id="paper-a",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-b-0",
                price=101.3,
                run_id="paper-b",
            ),
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "p-b-1",
                price=101.4,
                run_id="paper-b",
            ),
        ),
        lock_time_ns=260,
    )
    metric = "mean_slippage_error_ticks"
    plan = create_prospective_cluster_transfer_plan(
        manifest,
        created_time_ns=95,
        metrics=(metric,),
        tolerances={metric: 0.5},
        confidence_alpha=0.05,
        bootstrap_replicates=200,
        bootstrap_seed=7,
        min_clusters_per_kind=2,
        min_metric_observations_per_kind=2,
    )
    return plan, manifest, cohort


def test_export_preserves_cluster_transfer_identity_and_boundaries():
    plan, manifest, cohort = study()

    packet = export_registered_cluster_transfer(
        plan,
        manifest,
        cohort,
        source_id="argus",
        representation_id="impact-calibration-cluster-transfer",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )

    assert packet["contract_version"] == (
        "argus-impact-calibration-cluster-transfer-research-v1"
    )
    assert packet["kind"] == (
        "argus_impact_calibration_cluster_transfer"
    )
    assert packet["plane"] == "research"
    assert packet["manifest_id"] == manifest.manifest_id
    assert packet["cohort_id"] == cohort.cohort_id
    assert packet["cluster_transfer_plan_id"] == plan.plan_id
    assert packet["cluster_field"] == "source_run_id"
    assert packet["event_time_ns"] == 250
    assert packet["study_lock_time_ns"] == 260
    assert packet["available_ns"] == 270
    assert packet["ingestion_time_ns"] == 280
    assert packet["comparison_direction"] == "paper_minus_broker"
    assert packet["interval_method"] == (
        "deterministic_two_sample_cluster_percentile"
    )
    assert packet["formal_equivalence_test"] is False
    assert packet["small_sample_cluster_guarantee"] is False
    assert packet["multiplicity_adjusted"] is False
    assert packet["familywise_coverage"] is False
    assert packet["causal_effect_estimate"] is False
    assert packet["paper_evidence_promoted"] is False
    assert packet["broker_substitution_authorized"] is False
    assert packet["advisory_only"] is True
    assert packet["execution_authorized"] is False
    assert packet["production_authorized"] is False
    assert packet["production_decision_authorized"] is False

    assert len(packet["cluster_transfer_results"]) == 1
    row = packet["cluster_transfer_results"][0]
    assert row["broker_cluster_count"] == 2
    assert row["paper_cluster_count"] == 2
    assert row["broker_observation_count"] == 4
    assert row["paper_observation_count"] == 4
    assert row["within_tolerance"] is False
    assert packet["all_within_tolerance"] is False


def test_export_lineage_is_deterministic_and_representation_sensitive():
    plan, manifest, cohort = study()

    first = export_registered_cluster_transfer(
        plan,
        manifest,
        cohort,
        source_id="argus",
        representation_id="impact-calibration-cluster-transfer",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )
    same = export_registered_cluster_transfer(
        plan,
        manifest,
        cohort,
        source_id="argus",
        representation_id="impact-calibration-cluster-transfer",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )
    changed = export_registered_cluster_transfer(
        plan,
        manifest,
        cohort,
        source_id="argus",
        representation_id="impact-calibration-cluster-transfer-v2",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )

    assert first == same
    assert first["lineage_id"].startswith(
        "argus-impact-cluster-transfer-research:"
    )
    assert first["lineage_id"] != changed["lineage_id"]


def test_export_revalidates_cluster_plan_and_cohort():
    plan, manifest, cohort = study()

    with pytest.raises(ValueError, match="plan_id"):
        export_registered_cluster_transfer(
            replace(
                plan,
                tolerances=(("mean_slippage_error_ticks", 9.0),),
            ),
            manifest,
            cohort,
            source_id="argus",
            representation_id="impact-calibration-cluster-transfer",
            publication_time_ns=270,
            ingestion_time_ns=280,
        )

    with pytest.raises(ValueError, match="broker_confirmed_count"):
        export_registered_cluster_transfer(
            plan,
            manifest,
            replace(cohort, broker_confirmed_count=99),
            source_id="argus",
            representation_id="impact-calibration-cluster-transfer",
            publication_time_ns=270,
            ingestion_time_ns=280,
        )


def test_export_clock_ordering_fails_closed():
    plan, manifest, cohort = study()

    with pytest.raises(ValueError, match="cohort lock_time_ns"):
        export_registered_cluster_transfer(
            plan,
            manifest,
            cohort,
            source_id="argus",
            representation_id="impact-calibration-cluster-transfer",
            publication_time_ns=259,
            ingestion_time_ns=280,
        )

    with pytest.raises(ValueError, match="ingestion_time_ns"):
        export_registered_cluster_transfer(
            plan,
            manifest,
            cohort,
            source_id="argus",
            representation_id="impact-calibration-cluster-transfer",
            publication_time_ns=270,
            ingestion_time_ns=269,
        )


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("source_id", "", "source_id"),
        ("source_id", " argus ", "source_id"),
        ("representation_id", "", "representation_id"),
        ("publication_time_ns", -1, "publication_time_ns"),
        ("ingestion_time_ns", -1, "ingestion_time_ns"),
    ],
)
def test_export_identity_and_clock_inputs_fail_closed(field, value, error):
    plan, manifest, cohort = study()
    kwargs = dict(
        source_id="argus",
        representation_id="impact-calibration-cluster-transfer",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )
    kwargs[field] = value

    with pytest.raises((TypeError, ValueError), match=error):
        export_registered_cluster_transfer(
            plan,
            manifest,
            cohort,
            **kwargs,
        )
