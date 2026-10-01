from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable

from .execution_evidence import (
    ExecutionEvidenceKind,
    ImpactCalibrationEvidenceStratum,
    LineagedImpactCalibrationObservation,
    calibration_by_execution_evidence,
    validate_execution_evidence_receipt,
)


SCHEMA_VERSION = "argus-impact-calibration-study-v1"
_ALLOWED_ANALYSES = {"evidence_stratified_summary"}
_ALLOWED_EVIDENCE_KINDS = (
    ExecutionEvidenceKind.BROKER_CONFIRMED,
    ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
)
_ALLOWED_EXCLUSION_REASONS = {
    "impact_model_revision_mismatch",
    "calibration_revision_mismatch",
    "symbol_not_in_manifest",
    "execution_evidence_not_in_manifest",
    "execution_source_revision_not_in_manifest",
    "decision_before_cohort",
    "decision_at_or_after_cohort_end",
    "execution_observed_after_cutoff",
    "snapshot_age_exceeds_manifest",
    "completion_latency_exceeds_manifest",
}


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
    execution_source_revisions: tuple[tuple[str, str], ...]
    min_observations_per_stratum: int
    max_snapshot_age_ns: int | None
    max_completion_latency_ns: int | None
    analysis_plan: tuple[str, ...]
    execution_authorized: bool = False
    production_decision_authorized: bool = False


@dataclass(frozen=True)
class ImpactCalibrationStudySubject:
    row: LineagedImpactCalibrationObservation
    impact_model_revision: str
    calibration_revision: str


