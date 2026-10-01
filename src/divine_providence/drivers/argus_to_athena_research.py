"""Verified ARGUS -> ATHENA retrospective research advisory bridge.

A deterministic prospective ARGUS order-block study is completed, exported only
after its predeclared follow-up cutoff, and admitted to ATHENA only at local
ingestion time. Research/advisory evidence only; no execution authority.
"""
from __future__ import annotations

from argus.contracts import EvidenceTier
from argus.orderblock_lifecycle import OrderBlockState
from argus.orderblock_study import (
    OrderBlockStudySubject,
    create_prospective_manifest_v2,
    lock_study_cohort,
)
from argus.orderblock_survival import OrderBlockSurvivalRecord
from argus.research_export import export_registered_survival_uncertainty
from athena.contracts import DataPlane, Provenance
from athena.journal import AdvisoryEvent, AdvisoryJournal

from ._common import emit


REVISION = "argus-orderblock-lifecycle:ebab6ea2"


def _record(
    block_id: str,
    *,
    duration_ns: int,
    invalidated: bool,
) -> OrderBlockSurvivalRecord:
    return OrderBlockSurvivalRecord(
        block_id=block_id,
        direction=1,
        evidence_tier=EvidenceTier.TRUE_DEPTH,
        duration_ns=duration_ns,
        invalidated=invalidated,
        test_count=1,
        rejection_count=0,
        max_penetration_fraction=0.2,
        terminal_state=(
            OrderBlockState.INVALIDATED
            if invalidated
            else OrderBlockState.EXPIRED
        ),
    )


def _subject(
    block_id: str,
    *,
    duration_ns: int,
    invalidated: bool,
    confirmation_time_ns: int,
) -> OrderBlockStudySubject:
    return OrderBlockStudySubject(
        record=_record(
            block_id,
            duration_ns=duration_ns,
            invalidated=invalidated,
        ),
        asset_id="NQ",
        confirmation_time_ns=confirmation_time_ns,
        lifecycle_revision=REVISION,
    )


manifest = create_prospective_manifest_v2(
    study_name="argus-athena-research-bridge-fixture",
    created_time_ns=90,
    cohort_start_ns=100,
    cohort_end_ns=200,
    followup_cutoff_ns=300,
    lifecycle_revision=REVISION,
    asset_ids=("NQ",),
    evidence_tiers=(EvidenceTier.TRUE_DEPTH,),
    directions=(1,),
    analysis_horizon_ns=50,
    confidence_alpha=0.05,
)

cohort = lock_study_cohort(
    manifest,
    (
        _subject(
            "event",
            duration_ns=20,
            invalidated=True,
            confirmation_time_ns=120,
        ),
        _subject(
            "censor",
            duration_ns=30,
            invalidated=False,
            confirmation_time_ns=130,
        ),
        _subject(
            "late",
            duration_ns=100,
            invalidated=True,
            confirmation_time_ns=140,
        ),
    ),
)

packet = export_registered_survival_uncertainty(
    manifest,
    cohort,
    source_id="argus",
    representation_id="orderblock-survival",
    publication_time_ns=310,
    ingestion_time_ns=320,
)

if packet["event_time_ns"] != manifest.followup_cutoff_ns:
    raise ValueError("ARGUS research export escaped follow-up cutoff")
if packet["available_ns"] < packet["event_time_ns"]:
    raise ValueError("ARGUS research export became available before completion")
if packet["ingestion_time_ns"] < packet["available_ns"]:
    raise ValueError("ARGUS research export ingestion precedes publication")
if (
    packet["execution_authorized"]
    or packet["production_authorized"]
    or packet["production_decision_authorized"]
    or not packet["advisory_only"]
):
    raise ValueError("ARGUS research export authority boundary changed")

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

# Publication is not local knowledge. ATHENA must remain blind until receipt.
if journal.asof(packet["available_ns"]):
    raise ValueError("ATHENA exposed ARGUS study at publication instead of ingestion")
if journal.asof(packet["ingestion_time_ns"] - 1):
    raise ValueError("ATHENA exposed ARGUS study before local ingestion")

frame = journal.frame(
    packet["ingestion_time_ns"],
    max_age_ns=1_000_000_000,
)
if frame["production_authorized"] or not frame["advisory_only"]:
    raise ValueError("ATHENA authority boundary changed")
if frame["abstain_required"]:
    raise ValueError(f"ATHENA rejected healthy ARGUS research fixture: {frame}")
if len(frame["evidence"]) != 1:
    raise ValueError("ATHENA did not admit exactly one ARGUS research event")
if frame["evidence"][0]["body"]["payload"]["manifest_id"] != manifest.manifest_id:
    raise ValueError("ATHENA payload lost ARGUS manifest identity")
if not journal.verify()["verified"]:
    raise ValueError("ATHENA advisory journal failed verification")

emit(
    {
        "connection": "argus->athena-research",
        "ok": True,
        "contract_version": packet["contract_version"],
        "manifest_id": manifest.manifest_id,
        "cohort_id": cohort.cohort_id,
        "lineage_id": packet["lineage_id"],
        "study_schema_version": manifest.schema_version,
        "confidence_alpha": packet["confidence_alpha"],
        "confidence_level": packet["confidence_level"],
        "records": packet["records"],
        "invalidations": packet["invalidations"],
        "censored": packet["censored"],
        "administrative_censored": packet["administrative_censored"],
        "argus": {
            "event_time_ns": packet["event_time_ns"],
            "available_ns": packet["available_ns"],
            "input_evidence_tiers": packet["input_evidence_tiers"],
            "advisory_only": packet["advisory_only"],
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
