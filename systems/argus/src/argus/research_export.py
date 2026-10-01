from __future__ import annotations

import hashlib
import json
from typing import Any

from .orderblock_study import (
    OrderBlockStudyCohort,
    OrderBlockStudyManifest,
    STUDY_SCHEMA_V2,
    registered_kaplan_meier,
    registered_survival_uncertainty,
)


EXPORT_CONTRACT_VERSION = "argus-athena-research-v1"


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _canonical_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")
    return value


def _nonnegative_ns(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def export_registered_survival_uncertainty(
    manifest: OrderBlockStudyManifest,
    cohort: OrderBlockStudyCohort,
    *,
    source_id: str,
    representation_id: str,
    publication_time_ns: int,
    ingestion_time_ns: int,
    version: str = EXPORT_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Export a registered ARGUS study result as receipt-time advisory evidence.

    The study result is intentionally not considered knowable before its
    predeclared follow-up cutoff. Publication may occur later, and ATHENA must
    still gate local visibility on ingestion time.
    """

    source = _canonical_text("source_id", source_id)
    representation = _canonical_text("representation_id", representation_id)
    export_version = _canonical_text("version", version)
    publication = _nonnegative_ns("publication_time_ns", publication_time_ns)
    ingestion = _nonnegative_ns("ingestion_time_ns", ingestion_time_ns)

    if not isinstance(manifest, OrderBlockStudyManifest):
        raise TypeError("manifest must be OrderBlockStudyManifest")
    if manifest.schema_version != STUDY_SCHEMA_V2:
        raise ValueError("research uncertainty export requires study schema v2")

    # These registered calls self-verify manifest/cohort identities, enforce
    # predeclared analysis, and force use of the exact manifest alpha.
    curve = registered_kaplan_meier(manifest, cohort)
    band = registered_survival_uncertainty(manifest, cohort)

    knowledge_complete_ns = manifest.followup_cutoff_ns
    if publication < knowledge_complete_ns:
        raise ValueError(
            "publication_time_ns cannot precede predeclared follow-up cutoff"
        )
    if ingestion < publication:
        raise ValueError("ingestion_time_ns cannot precede publication_time_ns")

    final = band.points[-1]
    lineage_body = {
        "contract_version": export_version,
        "manifest_id": manifest.manifest_id,
        "cohort_id": cohort.cohort_id,
        "source_id": source,
        "representation_id": representation,
        "knowledge_complete_ns": knowledge_complete_ns,
    }
    lineage_id = "argus-research:" + _digest(lineage_body)

    packet = {
        "contract_version": export_version,
        "kind": "argus_orderblock_survival_uncertainty",
        "plane": "research",
        "event_time_ns": knowledge_complete_ns,
        "available_ns": publication,
        "ingestion_time_ns": ingestion,
        "source_id": source,
        "representation_id": representation,
        "lineage_id": lineage_id,
        "study_schema_version": manifest.schema_version,
        "manifest_id": manifest.manifest_id,
        "cohort_id": cohort.cohort_id,
        "lifecycle_revision": manifest.lifecycle_revision,
        "asset_ids": list(manifest.asset_ids),
        "input_evidence_tiers": [tier.name for tier in manifest.evidence_tiers],
        "directions": list(manifest.directions),
        "analysis_horizon_ns": manifest.analysis_horizon_ns,
        "followup_cutoff_ns": manifest.followup_cutoff_ns,
        "confidence_alpha": band.alpha,
        "confidence_level": band.confidence_level,
        "records": curve.records,
        "invalidations": curve.invalidations,
        "censored": curve.censored,
        "administrative_censored": cohort.administrative_censored,
        "administrative_censored_block_ids": list(
            cohort.administrative_censored_block_ids
        ),
        "median_survival_ns": curve.median_survival_ns,
        "restricted_mean_survival_ns": curve.restricted_mean_survival_ns,
        "uncertainty_points": len(band.points),
        "final_survival_probability": final.survival_probability,
        "final_lower_confidence": final.lower_confidence,
        "final_upper_confidence": final.upper_confidence,
        "final_cumulative_hazard": final.cumulative_hazard,
        "quality_flags": [
            "retrospective_research",
            "pointwise_uncertainty",
            "prospective_cohort_lock",
        ],
        "advisory_only": True,
        "execution_authorized": False,
        "production_authorized": False,
        "production_decision_authorized": False,
    }

    # Ensure downstream journal hashing can canonicalize the packet now rather
    # than failing after it crosses a sibling boundary.
    _canonical(packet)
    return packet
