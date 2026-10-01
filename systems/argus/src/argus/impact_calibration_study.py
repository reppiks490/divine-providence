from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Iterable

from .execution_evidence import (
    ExecutionEvidenceKind,
    ImpactCalibrationEvidenceStratum,
    LineagedImpactCalibrationObservation,
    calibration_by_execution_evidence,
)


SCHEMA_VERSION = "argus-impact-calibration-study-v1"
_ALLOWED_ANALYSES = {"evidence_stratified_summary"}


@dataclass(frozen=True)
class ImpactCalibrationStudyManifest:
    manifest_id: str
    schema_version: str
    study_name: str
    created_time_ns: int
    cohort_start_ns: int
    cohort_end_ns: int
    observation_cutoff_ns: int
    impact_model_revision: str
    calibration_revision: str
    symbols: tuple[str, ...]
    evidence_kinds: tuple[ExecutionEvidenceKind, ...]
    max_snapshot_age_ns: int | None
    max_completion_latency_ns: int | None
    analysis_plan: tuple[str, ...]


@dataclass(frozen=True)
class ImpactCalibrationStudySubject:
    row: LineagedImpactCalibrationObservation
    impact_model_revision: str
    calibration_revision: str


@dataclass(frozen=True)
class ImpactCalibrationStudyCohort:
    manifest_id: str
    cohort_id: str
    rows: tuple[LineagedImpactCalibrationObservation, ...]
    included_lineage_ids: tuple[str, ...]
    exclusions: tuple[tuple[str, str], ...]
    broker_confirmed_count: int
    paper_emulator_count: int


