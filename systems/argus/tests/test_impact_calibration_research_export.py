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
from argus.impact_calibration_research_export import (
    export_registered_impact_calibration_study,
)
from argus.impact_calibration_study import (
    ImpactCalibrationStudySubject,
    create_impact_calibration_study_manifest,
    lock_impact_calibration_study_cohort,
)


BROKER_COMMIT = "2" * 40
ICARUS_COMMIT = "1" * 40


def _curve():
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


def _receipt(kind, execution_id, *, price):
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
        source_run_id="paper-session",
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


def _subject(kind, execution_id, *, price):
    return ImpactCalibrationStudySubject(
        row=calibrate_lineaged_impact(
            _curve(),
            _receipt(kind, execution_id, price=price),
        ),
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
    )


def _study():
    manifest = create_impact_calibration_study_manifest(
        study_name="export-study",
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
        min_observations_per_stratum=1,
        max_snapshot_age_ns=50,
        max_completion_latency_ns=50,
    )
    cohort = lock_impact_calibration_study_cohort(
        manifest,
        (
            _subject(
                ExecutionEvidenceKind.BROKER_CONFIRMED,
                "broker-1",
                price=101.5,
            ),
            _subject(
                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                "paper-1",
                price=101.25,
            ),
        ),
        lock_time_ns=260,
    )
    return manifest, cohort


def test_export_preserves_prospective_identity_and_evidence_strata():
    manifest, cohort = _study()

    packet = export_registered_impact_calibration_study(
        manifest,
        cohort,
        source_id="argus",
        representation_id="impact-calibration-study",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )

    assert packet["contract_version"] == (
        "argus-impact-calibration-research-v1"
    )
    assert packet["kind"] == "argus_impact_calibration_study"
    assert packet["plane"] == "research"
    assert packet["event_time_ns"] == 250
    assert packet["study_lock_time_ns"] == 260
    assert packet["available_ns"] == 270
    assert packet["ingestion_time_ns"] == 280
    assert packet["manifest_id"] == manifest.manifest_id
    assert packet["cohort_id"] == cohort.cohort_id
    assert packet["broker_confirmed_observations"] == 1
    assert packet["paper_emulator_observations"] == 1
    assert [
        row["evidence_kind"]
        for row in packet["evidence_strata"]
    ] == [
        "BROKER_CONFIRMED",
        "ICARUS_PAPER_EMULATOR",
    ]
    assert packet["evidence_strata"][0]["broker_confirmed"] is True
    assert packet["evidence_strata"][1]["broker_confirmed"] is False
    assert "contains_broker_confirmed_evidence" in packet["quality_flags"]
    assert "contains_paper_emulator_evidence" in packet["quality_flags"]
    assert packet["advisory_only"] is True
    assert packet["execution_authorized"] is False
    assert packet["production_authorized"] is False
    assert packet["production_decision_authorized"] is False


def test_export_cannot_publish_before_cohort_lock_or_ingest_before_publication():
    manifest, cohort = _study()

    with pytest.raises(ValueError, match="cohort lock_time_ns"):
        export_registered_impact_calibration_study(
            manifest,
            cohort,
            source_id="argus",
            representation_id="impact-calibration-study",
            publication_time_ns=259,
            ingestion_time_ns=280,
        )

    with pytest.raises(ValueError, match="ingestion_time_ns"):
        export_registered_impact_calibration_study(
            manifest,
            cohort,
            source_id="argus",
            representation_id="impact-calibration-study",
            publication_time_ns=270,
            ingestion_time_ns=269,
        )


def test_export_lineage_is_deterministic_and_representation_sensitive():
    manifest, cohort = _study()

    first = export_registered_impact_calibration_study(
        manifest,
        cohort,
        source_id="argus",
        representation_id="impact-calibration-study",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )
    same = export_registered_impact_calibration_study(
        manifest,
        cohort,
        source_id="argus",
        representation_id="impact-calibration-study",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )
    changed = export_registered_impact_calibration_study(
        manifest,
        cohort,
        source_id="argus",
        representation_id="impact-calibration-study-v2",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )

    assert first == same
    assert first["lineage_id"].startswith("argus-impact-research:")
    assert first["lineage_id"] != changed["lineage_id"]


def test_export_revalidates_cohort_before_crossing_boundary():
    manifest, cohort = _study()
    tampered = replace(cohort, broker_confirmed_count=99)

    with pytest.raises(ValueError, match="broker_confirmed_count"):
        export_registered_impact_calibration_study(
            manifest,
            tampered,
            source_id="argus",
            representation_id="impact-calibration-study",
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
def test_export_identity_and_clock_inputs_fail_closed(field, value, error):
    manifest, cohort = _study()
    kwargs = dict(
        source_id="argus",
        representation_id="impact-calibration-study",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )
    kwargs[field] = value

    with pytest.raises((TypeError, ValueError), match=error):
        export_registered_impact_calibration_study(
            manifest,
            cohort,
            **kwargs,
        )
