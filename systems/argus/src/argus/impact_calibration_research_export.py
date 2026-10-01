from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from typing import Any

from .execution_evidence import ExecutionEvidenceKind
from .impact_calibration_study import (
    ImpactCalibrationStudyCohort,
    ImpactCalibrationStudyManifest,
    registered_evidence_stratified_summary,
)


EXPORT_CONTRACT_VERSION = "argus-impact-calibration-research-v1"


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")
    return value


def _nonnegative_ns(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _summary_payload(stratum) -> dict[str, Any]:
    summary = asdict(stratum.summary)
    return {
        "evidence_kind": stratum.evidence_kind.value,
        "market_fill_confirmed": stratum.market_fill_confirmed,
        "broker_confirmed": stratum.broker_confirmed,
        "observations": stratum.observations,
        "summary": summary,
    }


def export_registered_impact_calibration_study(
    manifest: ImpactCalibrationStudyManifest,
    cohort: ImpactCalibrationStudyCohort,
    *,
    source_id: str,
    representation_id: str,
    publication_time_ns: int,
    ingestion_time_ns: int,
    version: str = EXPORT_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Export one locked prospective impact-calibration study for advisories.

    The function recomputes the registered evidence-stratified analysis before
    export, so receipt, lineage, cohort and manifest validation all run again.
    Publication cannot precede cohort lock, and ATHENA must still gate local
    visibility on ingestion time.
    """

    source = _text("source_id", source_id)
    representation = _text("representation_id", representation_id)
    export_version = _text("version", version)
    publication = _nonnegative_ns(
        "publication_time_ns",
        publication_time_ns,
    )
    ingestion = _nonnegative_ns(
        "ingestion_time_ns",
        ingestion_time_ns,
    )

    strata = registered_evidence_stratified_summary(
        manifest,
        cohort,
    )

    if publication < cohort.lock_time_ns:
        raise ValueError(
            "publication_time_ns cannot precede cohort lock_time_ns"
        )
    if ingestion < publication:
        raise ValueError(
            "ingestion_time_ns cannot precede publication_time_ns"
        )

    stratum_payloads = [_summary_payload(row) for row in strata]
    evidence_kinds = [
        row["evidence_kind"] for row in stratum_payloads
    ]
    broker_count = sum(
        row["observations"]
        for row in stratum_payloads
        if row["evidence_kind"]
        == ExecutionEvidenceKind.BROKER_CONFIRMED.value
    )
    paper_count = sum(
        row["observations"]
        for row in stratum_payloads
        if row["evidence_kind"]
        == ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR.value
    )

    lineage_body = {
        "contract_version": export_version,
        "manifest_id": manifest.manifest_id,
        "cohort_id": cohort.cohort_id,
        "source_id": source,
        "representation_id": representation,
        "observation_cutoff_ns": manifest.observation_cutoff_ns,
        "lock_time_ns": cohort.lock_time_ns,
    }
    lineage_id = "argus-impact-research:" + _digest(lineage_body)

    quality_flags = [
        "prospective_calibration_study",
        "execution_evidence_stratified",
        "registered_analysis_only",
    ]
    if broker_count:
        quality_flags.append("contains_broker_confirmed_evidence")
    if paper_count:
        quality_flags.append("contains_paper_emulator_evidence")

    packet = {
        "contract_version": export_version,
        "kind": "argus_impact_calibration_study",
        "plane": "research",
        "event_time_ns": manifest.observation_cutoff_ns,
        "study_lock_time_ns": cohort.lock_time_ns,
        "available_ns": publication,
        "ingestion_time_ns": ingestion,
        "source_id": source,
        "representation_id": representation,
        "lineage_id": lineage_id,
        "study_schema_version": manifest.schema_version,
        "manifest_id": manifest.manifest_id,
        "cohort_id": cohort.cohort_id,
        "impact_model_revision": manifest.impact_model_revision,
        "calibration_revision": manifest.calibration_revision,
        "symbols": list(manifest.symbols),
        "declared_evidence_kinds": [
            kind.value for kind in manifest.evidence_kinds
        ],
        "execution_source_revisions": [
            {
                "repository": repository,
                "commit": commit,
            }
            for repository, commit
            in manifest.execution_source_revisions
        ],
        "min_observations_per_stratum": (
            manifest.min_observations_per_stratum
        ),
        "max_snapshot_age_ns": manifest.max_snapshot_age_ns,
        "max_completion_latency_ns": (
            manifest.max_completion_latency_ns
        ),
        "included_lineage_ids": list(
            cohort.included_lineage_ids
        ),
        "exclusions": [
            {
                "lineage_id": lineage_id_value,
                "reason": reason,
            }
            for lineage_id_value, reason in cohort.exclusions
        ],
        "broker_confirmed_observations": broker_count,
        "paper_emulator_observations": paper_count,
        "evidence_strata": stratum_payloads,
        "quality_flags": quality_flags,
        "advisory_only": True,
        "execution_authorized": False,
        "production_authorized": False,
        "production_decision_authorized": False,
    }

    # Fail immediately if any summary metric is not canonical JSON data.
    _canonical(packet)
    return packet