def _canonical(value) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(name: str, value: str, *, upper: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")
    out = value.upper() if upper else value
    return out


def _nonnegative_ns(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _positive_ns_or_none(name: str, value: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer or None")
    return value


def _manifest_payload(manifest: ImpactCalibrationStudyManifest) -> dict:
    return {
        "schema_version": manifest.schema_version,
        "study_name": manifest.study_name,
        "created_time_ns": manifest.created_time_ns,
        "cohort_start_ns": manifest.cohort_start_ns,
        "cohort_end_ns": manifest.cohort_end_ns,
        "observation_cutoff_ns": manifest.observation_cutoff_ns,
        "impact_model_revision": manifest.impact_model_revision,
        "calibration_revision": manifest.calibration_revision,
        "symbols": list(manifest.symbols),
        "evidence_kinds": [kind.value for kind in manifest.evidence_kinds],
        "max_snapshot_age_ns": manifest.max_snapshot_age_ns,
        "max_completion_latency_ns": manifest.max_completion_latency_ns,
        "analysis_plan": list(manifest.analysis_plan),
    }


def create_impact_calibration_study_manifest(
    *,
    study_name: str,
    created_time_ns: int,
    cohort_start_ns: int,
    cohort_end_ns: int,
    observation_cutoff_ns: int,
    impact_model_revision: str,
    calibration_revision: str,
    symbols: Iterable[str],
    evidence_kinds: Iterable[ExecutionEvidenceKind],
    max_snapshot_age_ns: int | None = None,
    max_completion_latency_ns: int | None = None,
    analysis_plan: Iterable[str] = ("evidence_stratified_summary",),
) -> ImpactCalibrationStudyManifest:
    name = _text("study_name", study_name)
    created = _nonnegative_ns("created_time_ns", created_time_ns)
    start = _nonnegative_ns("cohort_start_ns", cohort_start_ns)
    end = _nonnegative_ns("cohort_end_ns", cohort_end_ns)
    cutoff = _nonnegative_ns("observation_cutoff_ns", observation_cutoff_ns)
    impact_revision = _text("impact_model_revision", impact_model_revision)
    calibration_rev = _text("calibration_revision", calibration_revision)
    max_snapshot = _positive_ns_or_none(
        "max_snapshot_age_ns",
        max_snapshot_age_ns,
    )
    max_latency = _positive_ns_or_none(
        "max_completion_latency_ns",
        max_completion_latency_ns,
    )

    if created > start:
        raise ValueError("manifest must be created at or before cohort_start_ns")
    if start >= end:
        raise ValueError("cohort_start_ns must be before cohort_end_ns")
    if cutoff < end:
        raise ValueError(
            "observation_cutoff_ns must be at or after cohort_end_ns"
        )

    symbol_values = tuple(
        sorted({_text("symbol", value, upper=True) for value in symbols})
    )
    if not symbol_values:
        raise ValueError("at least one symbol is required")

    kinds_set: set[ExecutionEvidenceKind] = set()
    for kind in evidence_kinds:
        if not isinstance(kind, ExecutionEvidenceKind):
            raise TypeError(
                "evidence_kinds must contain ExecutionEvidenceKind values"
            )
        kinds_set.add(kind)
    if not kinds_set:
        raise ValueError("at least one execution evidence kind is required")
    kinds = tuple(
        kind
        for kind in ExecutionEvidenceKind
        if kind in kinds_set
    )

    analyses = tuple(
        sorted({_text("analysis", item) for item in analysis_plan})
    )
    if not analyses:
        raise ValueError("at least one analysis is required")
    unknown = set(analyses) - _ALLOWED_ANALYSES
    if unknown:
        raise ValueError(f"unsupported analysis plan entries: {sorted(unknown)}")

    candidate = ImpactCalibrationStudyManifest(
        manifest_id="",
        schema_version=SCHEMA_VERSION,
        study_name=name,
        created_time_ns=created,
        cohort_start_ns=start,
        cohort_end_ns=end,
        observation_cutoff_ns=cutoff,
        impact_model_revision=impact_revision,
        calibration_revision=calibration_rev,
        symbols=symbol_values,
        evidence_kinds=kinds,
        max_snapshot_age_ns=max_snapshot,
        max_completion_latency_ns=max_latency,
        analysis_plan=analyses,
    )
    manifest_id = "impact-calibration-study:" + _digest(
        _manifest_payload(candidate)
    )
    return ImpactCalibrationStudyManifest(
        **{**candidate.__dict__, "manifest_id": manifest_id}
    )


def _validate_manifest(manifest: ImpactCalibrationStudyManifest) -> None:
    if not isinstance(manifest, ImpactCalibrationStudyManifest):
        raise TypeError("manifest must be ImpactCalibrationStudyManifest")
    if manifest.schema_version != SCHEMA_VERSION:
        raise ValueError("unsupported impact-calibration study schema")

    if _text("study_name", manifest.study_name) != manifest.study_name:
        raise ValueError("study_name must be canonical")
    _nonnegative_ns("created_time_ns", manifest.created_time_ns)
    _nonnegative_ns("cohort_start_ns", manifest.cohort_start_ns)
    _nonnegative_ns("cohort_end_ns", manifest.cohort_end_ns)
    _nonnegative_ns("observation_cutoff_ns", manifest.observation_cutoff_ns)
    if manifest.created_time_ns > manifest.cohort_start_ns:
        raise ValueError("manifest creation is not prospective")
    if manifest.cohort_start_ns >= manifest.cohort_end_ns:
        raise ValueError("manifest cohort window is invalid")
    if manifest.observation_cutoff_ns < manifest.cohort_end_ns:
        raise ValueError("manifest observation cutoff is invalid")

    if (
        not manifest.symbols
        or manifest.symbols != tuple(sorted(set(manifest.symbols)))
        or any(_text("symbol", value, upper=True) != value for value in manifest.symbols)
    ):
        raise ValueError("manifest symbols must be canonical sorted unique values")

    if (
        not manifest.evidence_kinds
        or len(set(manifest.evidence_kinds)) != len(manifest.evidence_kinds)
        or any(
            not isinstance(kind, ExecutionEvidenceKind)
            for kind in manifest.evidence_kinds
        )
        or manifest.evidence_kinds
        != tuple(
            kind
            for kind in ExecutionEvidenceKind
            if kind in set(manifest.evidence_kinds)
        )
    ):
        raise ValueError("manifest evidence_kinds are not canonical")

    _positive_ns_or_none(
        "max_snapshot_age_ns",
        manifest.max_snapshot_age_ns,
    )
    _positive_ns_or_none(
        "max_completion_latency_ns",
        manifest.max_completion_latency_ns,
    )
    _text("impact_model_revision", manifest.impact_model_revision)
    _text("calibration_revision", manifest.calibration_revision)

    if (
        not manifest.analysis_plan
        or manifest.analysis_plan != tuple(sorted(set(manifest.analysis_plan)))
    ):
        raise ValueError("manifest analysis_plan is not canonical")
    unknown = set(manifest.analysis_plan) - _ALLOWED_ANALYSES
    if unknown:
        raise ValueError(f"unsupported analysis plan entries: {sorted(unknown)}")

    expected = "impact-calibration-study:" + _digest(
        _manifest_payload(manifest)
    )
    if manifest.manifest_id != expected:
        raise ValueError("manifest_id does not match manifest content")


def _validate_subject(subject: ImpactCalibrationStudySubject) -> None:
    if not isinstance(subject, ImpactCalibrationStudySubject):
        raise TypeError("subjects must contain ImpactCalibrationStudySubject")
    _text("impact_model_revision", subject.impact_model_revision)
    _text("calibration_revision", subject.calibration_revision)

    # A one-row safe aggregation exercises the complete execution-receipt,
    # lineaged-calibration, and calibration-observation validation stack.
    calibration_by_execution_evidence((subject.row,))


def lock_impact_calibration_study_cohort(
    manifest: ImpactCalibrationStudyManifest,
    subjects: Iterable[ImpactCalibrationStudySubject],
) -> ImpactCalibrationStudyCohort:
    _validate_manifest(manifest)

    seen: set[str] = set()
    included: list[LineagedImpactCalibrationObservation] = []
    exclusions: list[tuple[str, str]] = []

    for subject in tuple(subjects):
        _validate_subject(subject)
        row = subject.row
        lineage_id = row.lineage_id
        if lineage_id in seen:
            raise ValueError("duplicate lineage_id in calibration-study subjects")
        seen.add(lineage_id)

        receipt = row.receipt
        calibration = row.calibration
        reason: str | None = None

        if subject.impact_model_revision != manifest.impact_model_revision:
            reason = "impact_model_revision_mismatch"
        elif subject.calibration_revision != manifest.calibration_revision:
            reason = "calibration_revision_mismatch"
        elif receipt.symbol not in manifest.symbols:
            reason = "symbol_not_in_manifest"
        elif receipt.evidence_kind not in manifest.evidence_kinds:
            reason = "execution_evidence_not_in_manifest"
        elif receipt.decision_time_ns < manifest.cohort_start_ns:
            reason = "decision_before_cohort"
        elif receipt.decision_time_ns >= manifest.cohort_end_ns:
            reason = "decision_at_or_after_cohort_end"
        elif receipt.observed_time_ns > manifest.observation_cutoff_ns:
            reason = "execution_observed_after_cutoff"
        elif (
            manifest.max_snapshot_age_ns is not None
            and calibration.snapshot_age_ns > manifest.max_snapshot_age_ns
        ):
            reason = "snapshot_age_exceeds_manifest"
        elif (
            manifest.max_completion_latency_ns is not None
            and calibration.completion_latency_ns
            > manifest.max_completion_latency_ns
        ):
            reason = "completion_latency_exceeds_manifest"

        if reason is not None:
            exclusions.append((lineage_id, reason))
        else:
            included.append(row)

    if not included:
        raise ValueError("no calibration subjects matched the prospective manifest")

    included.sort(key=lambda row: row.lineage_id)
    exclusions.sort()

    broker_count = sum(
        1
        for row in included
        if row.receipt.evidence_kind
        is ExecutionEvidenceKind.BROKER_CONFIRMED
    )
    paper_count = sum(
        1
        for row in included
        if row.receipt.evidence_kind
        is ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR
    )

    payload = {
        "manifest_id": manifest.manifest_id,
        "included_lineage_ids": [row.lineage_id for row in included],
        "exclusions": exclusions,
        "broker_confirmed_count": broker_count,
        "paper_emulator_count": paper_count,
    }
    cohort_id = "impact-calibration-cohort:" + _digest(payload)

    return ImpactCalibrationStudyCohort(
        manifest_id=manifest.manifest_id,
        cohort_id=cohort_id,
        rows=tuple(included),
        included_lineage_ids=tuple(row.lineage_id for row in included),
        exclusions=tuple(exclusions),
        broker_confirmed_count=broker_count,
        paper_emulator_count=paper_count,
    )


def _validate_cohort(
    manifest: ImpactCalibrationStudyManifest,
    cohort: ImpactCalibrationStudyCohort,
) -> None:
    _validate_manifest(manifest)
    if not isinstance(cohort, ImpactCalibrationStudyCohort):
        raise TypeError("cohort must be ImpactCalibrationStudyCohort")
    if cohort.manifest_id != manifest.manifest_id:
        raise ValueError("cohort was not locked under this manifest")
    if not cohort.rows:
        raise ValueError("cohort rows are required")

    for row in cohort.rows:
        calibration_by_execution_evidence((row,))

    expected_ids = tuple(row.lineage_id for row in cohort.rows)
    if cohort.included_lineage_ids != expected_ids:
        raise ValueError("included_lineage_ids do not match cohort rows")
    if cohort.included_lineage_ids != tuple(sorted(cohort.included_lineage_ids)):
        raise ValueError("included_lineage_ids must be sorted")
    if len(set(cohort.included_lineage_ids)) != len(cohort.included_lineage_ids):
        raise ValueError("included_lineage_ids must be unique")
    if cohort.exclusions != tuple(sorted(cohort.exclusions)):
        raise ValueError("cohort exclusions must be sorted")

    exclusion_ids = [item[0] for item in cohort.exclusions]
    if len(exclusion_ids) != len(set(exclusion_ids)):
        raise ValueError("cohort exclusions contain duplicate lineage IDs")
    if set(exclusion_ids) & set(cohort.included_lineage_ids):
        raise ValueError("lineage cannot be both included and excluded")

    broker_count = sum(
        1
        for row in cohort.rows
        if row.receipt.evidence_kind
        is ExecutionEvidenceKind.BROKER_CONFIRMED
    )
    paper_count = sum(
        1
        for row in cohort.rows
        if row.receipt.evidence_kind
        is ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR
    )
    if cohort.broker_confirmed_count != broker_count:
        raise ValueError("broker_confirmed_count is inconsistent")
    if cohort.paper_emulator_count != paper_count:
        raise ValueError("paper_emulator_count is inconsistent")

    payload = {
        "manifest_id": cohort.manifest_id,
        "included_lineage_ids": list(cohort.included_lineage_ids),
        "exclusions": list(cohort.exclusions),
        "broker_confirmed_count": cohort.broker_confirmed_count,
        "paper_emulator_count": cohort.paper_emulator_count,
    }
    expected = "impact-calibration-cohort:" + _digest(payload)
    if cohort.cohort_id != expected:
        raise ValueError("cohort_id does not match cohort content")


def registered_evidence_stratified_summary(
    manifest: ImpactCalibrationStudyManifest,
    cohort: ImpactCalibrationStudyCohort,
) -> tuple[ImpactCalibrationEvidenceStratum, ...]:
    _validate_cohort(manifest, cohort)
    if "evidence_stratified_summary" not in manifest.analysis_plan:
        raise ValueError("evidence_stratified_summary was not predeclared")
    return calibration_by_execution_evidence(cohort.rows)
