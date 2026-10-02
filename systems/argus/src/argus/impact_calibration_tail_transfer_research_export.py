from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from typing import Any

from .impact_calibration_study import (
    ImpactCalibrationStudyCohort,
    ImpactCalibrationStudyManifest,
)
from .impact_calibration_tail_transfer import (
    ImpactCalibrationTailTransferPlan,
    registered_tail_transfer_compatibility,
)


EXPORT_CONTRACT_VERSION = (
    "argus-impact-calibration-tail-transfer-research-v1"
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


def export_registered_tail_transfer(
    plan: ImpactCalibrationTailTransferPlan,
    manifest: ImpactCalibrationStudyManifest,
    cohort: ImpactCalibrationStudyCohort,
    *,
    source_id: str,
    representation_id: str,
    publication_time_ns: int,
    ingestion_time_ns: int,
    version: str = EXPORT_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Export a registered tail transfer audit as research evidence."""

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

    result = registered_tail_transfer_compatibility(
        plan,
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

    quantile_payloads = [
        asdict(row) for row in result.quantiles
    ]

    lineage_body = {
        "contract_version": export_version,
        "manifest_id": manifest.manifest_id,
        "cohort_id": cohort.cohort_id,
        "tail_transfer_plan_id": plan.plan_id,
        "source_id": source,
        "representation_id": representation,
        "observation_cutoff_ns": manifest.observation_cutoff_ns,
        "study_lock_time_ns": cohort.lock_time_ns,
    }
    lineage_id = (
        "argus-impact-tail-transfer-research:"
        + _digest(lineage_body)
    )

    packet = {
        "contract_version": export_version,
        "kind": "argus_impact_calibration_tail_transfer",
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
        "tail_transfer_plan_schema_version": plan.schema_version,
        "tail_transfer_plan_id": plan.plan_id,
        "metric": plan.metric,
        "quantile_tolerances": [
            {
                "quantile": quantile,
                "tolerance": tolerance,
            }
            for quantile, tolerance in plan.quantile_tolerances
        ],
        "confidence_alpha": plan.confidence_alpha,
        "confidence_level": 1.0 - plan.confidence_alpha,
        "bootstrap_replicates": plan.bootstrap_replicates,
        "bootstrap_seed": plan.bootstrap_seed,
        "min_metric_observations_per_kind": (
            plan.min_metric_observations_per_kind
        ),
        "impact_model_revision": (
            manifest.impact_model_revision
        ),
        "calibration_revision": (
            manifest.calibration_revision
        ),
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
        "tail_quantiles": quantile_payloads,
        "all_within_tolerance": result.all_within_tolerance,
        "comparison_direction": "paper_minus_broker",
        "interval_method": (
            "deterministic_two_sample_quantile_percentile"
        ),
        "formal_equivalence_test": False,
        "multiplicity_adjusted": False,
        "familywise_coverage": False,
        "hypothesis_test": False,
        "causal_effect_estimate": False,
        "paper_evidence_promoted": False,
        "broker_substitution_authorized": False,
        "quality_flags": [
            "prospective_calibration_study",
            "prospective_tail_transfer_plan",
            "broker_and_paper_evidence_required",
            "deterministic_two_sample_quantile_bootstrap",
            "tail_compatibility_gate",
            "evidence_classes_not_pooled",
        ],
        "advisory_only": True,
        "execution_authorized": False,
        "production_authorized": False,
        "production_decision_authorized": False,
    }

    _canonical(packet)
    return packet
