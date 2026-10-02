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
)
from argus.impact_calibration_overlap import (
    create_prospective_overlap_plan,
)
from argus.impact_calibration_overlap_research_export import (
    export_registered_overlap_audit,
)
from argus.impact_calibration_study import (
    ImpactCalibrationStudySubject,
    create_impact_calibration_study_manifest,
    lock_impact_calibration_study_cohort,
)


BROKER_COMMIT = "2" * 40
ICARUS_COMMIT = "1" * 40

LOAD_BANDS = (
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
    run_id,
    decision,
    completion,
):
    kwargs = dict(
        evidence_kind=kind,
        source_system=(
            "synthetic-contract-fixture-broker"
            if kind is ExecutionEvidenceKind.BROKER_CONFIRMED
            else "icarus-paper-emulator"
        ),
        source_repo=(
            "broker/example-adapter"
            if kind is ExecutionEvidenceKind.BROKER_CONFIRMED
            else "reppiks490/Icarus"
        ),
        source_commit=(
            BROKER_COMMIT
            if kind is ExecutionEvidenceKind.BROKER_CONFIRMED
            else ICARUS_COMMIT
        ),
        source_run_id=run_id,
        source_execution_id=execution_id,
        symbol="NQ",
        decision_time_ns=decision,
        completion_time_ns=completion,
        observed_time_ns=completion + 1,
        side=1,
        requested_size=5.0,
        filled_size=5.0,
        average_price=101.5,
        source_payload={
            "synthetic_contract_fixture": True,
            "execution_id": execution_id,
            "run_id": run_id,
        },
    )
    if kind is ExecutionEvidenceKind.BROKER_CONFIRMED:
        kwargs.update(
            broker_name="Synthetic Contract Fixture Broker",
            broker_order_id=f"order-{execution_id}",
            broker_fill_id=execution_id,
        )
    return create_execution_evidence_receipt(**kwargs)


def subject(
    kind,
    execution_id,
    *,
    run_id,
    visible_size,
    sequence,
    decision,
    completion,
):
    return ImpactCalibrationStudySubject(
        row=calibrate_lineaged_impact(
            curve(
                visible_size=visible_size,
                sequence=sequence,
            ),
            receipt(
                kind,
                execution_id,
                run_id=run_id,
                decision=decision,
                completion=completion,
            ),
        ),
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
    )


def study():
    manifest = create_impact_calibration_study_manifest(
        study_name="overlap-export-contract-fixture",
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
        min_observations_per_stratum=8,
        max_snapshot_age_ns=100,
        max_completion_latency_ns=100,
    )

    rows = []
    sequence = 1

    low_times = (
        (120, 130),
        (120, 140),
        (130, 140),
        (130, 150),
    )
    for kind, prefix in (
        (ExecutionEvidenceKind.BROKER_CONFIRMED, "b"),
        (ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR, "p"),
    ):
        for i, (decision, completion) in enumerate(low_times):
            rows.append(
                subject(
                    kind,
                    f"{prefix}-low-{i}",
                    run_id=f"{prefix}-low-run-{i // 2}",
                    visible_size=50.0,
                    sequence=sequence,
                    decision=decision,
                    completion=completion,
                )
            )
            sequence += 1

    broker_high = (
        (120, 130),
        (120, 130),
        (130, 140),
        (130, 140),
    )
    paper_high = (
        (160, 200),
        (160, 200),
        (170, 220),
        (170, 220),
    )
    for i, (decision, completion) in enumerate(broker_high):
        rows.append(
            subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                f"b-high-{i}",
                run_id=f"b-high-run-{i // 2}",
                visible_size=10.0,
                sequence=sequence,
                decision=decision,
                completion=completion,
            )
        )
        sequence += 1

    for i, (decision, completion) in enumerate(paper_high):
        rows.append(
            subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                f"p-high-{i}",
                run_id=f"p-high-run-{i // 2}",
                visible_size=10.0,
                sequence=sequence,
                decision=decision,
                completion=completion,
            )
        )
        sequence += 1

    cohort = lock_impact_calibration_study_cohort(
        manifest,
        tuple(rows),
        lock_time_ns=260,
    )

    metric = "mean_fill_fraction_error"
    transfer = create_prospective_load_cluster_transfer_plan(
        manifest,
        created_time_ns=95,
        load_bands=LOAD_BANDS,
        metrics=(metric,),
        tolerances={
            ("low-load", metric): 1.0,
            ("high-load", metric): 1.0,
        },
        confidence_alpha=0.05,
        bootstrap_replicates=200,
        bootstrap_seed=7,
        min_clusters_per_kind_per_band=2,
        min_metric_observations_per_kind_per_band=2,
    )

    covariates = (
        "snapshot_age_ns",
        "completion_latency_ns",
    )
    overlap = create_prospective_overlap_plan(
        manifest,
        transfer,
        created_time_ns=95,
        covariates=covariates,
        covariate_bins={
            "snapshot_age_ns": (
                (0.0, 40.0),
                (40.0, None),
            ),
            "completion_latency_ns": (
                (0.0, 20.0),
                (20.0, None),
            ),
        },
        max_total_variation={
            (band, covariate): 0.25
            for band, _, _ in LOAD_BANDS
            for covariate in covariates
        },
        min_observations_per_kind_per_band=4,
    )
    return manifest, transfer, overlap, cohort


