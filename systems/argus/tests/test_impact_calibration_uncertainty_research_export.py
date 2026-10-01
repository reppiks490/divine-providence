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
from argus.impact_calibration_uncertainty import (
    create_prospective_bootstrap_plan,
)
from argus.impact_calibration_uncertainty_research_export import (
    export_registered_bootstrap_uncertainty,
)


BROKER_COMMIT = "2" * 40


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


def _subject(execution_id, price):
    receipt = create_execution_evidence_receipt(
        evidence_kind=ExecutionEvidenceKind.BROKER_CONFIRMED,
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
        source_payload={"fill_id": execution_id, "price": price},
        broker_name="Example Broker",
        broker_order_id=f"order-{execution_id}",
        broker_fill_id=execution_id,
    )
    return ImpactCalibrationStudySubject(
        row=calibrate_lineaged_impact(_curve(), receipt),
        impact_model_revision="impact-v1",
        calibration_revision="calibration-v1",
    )


def _fixture():
    manifest = create_impact_calibration_study_manifest(
        study_name="bootstrap-export-study",
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
        min_observations_per_stratum=3,
        max_snapshot_age_ns=50,
        max_completion_latency_ns=50,
    )
    cohort = lock_impact_calibration_study_cohort(
        manifest,
        (
            _subject("b0", 101.0),
            _subject("b1", 102.0),
            _subject("b2", 103.0),
        ),
        lock_time_ns=260,
    )
    plan = create_prospective_bootstrap_plan(
        manifest,
        created_time_ns=95,
        bootstrap_replicates=200,
        bootstrap_seed=42,
        min_metric_observations=2,
        metrics=(
            "mean_slippage_error_ticks",
            "slippage_underprediction_rate",
        ),
    )
    return manifest, cohort, plan


def test_export_preserves_plan_and_interval_semantics():
    manifest, cohort, plan = _fixture()

    packet = export_registered_bootstrap_uncertainty(
        plan,
        manifest,
        cohort,
        source_id="argus",
        representation_id="impact-calibration-bootstrap",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )

    assert packet["contract_version"] == (
        "argus-impact-calibration-uncertainty-research-v1"
    )
    assert packet["kind"] == (
        "argus_impact_calibration_bootstrap_uncertainty"
    )
    assert packet["plane"] == "research"
    assert packet["event_time_ns"] == 250
    assert packet["study_lock_time_ns"] == 260
    assert packet["available_ns"] == 270
    assert packet["ingestion_time_ns"] == 280
    assert packet["manifest_id"] == manifest.manifest_id
    assert packet["cohort_id"] == cohort.cohort_id
    assert packet["bootstrap_plan_id"] == plan.plan_id
    assert packet["confidence_alpha"] == pytest.approx(0.05)
    assert packet["confidence_level"] == pytest.approx(0.95)
    assert packet["bootstrap_replicates"] == 200
    assert packet["bootstrap_seed"] == 42
    assert packet["broker_confirmed_observations"] == 3
    assert packet["paper_emulator_observations"] == 0
    assert packet["interval_method"] == (
        "deterministic_nonparametric_percentile"
    )
    assert packet["simultaneous_coverage"] is False
    assert packet["multiplicity_adjusted"] is False
    assert packet["hypothesis_test"] is False
    assert packet["causal_effect_estimate"] is False
    assert packet["advisory_only"] is True
    assert packet["execution_authorized"] is False
    assert packet["production_authorized"] is False
    assert packet["production_decision_authorized"] is False

    assert len(packet["evidence_strata"]) == 1
    stratum = packet["evidence_strata"][0]
    assert stratum["evidence_kind"] == "BROKER_CONFIRMED"
    assert stratum["broker_confirmed"] is True
    assert stratum["observations"] == 3
    assert {row["metric"] for row in stratum["intervals"]} == {
        "mean_slippage_error_ticks",
        "slippage_underprediction_rate",
    }


def test_export_cannot_publish_before_lock_or_ingest_before_publication():
    manifest, cohort, plan = _fixture()

    with pytest.raises(ValueError, match="cohort lock_time_ns"):
        export_registered_bootstrap_uncertainty(
            plan,
            manifest,
            cohort,
            source_id="argus",
            representation_id="impact-calibration-bootstrap",
            publication_time_ns=259,
            ingestion_time_ns=280,
        )

    with pytest.raises(ValueError, match="ingestion_time_ns"):
        export_registered_bootstrap_uncertainty(
            plan,
            manifest,
            cohort,
            source_id="argus",
            representation_id="impact-calibration-bootstrap",
            publication_time_ns=270,
            ingestion_time_ns=269,
        )


def test_export_lineage_is_deterministic_and_plan_sensitive():
    manifest, cohort, plan = _fixture()

    first = export_registered_bootstrap_uncertainty(
        plan,
        manifest,
        cohort,
        source_id="argus",
        representation_id="impact-calibration-bootstrap",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )
    same = export_registered_bootstrap_uncertainty(
        plan,
        manifest,
        cohort,
        source_id="argus",
        representation_id="impact-calibration-bootstrap",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )
    changed_representation = export_registered_bootstrap_uncertainty(
        plan,
        manifest,
        cohort,
        source_id="argus",
        representation_id="impact-calibration-bootstrap-v2",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )

    assert first == same
    assert first["lineage_id"].startswith(
        "argus-impact-uncertainty-research:"
    )
    assert first["lineage_id"] != changed_representation["lineage_id"]


def test_export_revalidates_plan_and_cohort_before_boundary():
    manifest, cohort, plan = _fixture()

    with pytest.raises(ValueError, match="plan_id"):
        export_registered_bootstrap_uncertainty(
            replace(plan, bootstrap_seed=99),
            manifest,
            cohort,
            source_id="argus",
            representation_id="impact-calibration-bootstrap",
            publication_time_ns=270,
            ingestion_time_ns=280,
        )

    with pytest.raises(ValueError, match="broker_confirmed_count"):
        export_registered_bootstrap_uncertainty(
            plan,
            manifest,
            replace(cohort, broker_confirmed_count=99),
            source_id="argus",
            representation_id="impact-calibration-bootstrap",
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
    manifest, cohort, plan = _fixture()
    kwargs = dict(
        source_id="argus",
        representation_id="impact-calibration-bootstrap",
        publication_time_ns=270,
        ingestion_time_ns=280,
    )
    kwargs[field] = value

    with pytest.raises((TypeError, ValueError), match=error):
        export_registered_bootstrap_uncertainty(
            plan,
            manifest,
            cohort,
            **kwargs,
        )
