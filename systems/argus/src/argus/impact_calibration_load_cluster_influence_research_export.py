from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from typing import Any

from .impact_calibration_load_cluster_influence import (
    ImpactCalibrationLoadClusterInfluencePlan,
    registered_load_cluster_influence_audit,
)
from .impact_calibration_load_cluster_transfer import (
    ImpactCalibrationLoadClusterTransferPlan,
)
from .impact_calibration_study import (
    ImpactCalibrationStudyCohort,
    ImpactCalibrationStudyManifest,
)


EXPORT_CONTRACT_VERSION = (
    "argus-impact-calibration-load-cluster-influence-research-v1"
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


def export_registered_load_cluster_influence(
    plan: ImpactCalibrationLoadClusterInfluencePlan,
    transfer_plan: ImpactCalibrationLoadClusterTransferPlan,
    manifest: ImpactCalibrationStudyManifest,
    cohort: ImpactCalibrationStudyCohort,
    *,
    source_id: str,
    representation_id: str,
    publication_time_ns: int,
    ingestion_time_ns: int,
    version: str = EXPORT_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Export one registered leave-one-source-run sensitivity audit."""

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

    audit = registered_load_cluster_influence_audit(
        plan,
        transfer_plan,
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

    lineage_body = {
        "contract_version": export_version,
        "manifest_id": manifest.manifest_id,
        "cohort_id": cohort.cohort_id,
        "load_cluster_transfer_plan_id": transfer_plan.plan_id,
        "influence_plan_id": plan.plan_id,
        "source_id": source,
        "representation_id": representation,
        "observation_cutoff_ns": manifest.observation_cutoff_ns,
        "study_lock_time_ns": cohort.lock_time_ns,
    }
    lineage_id = (
        "argus-impact-load-cluster-influence-research:"
        + _digest(lineage_body)
    )

    packet = {
        "contract_version": export_version,
        "kind": "argus_impact_calibration_load_cluster_influence",
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
        "load_cluster_transfer_plan_id": transfer_plan.plan_id,
        "influence_plan_schema_version": plan.schema_version,
        "influence_plan_id": plan.plan_id,
        "cluster_field": transfer_plan.cluster_field,
        "load_bands": [
            {
                "label": label,
                "lower_ratio_inclusive": lower,
                "upper_ratio_exclusive": upper,
            }
            for label, lower, upper in transfer_plan.load_bands
        ],
        "metrics": list(transfer_plan.metrics),
        "min_clusters_after_drop_per_kind": (
            plan.min_clusters_after_drop_per_kind
        ),
        "max_abs_shift_tolerances": [
            {
                "band_label": band,
                "metric": metric,
                "max_abs_shift": tolerance,
            }
            for band, metric, tolerance
            in plan.max_abs_shift_tolerances
        ],
        "impact_model_revision": (
            manifest.impact_model_revision
        ),
        "calibration_revision": (
            manifest.calibration_revision
        ),
        "symbols": list(manifest.symbols),
        "execution_source_revisions": [
            {
                "repository": repository,
                "commit": commit,
            }
            for repository, commit
            in manifest.execution_source_revisions
        ],
        "influence_results": [
            {
                **asdict(row),
                "worst_evidence_kind": (
                    row.worst_evidence_kind.value
                ),
            }
            for row in audit.results
        ],
        "all_stable_under_leave_one_cluster": (
            audit.all_stable_under_leave_one_cluster
        ),
        "sensitivity_method": "leave_one_source_run_cluster_out",
        "formal_influence_theorem": False,
        "jackknife_confidence_interval": False,
        "hypothesis_test": False,
        "multiplicity_adjusted": False,
        "causal_effect_estimate": False,
        "paper_evidence_promoted": False,
        "broker_substitution_authorized": False,
        "quality_flags": [
            "prospective_calibration_study",
            "prospective_load_cluster_transfer_plan",
            "prospective_cluster_influence_plan",
            "load_stratified",
            "source_run_cluster_sensitivity",
            "single_cluster_domination_guardrail",
            "evidence_classes_not_pooled",
        ],
        "advisory_only": True,
        "execution_authorized": False,
        "production_authorized": False,
        "production_decision_authorized": False,
    }

    _canonical(packet)
    return packet
