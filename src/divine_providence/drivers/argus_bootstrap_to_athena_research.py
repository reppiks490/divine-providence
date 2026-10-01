"""Verified ARGUS bootstrap-uncertainty -> ATHENA research bridge.

The deterministic fixture uses ICARUS_PAPER_EMULATOR observations only. It
exercises pre-registered uncertainty transport without fabricating broker fills
or converting descriptive intervals into execution authority.
"""
from __future__ import annotations

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
from athena.contracts import DataPlane, Provenance
from athena.journal import AdvisoryEvent, AdvisoryJournal

from ._common import emit


ICARUS_SOURCE_COMMIT = "0b784fc8630f4f39bace2d22c6ccf3abb89132bd"


book = BookSnapshot(
    event_time_ns=100,
    sequence=7,
    bids=(
        BookLevel(99.0, 10.0),
        BookLevel(98.0, 20.0),
    ),
    asks=(
        BookLevel(101.0, 8.0),
        BookLevel(102.0, 20.0),
    ),
)

curve = depth_impact_curve(
    book,
    side=1,
    sizes=(5.0,),
    tick_size=1.0,
    capacity_threshold_ticks=(0.0, 1.0),
)


def paper_subject(execution_id: str, price: float) -> ImpactCalibrationStudySubject:
    receipt = create_execution_evidence_receipt(
        evidence_kind=ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
        source_system="icarus-paper-emulator",
        source_repo="reppiks490/Icarus",
        source_commit=ICARUS_SOURCE_COMMIT,
        source_run_id="divine-providence-bootstrap-fixture",
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
            "fixture": True,
            "kind": "paper_emulator_fill",
            "execution_id": execution_id,
            "qty": 5,
            "price": price,
        },
    )
    return ImpactCalibrationStudySubject(
        row=calibrate_lineaged_impact(curve, receipt),
        impact_model_revision="argus-depth-impact-v1",
        calibration_revision="argus-impact-calibration-v1",
    )


manifest = create_impact_calibration_study_manifest(
    study_name="argus-athena-bootstrap-uncertainty-fixture",
    created_time_ns=90,
    cohort_start_ns=110,
    cohort_end_ns=200,
    observation_cutoff_ns=250,
    impact_model_revision="argus-depth-impact-v1",
    calibration_revision="argus-impact-calibration-v1",
    symbols=("NQ",),
    evidence_kinds=(
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
    ),
    execution_source_revisions=(
        ("reppiks490/Icarus", ICARUS_SOURCE_COMMIT),
    ),
    min_observations_per_stratum=2,
    max_snapshot_age_ns=50,
    max_completion_latency_ns=50,
)

plan = create_prospective_bootstrap_plan(
    manifest,
    created_time_ns=95,
    confidence_alpha=0.05,
    bootstrap_replicates=200,
    bootstrap_seed=7,
    min_metric_observations=2,
    metrics=(
        "mean_slippage_error_ticks",
        "slippage_underprediction_rate",
    ),
)

cohort = lock_impact_calibration_study_cohort(
    manifest,
    (
        paper_subject("paper-1", 101.25),
        paper_subject("paper-2", 101.75),
    ),
    lock_time_ns=260,
)

packet = export_registered_bootstrap_uncertainty(
    plan,
    manifest,
    cohort,
    source_id="argus",
    representation_id="impact-calibration-bootstrap",
    publication_time_ns=270,
    ingestion_time_ns=280,
)

if packet["broker_confirmed_observations"] != 0:
    raise ValueError("fixture invented broker-confirmed execution evidence")
if packet["paper_emulator_observations"] != 2:
    raise ValueError("paper-emulator bootstrap evidence count changed")
if packet["simultaneous_coverage"]:
    raise ValueError("percentile intervals were mislabeled as simultaneous")
if packet["multiplicity_adjusted"]:
    raise ValueError("bootstrap intervals were mislabeled as multiplicity adjusted")
