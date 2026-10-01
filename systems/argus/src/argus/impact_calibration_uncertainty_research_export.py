from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from typing import Any

from .execution_evidence import ExecutionEvidenceKind
from .impact_calibration_study import (
    ImpactCalibrationStudyCohort,
    ImpactCalibrationStudyManifest,
)
from .impact_calibration_uncertainty import (
    ImpactCalibrationBootstrapPlan,
    registered_bootstrap_uncertainty,
)


EXPORT_CONTRACT_VERSION = (
    "argus-impact-calibration-uncertainty-research-v1"
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


def _stratum_payload(stratum) -> dict[str, Any]:
    return {
        "evidence_kind": stratum.evidence_kind.value,
        "market_fill_confirmed": stratum.market_fill_confirmed,
        "broker_confirmed": stratum.broker_confirmed,
        "observations": stratum.observations,
        "intervals": [
            asdict(interval) for interval in stratum.intervals
        ],
    }


def export_registered_bootstrap_uncertainty(
    plan: ImpactCalibrationBootstrapPlan,
    manifest: ImpactCalibrationStudyManifest,
    cohort: ImpactCalibrationStudyCohort,
    *,
    source_id: str,
    representation_id: str,
    publication_time_ns: int,
    ingestion_time_ns: int,
    version: str = EXPORT_CONTRACT_VERSION,
) -> dict[str, Any]:
    """Export pre-registered bootstrap uncertainty for ATHENA research.

    The registered bootstrap is recomputed before export. Publication cannot
    precede study cohort lock, and downstream local visibility must still wait
    for ingestion time.
    """

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

    strata = registered_bootstrap_uncertainty(
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

    stratum_payloads = [
        _stratum_payload(stratum) for stratum in strata
    ]
    broker_observations = sum(
        stratum["observations"]
        for stratum in stratum_payloads
        if stratum["evidence_kind"]
        == ExecutionEvidenceKind.BROKER_CONFIRMED.value
    )
    paper_observations = sum(
        stratum["observations"]
        for stratum in stratum_payloads
        if stratum["evidence_kind"]
        == ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR.value
    )

    lineage_body = {
        "contract_version": export_version,
        "manifest_id": manifest.manifest_id,
        "cohort_id": cohort.cohort_id,
        "bootstrap_plan_id": plan.plan_id,
        "source_id": source,
        "representation_id": representation,
        "observation_cutoff_ns": manifest.observation_cutoff_ns,
        "study_lock_time_ns": cohort.lock_time_ns,
    }
    lineage_id = (
        "argus-impact-uncertainty-research:"
        + _digest(lineage_body)
    )

    quality_flags = [
        "prospective_calibration_study",
        "prospective_bootstrap_plan",
        "deterministic_resampling",
        "execution_evidence_stratified",
        "descriptive_percentile_intervals",
    ]
    if broker_observations:
        quality_flags.append(
            "contains_broker_confirmed_evidence"
        )
    if paper_observations:
        quality_flags.append(
            "contains_paper_emulator_evidence"
        )

    packet = {
        "contract_version": export_version,
        "kind": "argus_impact_calibration_bootstrap_uncertainty",
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
        "bootstrap_plan_schema_version": plan.schema_version,
        "bootstrap_plan_id": plan.plan_id,
        "confidence_alpha": plan.confidence_alpha,
        "confidence_level": 1.0 - plan.confidence_alpha,
        "bootstrap_replicates": plan.bootstrap_replicates,
        "bootstrap_seed": plan.bootstrap_seed,
        "min_metric_observations": (
            plan.min_metric_observations
        ),
        "metrics": list(plan.metrics),
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
        "broker_confirmed_observations": (
            broker_observations
        ),
        "paper_emulator_observations": (
            paper_observations
        ),
        "evidence_strata": stratum_payloads,
        "interval_method": (
            "deterministic_nonparametric_percentile"
        ),
        "simultaneous_coverage": False,
        "multiplicity_adjusted": False,
        "hypothesis_test": False,
        "causal_effect_estimate": False,
        "quality_flags": quality_flags,
        "advisory_only": True,
        "execution_authorized": False,
        "production_authorized": False,
        "production_decision_authorized": False,
    }

    _canonical(packet)
    return packet