def export_packet():
    manifest, transfer, overlap, cohort = study()
    packet = export_registered_overlap_audit(
        overlap,
        manifest,
        transfer,
        cohort,
        source_id="argus",
        representation_id="impact-calibration-support-overlap",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )
    return manifest, transfer, overlap, cohort, packet


def test_overlap_export_preserves_identity_support_and_authority_boundaries():
    manifest, transfer, overlap, cohort, packet = export_packet()

    assert packet["contract_version"] == (
        "argus-impact-calibration-overlap-research-v1"
    )
    assert packet["kind"] == (
        "argus_impact_calibration_support_overlap"
    )
    assert packet["plane"] == "research"
    assert packet["event_time_ns"] == 250
    assert packet["study_lock_time_ns"] == 260
    assert packet["available_ns"] == 270
    assert packet["ingestion_time_ns"] == 280
    assert packet["manifest_id"] == manifest.manifest_id
    assert packet["cohort_id"] == cohort.cohort_id
    assert packet["load_cluster_transfer_plan_id"] == transfer.plan_id
    assert packet["overlap_plan_id"] == overlap.plan_id
    assert packet["support_metric"] == (
        "empirical_binned_total_variation"
    )

    assert packet["formal_equivalence_test"] is False
    assert packet["propensity_score"] is False
    assert packet["inverse_probability_weighting"] is False
    assert packet["causal_identification_claim"] is False
    assert packet["exchangeability_proven"] is False
    assert packet["hypothesis_test"] is False
    assert packet["multiplicity_adjusted"] is False
    assert packet["familywise_coverage"] is False
    assert packet["paper_evidence_promoted"] is False
    assert packet["broker_substitution_authorized"] is False
    assert packet["advisory_only"] is True
    assert packet["execution_authorized"] is False
    assert packet["production_authorized"] is False
    assert packet["production_decision_authorized"] is False

    rows = {
        (row["band_label"], row["covariate"]): row
        for row in packet["overlap_results"]
    }
    assert rows[
        ("low-load", "snapshot_age_ns")
    ]["total_variation_distance"] == pytest.approx(0.0)
    assert rows[
        ("high-load", "snapshot_age_ns")
    ]["total_variation_distance"] == pytest.approx(1.0)
    assert rows[
        ("high-load", "completion_latency_ns")
    ]["support_adequate"] is False
    assert packet["all_support_adequate"] is False


def test_overlap_export_lineage_is_deterministic_and_representation_sensitive():
    manifest, transfer, overlap, cohort = study()
    kwargs = dict(
        source_id="argus",
        representation_id="impact-calibration-support-overlap",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )

    first = export_registered_overlap_audit(
        overlap,
        manifest,
        transfer,
        cohort,
        **kwargs,
    )
    same = export_registered_overlap_audit(
        overlap,
        manifest,
        transfer,
        cohort,
        **kwargs,
    )
    changed = export_registered_overlap_audit(
        overlap,
        manifest,
        transfer,
        cohort,
        source_id="argus",
        representation_id="impact-calibration-support-overlap-v2",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )

    assert first == same
    assert first["lineage_id"].startswith(
        "argus-impact-overlap-research:"
    )
    assert first["lineage_id"] != changed["lineage_id"]


def test_overlap_export_cannot_publish_before_lock_or_ingest_before_publication():
    manifest, transfer, overlap, cohort = study()

    with pytest.raises(ValueError, match="cohort lock_time_ns"):
        export_registered_overlap_audit(
            overlap,
            manifest,
            transfer,
            cohort,
            source_id="argus",
            representation_id="impact-calibration-support-overlap",
            publication_time_ns=259,
            ingestion_time_ns=280,
        )

    with pytest.raises(ValueError, match="ingestion_time_ns"):
        export_registered_overlap_audit(
            overlap,
            manifest,
            transfer,
            cohort,
            source_id="argus",
            representation_id="impact-calibration-support-overlap",
            publication_time_ns=270,
            ingestion_time_ns=269,
        )


def test_overlap_export_revalidates_plan_and_cohort():
    manifest, transfer, overlap, cohort = study()

    with pytest.raises(ValueError, match="plan_id"):
        export_registered_overlap_audit(
            replace(
                overlap,
                min_observations_per_kind_per_band=3,
            ),
            manifest,
            transfer,
            cohort,
            source_id="argus",
            representation_id="impact-calibration-support-overlap",
            publication_time_ns=270,
            ingestion_time_ns=280,
        )

    with pytest.raises(ValueError, match="broker_confirmed_count"):
        export_registered_overlap_audit(
            overlap,
            manifest,
            transfer,
            replace(cohort, broker_confirmed_count=99),
            source_id="argus",
            representation_id="impact-calibration-support-overlap",
            publication_time_ns=270,
            ingestion_time_ns=280,
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
def test_overlap_export_identity_and_clock_inputs_fail_closed(
    field,
    value,
    error,
):
    manifest, transfer, overlap, cohort = study()
    kwargs = dict(
        source_id="argus",
        representation_id="impact-calibration-support-overlap",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )
    kwargs[field] = value

    with pytest.raises((TypeError, ValueError), match=error):
        export_registered_overlap_audit(
            overlap,
            manifest,
            transfer,
            cohort,
            **kwargs,
        )
