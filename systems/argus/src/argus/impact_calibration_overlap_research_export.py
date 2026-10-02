from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from typing import Any

from .impact_calibration_load_cluster_transfer import (
    ImpactCalibrationLoadClusterTransferPlan,
)
from .impact_calibration_overlap import (
    ImpactCalibrationOverlapPlan,
    registered_overlap_audit,
)
from .impact_calibration_study import (
    ImpactCalibrationStudyCohort,
    ImpactCalibrationStudyManifest,
)


EXPORT_CONTRACT_VERSION = (
    "argus-impact-calibration-overlap-research-v1"
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(
        _canonical(value).encode("utf-8")
    ).hexdigest()


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if value != value.strip():
        raise ValueError(
            f"{name} must not contain surrounding whitespace"
        )
    return value


def _nonnegative_ns(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            f"{name} must be a non-negative integer"
        )
    return value


def export_registered_overlap_audit(
    overlap_plan: ImpactCalibrationOverlapPlan,
    manifest: ImpactCalibrationStudyManifest,
    transfer_plan: ImpactCalibrationLoadClusterTransferPlan,
    cohort: ImpactCalibrationStudyCohort,
    *,
    source_id: str,
    representation_id: str,
    publication_time_ns: int,
    ingestion_time_ns: int,
    version: str = EXPORT_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Export a registered paper/broker observable-support audit."""

    source = _text("source_id", source_id)
    representation = _text(
        "representation_id",
        representation_id,
    )
    export_version = _text("version", version)
    publication = _nonnegative_ns(
        "publication_time_ns",
        publication_time_ns,
    )
    ingestion = _nonnegative_ns(
        "ingestion_time_ns",
        ingestion_time_ns,
    )

    audit = registered_overlap_audit(
        overlap_plan,
        manifest,
        transfer_plan,
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

    overlap_results: list[dict[str, Any]] = []
    for result in audit.results:
        row = asdict(result)
        row["bins"] = [
            asdict(bin_row)
            for bin_row in result.bins
        ]
        overlap_results.append(row)

    lineage_body = {
        "contract_version": export_version,
        "manifest_id": manifest.manifest_id,
        "cohort_id": cohort.cohort_id,
        "load_cluster_transfer_plan_id": transfer_plan.plan_id,
        "overlap_plan_id": overlap_plan.plan_id,
        "source_id": source,
        "representation_id": representation,
        "observation_cutoff_ns": manifest.observation_cutoff_ns,
        "study_lock_time_ns": cohort.lock_time_ns,
    }
    lineage_id = (
        "argus-impact-overlap-research:"
        + _digest(lineage_body)
    )

    packet = {
        "contract_version": export_version,
        "kind": "argus_impact_calibration_support_overlap",
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
        "load_cluster_transfer_plan_schema_version": (
            transfer_plan.schema_version
        ),
        "load_cluster_transfer_plan_id": transfer_plan.plan_id,
        "overlap_plan_schema_version": overlap_plan.schema_version,
        "overlap_plan_id": overlap_plan.plan_id,
        "covariates": list(overlap_plan.covariates),
        "covariate_bins": {
            covariate: [
                {
                    "lower_inclusive": lower,
                    "upper_exclusive": upper,
                }
                for lower, upper in bins
            ]
            for covariate, bins in overlap_plan.covariate_bins
        },
        "max_total_variation": [
            {
                "band_label": label,
                "covariate": covariate,
                "max_total_variation": maximum,
            }
            for label, covariate, maximum
            in overlap_plan.max_total_variation
        ],
        "min_observations_per_kind_per_band": (
            overlap_plan.min_observations_per_kind_per_band
        ),
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
        "baseline_transfer_all_within_tolerance": (
            audit.baseline_transfer_all_within_tolerance
        ),
        "all_support_adequate": audit.all_support_adequate,
        "overlap_results": overlap_results,
        "support_metric": "empirical_binned_total_variation",
        "formal_equivalence_test": False,
        "propensity_score": False,
        "inverse_probability_weighting": False,
        "causal_identification_claim": False,
        "exchangeability_proven": False,
        "hypothesis_test": False,
        "multiplicity_adjusted": False,
        "familywise_coverage": False,
        "paper_evidence_promoted": False,
        "broker_substitution_authorized": False,
        "quality_flags": [
            "prospective_calibration_study",
            "prospective_load_cluster_transfer_plan",
            "prospective_observable_support_overlap_plan",
            "broker_and_paper_evidence_required",
            "load_stratified",
            "source_run_dependence_preserved_by_baseline_audit",
            "evidence_classes_not_pooled",
        ],
        "advisory_only": True,
        "execution_authorized": False,
        "production_authorized": False,
        "production_decision_authorized": False,
    }

    _canonical(packet)
    return packet
