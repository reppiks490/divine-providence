"""Verified ARGUS prospective impact-calibration -> ATHENA research bridge.

The fixture deliberately uses ICARUS_PAPER_EMULATOR evidence only. It proves the
cross-system receipt-time path without fabricating a broker-confirmed fill.
Research/advisory only; no execution authority.
"""
from __future__ import annotations

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
from athena.contracts import DataPlane, Provenance
from athena.journal import AdvisoryEvent, AdvisoryJournal

from ._common import emit


ICARUS_SOURCE_COMMIT = "ce3c49ba18f0f9e89cefc2091fd2b1831bce8333"


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

receipt = create_execution_evidence_receipt(
    evidence_kind=ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
    source_system="icarus-paper-emulator",
    source_repo="reppiks490/Icarus",
    source_commit=ICARUS_SOURCE_COMMIT,
    source_run_id="divine-providence-research-fixture",
    source_execution_id="paper-fill-1",
    symbol="NQ",
    decision_time_ns=120,
    completion_time_ns=130,
    observed_time_ns=140,
    side=1,
    requested_size=5.0,
    filled_size=5.0,
    average_price=101.25,
    source_payload={
        "fixture": True,
        "kind": "paper_emulator_fill",
        "qty": 5,
        "price": 101.25,
    },
)

subject = ImpactCalibrationStudySubject(
    row=calibrate_lineaged_impact(curve, receipt),
    impact_model_revision="argus-depth-impact-v1",
    calibration_revision="argus-impact-calibration-v1",
)

manifest = create_impact_calibration_study_manifest(
    study_name="argus-athena-impact-calibration-fixture",
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
    min_observations_per_stratum=1,
    max_snapshot_age_ns=50,
    max_completion_latency_ns=50,
)

cohort = lock_impact_calibration_study_cohort(
    manifest,
    (subject,),
    lock_time_ns=260,
)

packet = export_registered_impact_calibration_study(
    manifest,
    cohort,
    source_id="argus",
    representation_id="impact-calibration-study",
    publication_time_ns=270,
    ingestion_time_ns=280,
)

if packet["broker_confirmed_observations"] != 0:
    raise ValueError("fixture invented broker-confirmed execution evidence")
if packet["paper_emulator_observations"] != 1:
    raise ValueError("paper-emulator evidence count changed")
if "contains_broker_confirmed_evidence" in packet["quality_flags"]:
    raise ValueError("paper-only fixture was mislabeled as broker-confirmed")
if "contains_paper_emulator_evidence" not in packet["quality_flags"]:
    raise ValueError("paper-emulator evidence quality flag missing")
if (
    packet["execution_authorized"]
    or packet["production_authorized"]
    or packet["production_decision_authorized"]
    or not packet["advisory_only"]
):
    raise ValueError("impact-calibration export authority boundary changed")

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

# Study publication is not local knowledge. ATHENA remains blind until receipt.
if journal.asof(packet["available_ns"]):
    raise ValueError(
        "ATHENA exposed impact-calibration study at publication time"
    )
if journal.asof(packet["ingestion_time_ns"] - 1):
    raise ValueError(
        "ATHENA exposed impact-calibration study before local ingestion"
    )

frame = journal.frame(
    packet["ingestion_time_ns"],
    max_age_ns=1_000_000_000,
)
if frame["production_authorized"] or not frame["advisory_only"]:
    raise ValueError("ATHENA authority boundary changed")
if frame["abstain_required"]:
    raise ValueError(
        f"ATHENA rejected healthy impact-calibration fixture: {frame}"
    )
if len(frame["evidence"]) != 1:
    raise ValueError(
        "ATHENA did not admit exactly one impact-calibration study"
    )

body = frame["evidence"][0]["body"]["payload"]
if body["manifest_id"] != manifest.manifest_id:
    raise ValueError("ATHENA payload lost study manifest identity")
if body["cohort_id"] != cohort.cohort_id:
    raise ValueError("ATHENA payload lost study cohort identity")
if body["broker_confirmed_observations"] != 0:
    raise ValueError("ATHENA payload strengthened paper evidence")
if body["paper_emulator_observations"] != 1:
    raise ValueError("ATHENA payload lost paper evidence count")
if not journal.verify()["verified"]:
    raise ValueError("ATHENA advisory journal failed verification")

emit(
    {
        "connection": "argus-impact-athena-research",
        "ok": True,
        "contract_version": packet["contract_version"],
        "study_schema_version": manifest.schema_version,
        "manifest_id": manifest.manifest_id,
        "cohort_id": cohort.cohort_id,
        "lineage_id": packet["lineage_id"],
        "impact_model_revision": manifest.impact_model_revision,
        "calibration_revision": manifest.calibration_revision,
        "argus": {
            "event_time_ns": packet["event_time_ns"],
            "study_lock_time_ns": packet["study_lock_time_ns"],
            "available_ns": packet["available_ns"],
            "broker_confirmed_observations": (
                packet["broker_confirmed_observations"]
            ),
            "paper_emulator_observations": (
                packet["paper_emulator_observations"]
            ),
            "paper_only_fixture": True,
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