if packet["hypothesis_test"] or packet["causal_effect_estimate"]:
    raise ValueError("descriptive bootstrap was mislabeled as inferential/causal")
if (
    packet["execution_authorized"]
    or packet["production_authorized"]
    or packet["production_decision_authorized"]
    or not packet["advisory_only"]
):
    raise ValueError("bootstrap export authority boundary changed")

provenance = Provenance(
    event_time_ns=packet["event_time_ns"],
    ingestion_time_ns=packet["ingestion_time_ns"],
    source_id=packet["source_id"],
    representation_id=packet["representation_id"],
    version=packet["contract_version"],
    plane=DataPlane.RESEARCH,
    lineage_id=packet["lineage_id"],
    quality_flags=tuple(packet["quality_flags"]),
)

journal = AdvisoryJournal()
row = journal.append(
    AdvisoryEvent(
        provenance=provenance,
        kind=packet["kind"],
        available_ns=packet["available_ns"],
        payload=packet,
        sequence=1,
    )
)

if journal.asof(packet["available_ns"]):
    raise ValueError(
        "ATHENA exposed bootstrap uncertainty at publication time"
    )
if journal.asof(packet["ingestion_time_ns"] - 1):
    raise ValueError(
        "ATHENA exposed bootstrap uncertainty before local ingestion"
    )

frame = journal.frame(
    packet["ingestion_time_ns"],
    max_age_ns=1_000_000_000,
)
if frame["production_authorized"] or not frame["advisory_only"]:
    raise ValueError("ATHENA authority boundary changed")
if frame["abstain_required"]:
    raise ValueError(
        f"ATHENA rejected healthy bootstrap fixture: {frame}"
    )
if len(frame["evidence"]) != 1:
    raise ValueError(
        "ATHENA did not admit exactly one bootstrap research event"
    )

body = frame["evidence"][0]["body"]["payload"]
if body["bootstrap_plan_id"] != plan.plan_id:
    raise ValueError("ATHENA payload lost bootstrap plan identity")
if body["manifest_id"] != manifest.manifest_id:
    raise ValueError("ATHENA payload lost study manifest identity")
if body["cohort_id"] != cohort.cohort_id:
    raise ValueError("ATHENA payload lost cohort identity")
if body["broker_confirmed_observations"] != 0:
    raise ValueError("ATHENA payload strengthened paper evidence")
if not journal.verify()["verified"]:
    raise ValueError("ATHENA advisory journal failed verification")

emit(
    {
        "connection": "argus-bootstrap-athena-research",
        "ok": True,
        "contract_version": packet["contract_version"],
        "study_schema_version": manifest.schema_version,
        "bootstrap_plan_schema_version": plan.schema_version,
        "manifest_id": manifest.manifest_id,
        "cohort_id": cohort.cohort_id,
        "bootstrap_plan_id": plan.plan_id,
        "lineage_id": packet["lineage_id"],
        "argus": {
            "event_time_ns": packet["event_time_ns"],
            "study_lock_time_ns": packet["study_lock_time_ns"],
            "available_ns": packet["available_ns"],
            "confidence_level": packet["confidence_level"],
            "bootstrap_replicates": packet["bootstrap_replicates"],
            "broker_confirmed_observations": (
                packet["broker_confirmed_observations"]
            ),
            "paper_emulator_observations": (
                packet["paper_emulator_observations"]
            ),
            "paper_only_fixture": True,
            "simultaneous_coverage": packet["simultaneous_coverage"],
            "multiplicity_adjusted": packet["multiplicity_adjusted"],
            "hypothesis_test": packet["hypothesis_test"],
        },
        "athena": {
            "ingestion_time_ns": packet["ingestion_time_ns"],
            "event_id": row["event_id"],
            "frame_id": frame["frame_id"],
            "receipt_time_gated": True,
            "admitted_events": len(frame["evidence"]),
            "abstain_required": frame["abstain_required"],
        },
        "execution_authorized": False,
        "production_authorized": False,
        "production_decision_authorized": False,
    }
)