@dataclass(frozen=True)
class ImpactCalibrationStudyCohort:
    manifest_id: str
    cohort_id: str
    lock_time_ns: int
    subjects: tuple[ImpactCalibrationStudySubject, ...]
    included_lineage_ids: tuple[str, ...]
    exclusions: tuple[tuple[str, str], ...]
    broker_confirmed_count: int
    paper_emulator_count: int
    execution_authorized: bool = False
    production_decision_authorized: bool = False


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(
    name: str,
    value: str,
    *,
    upper: bool = False,
    max_len: int = 240,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")
    if len(value) > max_len:
        raise ValueError(f"{name} exceeds {max_len} characters")
    return value.upper() if upper else value


def _sha40(name: str, value: str) -> str:
    out = _text(name, value, max_len=40)
    if len(out) != 40 or any(ch not in "0123456789abcdef" for ch in out):
        raise ValueError(
            f"{name} must be an exact 40-character lowercase hex SHA"
        )
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


def _positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _canonical_source_revisions(
    values: Iterable[tuple[str, str]],
) -> tuple[tuple[str, str], ...]:
    out: set[tuple[str, str]] = set()
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError(
                "execution_source_revisions must contain "
                "(repository, commit) tuples"
            )
        repository, commit = item
        repo = _text("execution source repository", repository)
        if "/" not in repo:
            raise ValueError(
                "execution source repository must be owner/repository"
            )
        out.add((repo, _sha40("execution source commit", commit)))
    if not out:
        raise ValueError(
            "at least one execution source revision is required"
        )
    return tuple(sorted(out))


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
        "evidence_kinds": [
            kind.value for kind in manifest.evidence_kinds
        ],
        "execution_source_revisions": [
            list(item) for item in manifest.execution_source_revisions
        ],
        "min_observations_per_stratum": (
            manifest.min_observations_per_stratum
        ),
        "max_snapshot_age_ns": manifest.max_snapshot_age_ns,
        "max_completion_latency_ns": (
            manifest.max_completion_latency_ns
        ),
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
    execution_source_revisions: Iterable[tuple[str, str]],
    min_observations_per_stratum: int = 1,
    max_snapshot_age_ns: int | None = None,
    max_completion_latency_ns: int | None = None,
    analysis_plan: Iterable[str] = ("evidence_stratified_summary",),
) -> ImpactCalibrationStudyManifest:
    """Register impact-calibration sampling and analysis before the cohort."""

    name = _text("study_name", study_name)
    created = _nonnegative_ns("created_time_ns", created_time_ns)
    start = _nonnegative_ns("cohort_start_ns", cohort_start_ns)
    end = _nonnegative_ns("cohort_end_ns", cohort_end_ns)
    cutoff = _nonnegative_ns(
        "observation_cutoff_ns",
        observation_cutoff_ns,
    )
    impact_revision = _text(
        "impact_model_revision",
        impact_model_revision,
    )
    calibration_rev = _text(
        "calibration_revision",
        calibration_revision,
    )
    max_snapshot = _positive_ns_or_none(
        "max_snapshot_age_ns",
        max_snapshot_age_ns,
    )
    max_latency = _positive_ns_or_none(
        "max_completion_latency_ns",
        max_completion_latency_ns,
    )
    minimum = _positive_int(
        "min_observations_per_stratum",
        min_observations_per_stratum,
    )

    if created > start:
        raise ValueError(
            "manifest must be created at or before cohort_start_ns"
        )
    if start >= end:
        raise ValueError(
            "cohort_start_ns must be before cohort_end_ns"
        )
    if cutoff < end:
        raise ValueError(
            "observation_cutoff_ns must be at or after cohort_end_ns"
        )

    symbol_values = tuple(
        sorted(
            {
                _text(
                    "symbol",
                    value,
                    upper=True,
                    max_len=64,
                )
                for value in symbols
            }
        )
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
        raise ValueError(
            "at least one execution evidence kind is required"
        )
    unsupported_kinds = kinds_set - set(_ALLOWED_EVIDENCE_KINDS)
    if unsupported_kinds:
        raise ValueError(
            "unsupported execution evidence kinds for study schema v1: "
            f"{sorted(kind.value for kind in unsupported_kinds)}"
        )
    kinds = tuple(
        kind for kind in _ALLOWED_EVIDENCE_KINDS if kind in kinds_set
    )

    source_revisions = _canonical_source_revisions(
        execution_source_revisions
    )

    analyses = tuple(
        sorted({_text("analysis", item) for item in analysis_plan})
    )
    if not analyses:
        raise ValueError("at least one analysis is required")
    unknown = set(analyses) - _ALLOWED_ANALYSES
    if unknown:
        raise ValueError(
            f"unsupported analysis plan entries: {sorted(unknown)}"
        )

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
        execution_source_revisions=source_revisions,
        min_observations_per_stratum=minimum,
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


def _validate_manifest(
    manifest: ImpactCalibrationStudyManifest,
) -> None:
    if not isinstance(manifest, ImpactCalibrationStudyManifest):
        raise TypeError(
            "manifest must be ImpactCalibrationStudyManifest"
        )
    if manifest.schema_version != SCHEMA_VERSION:
        raise ValueError(
            "unsupported impact-calibration study schema"
        )
    if (
        manifest.execution_authorized
        or manifest.production_decision_authorized
    ):
        raise ValueError(
            "impact-calibration study manifest carries authority"
        )

    if _text("study_name", manifest.study_name) != manifest.study_name:
        raise ValueError("study_name must be canonical")
    _nonnegative_ns("created_time_ns", manifest.created_time_ns)
    _nonnegative_ns("cohort_start_ns", manifest.cohort_start_ns)
    _nonnegative_ns("cohort_end_ns", manifest.cohort_end_ns)
    _nonnegative_ns(
        "observation_cutoff_ns",
        manifest.observation_cutoff_ns,
    )
    if manifest.created_time_ns > manifest.cohort_start_ns:
        raise ValueError("manifest creation is not prospective")
    if manifest.cohort_start_ns >= manifest.cohort_end_ns:
        raise ValueError("manifest cohort window is invalid")
    if manifest.observation_cutoff_ns < manifest.cohort_end_ns:
        raise ValueError("manifest observation cutoff is invalid")

    if (
        not manifest.symbols
        or manifest.symbols != tuple(sorted(set(manifest.symbols)))
        or any(
            _text(
                "symbol",
                value,
                upper=True,
                max_len=64,
            )
            != value
            for value in manifest.symbols
        )
    ):
        raise ValueError(
            "manifest symbols must be canonical sorted unique values"
        )

    if (
        not manifest.evidence_kinds
        or len(set(manifest.evidence_kinds))
        != len(manifest.evidence_kinds)
        or any(
            not isinstance(kind, ExecutionEvidenceKind)
            for kind in manifest.evidence_kinds
        )
        or any(
            kind not in _ALLOWED_EVIDENCE_KINDS
            for kind in manifest.evidence_kinds
        )
        or manifest.evidence_kinds
        != tuple(
            kind
            for kind in _ALLOWED_EVIDENCE_KINDS
            if kind in set(manifest.evidence_kinds)
        )
    ):
        raise ValueError(
            "manifest evidence_kinds are not canonical"
        )

    if (
        _canonical_source_revisions(
            manifest.execution_source_revisions
        )
        != manifest.execution_source_revisions
    ):
        raise ValueError(
            "manifest execution_source_revisions are not canonical"
        )

    _positive_int(
        "min_observations_per_stratum",
        manifest.min_observations_per_stratum,
    )
    _positive_ns_or_none(
        "max_snapshot_age_ns",
        manifest.max_snapshot_age_ns,
    )
    _positive_ns_or_none(
        "max_completion_latency_ns",
        manifest.max_completion_latency_ns,
    )
    _text(
        "impact_model_revision",
        manifest.impact_model_revision,
    )
    _text(
        "calibration_revision",
        manifest.calibration_revision,
    )

    if (
        not manifest.analysis_plan
        or manifest.analysis_plan
        != tuple(sorted(set(manifest.analysis_plan)))
    ):
        raise ValueError(
            "manifest analysis_plan is not canonical"
        )
    unknown = set(manifest.analysis_plan) - _ALLOWED_ANALYSES
    if unknown:
        raise ValueError(
            f"unsupported analysis plan entries: {sorted(unknown)}"
        )

    expected = "impact-calibration-study:" + _digest(
        _manifest_payload(manifest)
    )
    if manifest.manifest_id != expected:
        raise ValueError(
            "manifest_id does not match manifest content"
        )


def _validate_subject(
    subject: ImpactCalibrationStudySubject,
) -> None:
    if not isinstance(subject, ImpactCalibrationStudySubject):
        raise TypeError(
            "subjects must contain ImpactCalibrationStudySubject"
        )
    _text(
        "impact_model_revision",
        subject.impact_model_revision,
    )
    _text(
        "calibration_revision",
        subject.calibration_revision,
    )

    # A one-row safe aggregation exercises the complete execution-receipt,
    # lineaged-calibration, and calibration-observation validation stack.
    calibration_by_execution_evidence((subject.row,))
    validate_execution_evidence_receipt(subject.row.receipt)


def _included_subject_payload(
    subjects: tuple[ImpactCalibrationStudySubject, ...],
) -> list[dict[str, str]]:
    return [
        {
            "lineage_id": subject.row.lineage_id,
            "impact_model_revision": (
                subject.impact_model_revision
            ),
            "calibration_revision": subject.calibration_revision,
        }
        for subject in subjects
    ]


def lock_impact_calibration_study_cohort(
    manifest: ImpactCalibrationStudyManifest,
    subjects: Iterable[ImpactCalibrationStudySubject],
    *,
    lock_time_ns: int,
) -> ImpactCalibrationStudyCohort:
    """Lock only after the predeclared observation cutoff has passed."""

    _validate_manifest(manifest)
    lock_time = _nonnegative_ns("lock_time_ns", lock_time_ns)
    if lock_time < manifest.observation_cutoff_ns:
        raise ValueError(
            "cohort cannot be locked before observation_cutoff_ns"
        )

    seen_lineage: set[str] = set()
    seen_receipts: set[str] = set()
    included: list[ImpactCalibrationStudySubject] = []
    exclusions: list[tuple[str, str]] = []
    source_revisions = set(manifest.execution_source_revisions)

    for subject in tuple(subjects):
        _validate_subject(subject)
        row = subject.row
        receipt = row.receipt
        lineage_id = row.lineage_id

        if lineage_id in seen_lineage:
            raise ValueError(
                "duplicate lineage_id in calibration-study subjects"
            )
        if receipt.receipt_id in seen_receipts:
            raise ValueError(
                "duplicate execution receipt in calibration-study subjects"
            )
        seen_lineage.add(lineage_id)
        seen_receipts.add(receipt.receipt_id)

        calibration = row.calibration
        reason: str | None = None

        if (
            subject.impact_model_revision
            != manifest.impact_model_revision
        ):
            reason = "impact_model_revision_mismatch"
        elif (
            subject.calibration_revision
            != manifest.calibration_revision
        ):
            reason = "calibration_revision_mismatch"
        elif receipt.symbol not in manifest.symbols:
            reason = "symbol_not_in_manifest"
        elif receipt.evidence_kind not in manifest.evidence_kinds:
            reason = "execution_evidence_not_in_manifest"
        elif (
            receipt.source_repo,
            receipt.source_commit,
        ) not in source_revisions:
            reason = "execution_source_revision_not_in_manifest"
        elif receipt.decision_time_ns < manifest.cohort_start_ns:
            reason = "decision_before_cohort"
        elif receipt.decision_time_ns >= manifest.cohort_end_ns:
            reason = "decision_at_or_after_cohort_end"
        elif (
            receipt.observed_time_ns
            > manifest.observation_cutoff_ns
        ):
            reason = "execution_observed_after_cutoff"
        elif (
            manifest.max_snapshot_age_ns is not None
            and calibration.snapshot_age_ns
            > manifest.max_snapshot_age_ns
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
            included.append(subject)

    if not included:
        raise ValueError(
            "no calibration subjects matched the prospective manifest"
        )

    included.sort(key=lambda subject: subject.row.lineage_id)
    exclusions.sort()

    broker_count = sum(
        1
        for subject in included
        if subject.row.receipt.evidence_kind
        is ExecutionEvidenceKind.BROKER_CONFIRMED
    )
    paper_count = sum(
        1
        for subject in included
        if subject.row.receipt.evidence_kind
        is ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR
    )

    counts = {
        ExecutionEvidenceKind.BROKER_CONFIRMED: broker_count,
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR: paper_count,
    }
    short = {
        kind.value: counts[kind]
        for kind in manifest.evidence_kinds
        if counts[kind] < manifest.min_observations_per_stratum
    }
    if short:
        raise ValueError(
            "insufficient observations for predeclared evidence strata: "
            f"{short}"
        )

    included_tuple = tuple(included)
    payload = {
        "manifest_id": manifest.manifest_id,
        "lock_time_ns": lock_time,
        "included_subjects": _included_subject_payload(
            included_tuple
        ),
        "exclusions": exclusions,
        "broker_confirmed_count": broker_count,
        "paper_emulator_count": paper_count,
    }
    cohort_id = "impact-calibration-cohort:" + _digest(payload)

    return ImpactCalibrationStudyCohort(
        manifest_id=manifest.manifest_id,
        cohort_id=cohort_id,
        lock_time_ns=lock_time,
        subjects=included_tuple,
        included_lineage_ids=tuple(
            subject.row.lineage_id for subject in included_tuple
        ),
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
        raise TypeError(
            "cohort must be ImpactCalibrationStudyCohort"
        )
    if (
        cohort.execution_authorized
        or cohort.production_decision_authorized
    ):
        raise ValueError(
            "impact-calibration study cohort carries authority"
        )
    if cohort.manifest_id != manifest.manifest_id:
        raise ValueError(
            "cohort was not locked under this manifest"
        )
    if cohort.lock_time_ns < manifest.observation_cutoff_ns:
        raise ValueError(
            "cohort lock_time_ns predates observation cutoff"
        )
    if not cohort.subjects:
        raise ValueError("cohort subjects are required")

    source_revisions = set(manifest.execution_source_revisions)
    seen_receipts: set[str] = set()
    for subject in cohort.subjects:
        _validate_subject(subject)
        row = subject.row
        receipt = row.receipt

        if receipt.receipt_id in seen_receipts:
            raise ValueError(
                "cohort contains duplicate execution receipt"
            )
        seen_receipts.add(receipt.receipt_id)

        if (
            subject.impact_model_revision
            != manifest.impact_model_revision
        ):
            raise ValueError(
                "cohort subject impact model revision was not predeclared"
            )
        if (
            subject.calibration_revision
            != manifest.calibration_revision
        ):
            raise ValueError(
                "cohort subject calibration revision was not predeclared"
            )
        if receipt.symbol not in manifest.symbols:
            raise ValueError(
                "cohort subject symbol was not predeclared"
            )
        if receipt.evidence_kind not in manifest.evidence_kinds:
            raise ValueError(
                "cohort subject evidence kind was not predeclared"
            )
        if (
            receipt.source_repo,
            receipt.source_commit,
        ) not in source_revisions:
            raise ValueError(
                "cohort subject execution source revision was not predeclared"
            )
        if not (
            manifest.cohort_start_ns
            <= receipt.decision_time_ns
            < manifest.cohort_end_ns
        ):
            raise ValueError(
                "cohort subject decision time lies outside cohort window"
            )
        if receipt.observed_time_ns > manifest.observation_cutoff_ns:
            raise ValueError(
                "cohort subject was observed after cutoff"
            )
        if (
            manifest.max_snapshot_age_ns is not None
            and row.calibration.snapshot_age_ns
            > manifest.max_snapshot_age_ns
        ):
            raise ValueError(
                "cohort subject snapshot age exceeds manifest"
            )
        if (
            manifest.max_completion_latency_ns is not None
            and row.calibration.completion_latency_ns
            > manifest.max_completion_latency_ns
        ):
            raise ValueError(
                "cohort subject completion latency exceeds manifest"
            )

    expected_ids = tuple(
        subject.row.lineage_id for subject in cohort.subjects
    )
    if cohort.included_lineage_ids != expected_ids:
        raise ValueError(
            "included_lineage_ids do not match cohort subjects"
        )
    if cohort.included_lineage_ids != tuple(
        sorted(cohort.included_lineage_ids)
    ):
        raise ValueError(
            "included_lineage_ids must be sorted"
        )
    if len(set(cohort.included_lineage_ids)) != len(
        cohort.included_lineage_ids
    ):
        raise ValueError(
            "included_lineage_ids must be unique"
        )
    if cohort.exclusions != tuple(sorted(cohort.exclusions)):
        raise ValueError("cohort exclusions must be sorted")
    for lineage_id, reason in cohort.exclusions:
        _text("excluded lineage_id", lineage_id)
        if reason not in _ALLOWED_EXCLUSION_REASONS:
            raise ValueError("cohort contains unknown exclusion reason")

    exclusion_ids = [item[0] for item in cohort.exclusions]
    if len(exclusion_ids) != len(set(exclusion_ids)):
        raise ValueError(
            "cohort exclusions contain duplicate lineage IDs"
        )
    if set(exclusion_ids) & set(cohort.included_lineage_ids):
        raise ValueError(
            "lineage cannot be both included and excluded"
        )

    broker_count = sum(
        1
        for subject in cohort.subjects
        if subject.row.receipt.evidence_kind
        is ExecutionEvidenceKind.BROKER_CONFIRMED
    )
    paper_count = sum(
        1
        for subject in cohort.subjects
        if subject.row.receipt.evidence_kind
        is ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR
    )
    if cohort.broker_confirmed_count != broker_count:
        raise ValueError(
            "broker_confirmed_count is inconsistent"
        )
    if cohort.paper_emulator_count != paper_count:
        raise ValueError(
            "paper_emulator_count is inconsistent"
        )

    counts = {
        ExecutionEvidenceKind.BROKER_CONFIRMED: broker_count,
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR: paper_count,
    }
    if any(
        counts[kind] < manifest.min_observations_per_stratum
        for kind in manifest.evidence_kinds
    ):
        raise ValueError(
            "cohort no longer meets predeclared evidence-stratum minimums"
        )

    payload = {
        "manifest_id": cohort.manifest_id,
        "lock_time_ns": cohort.lock_time_ns,
        "included_subjects": _included_subject_payload(
            cohort.subjects
        ),
        "exclusions": list(cohort.exclusions),
        "broker_confirmed_count": (
            cohort.broker_confirmed_count
        ),
        "paper_emulator_count": cohort.paper_emulator_count,
    }
    expected = "impact-calibration-cohort:" + _digest(payload)
    if cohort.cohort_id != expected:
        raise ValueError(
            "cohort_id does not match cohort content"
        )


def registered_evidence_stratified_summary(
    manifest: ImpactCalibrationStudyManifest,
    cohort: ImpactCalibrationStudyCohort,
) -> tuple[ImpactCalibrationEvidenceStratum, ...]:
    """Run only the analysis predeclared in the prospective manifest."""

    _validate_cohort(manifest, cohort)
    if (
        "evidence_stratified_summary"
        not in manifest.analysis_plan
    ):
        raise ValueError(
            "evidence_stratified_summary was not predeclared"
        )
    return calibration_by_execution_evidence(
        subject.row for subject in cohort.subjects
    )
