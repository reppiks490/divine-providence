from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import math
from typing import Iterable

from .contracts import EvidenceTier
from .orderblock_lifecycle import OrderBlockState
from .orderblock_survival import (
    KaplanMeierCurve,
    OrderBlockSurvivalRecord,
    SurvivalStratum,
    kaplan_meier,
    survival_by_evidence_tier,
)


STUDY_SCHEMA_VERSION = "argus-orderblock-study-v1"

_ALLOWED_ANALYSES = {
    "kaplan_meier",
    "evidence_tier_strata",
}


@dataclass(frozen=True)
class OrderBlockStudyManifest:
    manifest_id: str
    schema_version: str
    study_name: str
    created_time_ns: int
    cohort_start_ns: int
    cohort_end_ns: int
    followup_cutoff_ns: int
    lifecycle_revision: str
    asset_ids: tuple[str, ...]
    evidence_tiers: tuple[EvidenceTier, ...]
    directions: tuple[int, ...]
    analysis_horizon_ns: int | None
    analysis_plan: tuple[str, ...]


@dataclass(frozen=True)
class OrderBlockStudySubject:
    record: OrderBlockSurvivalRecord
    asset_id: str
    confirmation_time_ns: int
    lifecycle_revision: str


@dataclass(frozen=True)
class OrderBlockStudyCohort:
    manifest_id: str
    cohort_id: str
    records: tuple[OrderBlockSurvivalRecord, ...]
    included_block_ids: tuple[str, ...]
    exclusions: tuple[tuple[str, str], ...]
    administrative_censored: int


def _nonnegative_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _positive_int_or_none(name: str, value: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer or None")
    return value


def _nonempty(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _hash(prefix: str, payload: dict) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return prefix + ":" + hashlib.sha256(raw).hexdigest()


def create_prospective_manifest(
    *,
    study_name: str,
    created_time_ns: int,
    cohort_start_ns: int,
    cohort_end_ns: int,
    followup_cutoff_ns: int,
    lifecycle_revision: str,
    asset_ids: Iterable[str],
    evidence_tiers: Iterable[EvidenceTier],
    directions: Iterable[int] = (-1, 1),
    analysis_horizon_ns: int | None = None,
    analysis_plan: Iterable[str] = (
        "kaplan_meier",
        "evidence_tier_strata",
    ),
) -> OrderBlockStudyManifest:
    """Create an immutable prospective order-block survival study contract."""

    name = _nonempty("study_name", study_name)
    revision = _nonempty("lifecycle_revision", lifecycle_revision)
    created = _nonnegative_int("created_time_ns", created_time_ns)
    start = _nonnegative_int("cohort_start_ns", cohort_start_ns)
    end = _nonnegative_int("cohort_end_ns", cohort_end_ns)
    cutoff = _nonnegative_int("followup_cutoff_ns", followup_cutoff_ns)
    horizon = _positive_int_or_none("analysis_horizon_ns", analysis_horizon_ns)

    if created > start:
        raise ValueError("prospective manifest must be created at or before cohort_start_ns")
    if start >= end:
        raise ValueError("cohort_start_ns must be before cohort_end_ns")
    if cutoff < end:
        raise ValueError("followup_cutoff_ns must be at or after cohort_end_ns")

    assets = tuple(sorted({_nonempty("asset_id", value) for value in asset_ids}))
    if not assets:
        raise ValueError("at least one asset_id is required")

    tiers_set: set[EvidenceTier] = set()
    for tier in evidence_tiers:
        if not isinstance(tier, EvidenceTier):
            raise TypeError("evidence_tiers must contain EvidenceTier values")
        tiers_set.add(tier)
    if not tiers_set:
        raise ValueError("at least one evidence tier is required")
    tiers = tuple(sorted(tiers_set, key=int))

    direction_set: set[int] = set()
    for direction in directions:
        if isinstance(direction, bool) or direction not in (-1, 1):
            raise ValueError("directions may contain only -1 and +1")
        direction_set.add(int(direction))
    if not direction_set:
        raise ValueError("at least one direction is required")
    direction_values = tuple(sorted(direction_set))

    analyses = tuple(sorted({_nonempty("analysis", item) for item in analysis_plan}))
    if not analyses:
        raise ValueError("at least one analysis is required")
    unknown = set(analyses) - _ALLOWED_ANALYSES
    if unknown:
        raise ValueError(f"unsupported analysis plan entries: {sorted(unknown)}")

    identity = {
        "schema_version": STUDY_SCHEMA_VERSION,
        "study_name": name,
        "created_time_ns": created,
        "cohort_start_ns": start,
        "cohort_end_ns": end,
        "followup_cutoff_ns": cutoff,
        "lifecycle_revision": revision,
        "asset_ids": assets,
        "evidence_tiers": [tier.name for tier in tiers],
        "directions": direction_values,
        "analysis_horizon_ns": horizon,
        "analysis_plan": analyses,
    }
    manifest_id = _hash("order-block-study", identity)

    return OrderBlockStudyManifest(
        manifest_id=manifest_id,
        schema_version=STUDY_SCHEMA_VERSION,
        study_name=name,
        created_time_ns=created,
        cohort_start_ns=start,
        cohort_end_ns=end,
        followup_cutoff_ns=cutoff,
        lifecycle_revision=revision,
        asset_ids=assets,
        evidence_tiers=tiers,
        directions=direction_values,
        analysis_horizon_ns=horizon,
        analysis_plan=analyses,
    )


def _validate_subject(subject: OrderBlockStudySubject) -> None:
    if not isinstance(subject, OrderBlockStudySubject):
        raise TypeError("subjects must contain OrderBlockStudySubject values")
    if not isinstance(subject.record, OrderBlockSurvivalRecord):
        raise TypeError("subject record must be OrderBlockSurvivalRecord")
    canonical_asset = _nonempty("asset_id", subject.asset_id)
    canonical_revision = _nonempty("lifecycle_revision", subject.lifecycle_revision)
    if canonical_asset != subject.asset_id:
        raise ValueError("subject asset_id must not contain surrounding whitespace")
    if canonical_revision != subject.lifecycle_revision:
        raise ValueError(
            "subject lifecycle_revision must not contain surrounding whitespace"
        )
    _nonnegative_int("confirmation_time_ns", subject.confirmation_time_ns)

    record = subject.record
    _nonempty("subject record block_id", record.block_id)
    if isinstance(record.direction, bool) or record.direction not in (-1, 1):
        raise ValueError("subject record direction must be +/-1")
    if not isinstance(record.evidence_tier, EvidenceTier):
        raise TypeError("subject record evidence_tier must be EvidenceTier")
    if (
        isinstance(record.duration_ns, bool)
        or not isinstance(record.duration_ns, int)
        or record.duration_ns < 0
    ):
        raise ValueError("subject record duration_ns must be non-negative integer")
    if type(record.invalidated) is not bool:
        raise TypeError("subject record invalidated must be bool")
    if (
        isinstance(record.test_count, bool)
        or not isinstance(record.test_count, int)
        or record.test_count < 0
    ):
        raise ValueError("subject record test_count must be non-negative integer")
    if (
        isinstance(record.rejection_count, bool)
        or not isinstance(record.rejection_count, int)
        or record.rejection_count < 0
        or record.rejection_count > record.test_count
    ):
        raise ValueError("subject record rejection_count must be in [0, test_count]")
    if (
        isinstance(record.max_penetration_fraction, bool)
        or not isinstance(record.max_penetration_fraction, (int, float))
        or not math.isfinite(float(record.max_penetration_fraction))
        or float(record.max_penetration_fraction) < 0
    ):
        raise ValueError(
            "subject record max_penetration_fraction must be finite and non-negative"
        )
    expected = (
        OrderBlockState.INVALIDATED
        if record.invalidated
        else OrderBlockState.EXPIRED
    )
    if record.terminal_state is not expected:
        raise ValueError("subject record terminal_state is inconsistent")


def _manifest_payload(manifest: OrderBlockStudyManifest) -> dict:
    return {
        "schema_version": manifest.schema_version,
        "study_name": manifest.study_name,
        "created_time_ns": manifest.created_time_ns,
        "cohort_start_ns": manifest.cohort_start_ns,
        "cohort_end_ns": manifest.cohort_end_ns,
        "followup_cutoff_ns": manifest.followup_cutoff_ns,
        "lifecycle_revision": manifest.lifecycle_revision,
        "asset_ids": manifest.asset_ids,
        "evidence_tiers": [tier.name for tier in manifest.evidence_tiers],
        "directions": manifest.directions,
        "analysis_horizon_ns": manifest.analysis_horizon_ns,
        "analysis_plan": manifest.analysis_plan,
    }


def _validate_manifest(manifest: OrderBlockStudyManifest) -> None:
    if not isinstance(manifest, OrderBlockStudyManifest):
        raise TypeError("manifest must be OrderBlockStudyManifest")
    if manifest.schema_version != STUDY_SCHEMA_VERSION:
        raise ValueError("unsupported study schema_version")

    if _nonempty("study_name", manifest.study_name) != manifest.study_name:
        raise ValueError("study_name must be canonical")
    if _nonempty("lifecycle_revision", manifest.lifecycle_revision) != manifest.lifecycle_revision:
        raise ValueError("lifecycle_revision must be canonical")

    created = _nonnegative_int("created_time_ns", manifest.created_time_ns)
    start = _nonnegative_int("cohort_start_ns", manifest.cohort_start_ns)
    end = _nonnegative_int("cohort_end_ns", manifest.cohort_end_ns)
    cutoff = _nonnegative_int("followup_cutoff_ns", manifest.followup_cutoff_ns)
    _positive_int_or_none("analysis_horizon_ns", manifest.analysis_horizon_ns)

    if created > start:
        raise ValueError("prospective manifest must be created at or before cohort_start_ns")
    if start >= end:
        raise ValueError("cohort_start_ns must be before cohort_end_ns")
    if cutoff < end:
        raise ValueError("followup_cutoff_ns must be at or after cohort_end_ns")

    if (
        not manifest.asset_ids
        or manifest.asset_ids != tuple(sorted(set(manifest.asset_ids)))
        or any(_nonempty("asset_id", item) != item for item in manifest.asset_ids)
    ):
        raise ValueError("asset_ids must be non-empty canonical sorted unique values")

    if (
        not manifest.evidence_tiers
        or any(not isinstance(tier, EvidenceTier) for tier in manifest.evidence_tiers)
        or manifest.evidence_tiers
        != tuple(sorted(set(manifest.evidence_tiers), key=int))
    ):
        raise ValueError(
            "evidence_tiers must be non-empty canonical sorted unique EvidenceTier values"
        )

    if (
        not manifest.directions
        or any(
            isinstance(direction, bool) or direction not in (-1, 1)
            for direction in manifest.directions
        )
        or manifest.directions != tuple(sorted(set(manifest.directions)))
    ):
        raise ValueError("directions must be non-empty canonical sorted unique +/-1 values")

    if (
        not manifest.analysis_plan
        or manifest.analysis_plan != tuple(sorted(set(manifest.analysis_plan)))
        or any(_nonempty("analysis", item) != item for item in manifest.analysis_plan)
    ):
        raise ValueError("analysis_plan must be non-empty canonical sorted unique values")
    unknown = set(manifest.analysis_plan) - _ALLOWED_ANALYSES
    if unknown:
        raise ValueError(f"unsupported analysis plan entries: {sorted(unknown)}")

    expected_id = _hash("order-block-study", _manifest_payload(manifest))
    if manifest.manifest_id != expected_id:
        raise ValueError("manifest_id does not match manifest content")


def _record_payload(record: OrderBlockSurvivalRecord) -> dict:
    return {
        "block_id": record.block_id,
        "direction": record.direction,
        "evidence_tier": record.evidence_tier.name,
        "duration_ns": record.duration_ns,
        "invalidated": record.invalidated,
        "test_count": record.test_count,
        "rejection_count": record.rejection_count,
        "max_penetration_fraction": float(record.max_penetration_fraction),
        "terminal_state": record.terminal_state.value,
    }


def lock_study_cohort(
    manifest: OrderBlockStudyManifest,
    subjects: Iterable[OrderBlockStudySubject],
) -> OrderBlockStudyCohort:
    """Apply the predeclared study contract and freeze one deterministic cohort."""

    _validate_manifest(manifest)

    subject_rows = tuple(subjects)
    seen: set[str] = set()
    included: list[OrderBlockSurvivalRecord] = []
    exclusions: list[tuple[str, str]] = []
    administrative_censored = 0

    for subject in subject_rows:
        _validate_subject(subject)
        block_id = subject.record.block_id
        if block_id in seen:
            raise ValueError("duplicate block_id in study subjects")
        seen.add(block_id)

        reason: str | None = None
        if subject.lifecycle_revision != manifest.lifecycle_revision:
            reason = "lifecycle_revision_mismatch"
        elif subject.asset_id not in manifest.asset_ids:
            reason = "asset_not_in_manifest"
        elif subject.record.evidence_tier not in manifest.evidence_tiers:
            reason = "evidence_tier_not_in_manifest"
        elif subject.record.direction not in manifest.directions:
            reason = "direction_not_in_manifest"
        elif subject.confirmation_time_ns < manifest.cohort_start_ns:
            reason = "confirmation_before_cohort"
        elif subject.confirmation_time_ns >= manifest.cohort_end_ns:
            reason = "confirmation_at_or_after_cohort_end"

        if reason is not None:
            exclusions.append((block_id, reason))
            continue

        followup_cap = manifest.followup_cutoff_ns - subject.confirmation_time_ns
        if manifest.analysis_horizon_ns is not None:
            followup_cap = min(followup_cap, manifest.analysis_horizon_ns)

        record = subject.record
        if record.duration_ns > followup_cap:
            record = replace(
                record,
                duration_ns=followup_cap,
                invalidated=False,
                terminal_state=OrderBlockState.EXPIRED,
            )
            administrative_censored += 1

        included.append(record)

    if not included:
        raise ValueError("no study subjects matched the prospective manifest")

    included.sort(key=lambda row: row.block_id)
    exclusions.sort()

    cohort_payload = {
        "manifest_id": manifest.manifest_id,
        "records": [_record_payload(row) for row in included],
        "exclusions": exclusions,
        "administrative_censored": administrative_censored,
    }
    cohort_id = _hash("order-block-cohort", cohort_payload)

    return OrderBlockStudyCohort(
        manifest_id=manifest.manifest_id,
        cohort_id=cohort_id,
        records=tuple(included),
        included_block_ids=tuple(row.block_id for row in included),
        exclusions=tuple(exclusions),
        administrative_censored=administrative_censored,
    )


def _validate_cohort(
    manifest: OrderBlockStudyManifest,
    cohort: OrderBlockStudyCohort,
) -> None:
    _validate_manifest(manifest)
    if not isinstance(cohort, OrderBlockStudyCohort):
        raise TypeError("cohort must be OrderBlockStudyCohort")
    if cohort.manifest_id != manifest.manifest_id:
        raise ValueError("cohort was not locked under this manifest")
    if not cohort.records:
        raise ValueError("cohort records are required")

    # Reuse the survival estimator's public fail-closed record validation.
    kaplan_meier(cohort.records)

    expected_ids = tuple(row.block_id for row in cohort.records)
    if cohort.included_block_ids != expected_ids:
        raise ValueError("included_block_ids do not match cohort records")
    if cohort.included_block_ids != tuple(sorted(cohort.included_block_ids)):
        raise ValueError("included_block_ids must be sorted")
    if cohort.exclusions != tuple(sorted(cohort.exclusions)):
        raise ValueError("cohort exclusions must be sorted")
    if (
        isinstance(cohort.administrative_censored, bool)
        or not isinstance(cohort.administrative_censored, int)
        or cohort.administrative_censored < 0
        or cohort.administrative_censored > len(cohort.records)
    ):
        raise ValueError("administrative_censored is invalid")

    payload = {
        "manifest_id": cohort.manifest_id,
        "records": [_record_payload(row) for row in cohort.records],
        "exclusions": list(cohort.exclusions),
        "administrative_censored": cohort.administrative_censored,
    }
    expected_id = _hash("order-block-cohort", payload)
    if cohort.cohort_id != expected_id:
        raise ValueError("cohort_id does not match cohort content")


def registered_kaplan_meier(
    manifest: OrderBlockStudyManifest,
    cohort: OrderBlockStudyCohort,
) -> KaplanMeierCurve:
    _validate_cohort(manifest, cohort)
    if "kaplan_meier" not in manifest.analysis_plan:
        raise ValueError("kaplan_meier was not predeclared")
    return kaplan_meier(cohort.records)


def registered_evidence_strata(
    manifest: OrderBlockStudyManifest,
    cohort: OrderBlockStudyCohort,
) -> tuple[SurvivalStratum, ...]:
    _validate_cohort(manifest, cohort)
    if "evidence_tier_strata" not in manifest.analysis_plan:
        raise ValueError("evidence_tier_strata was not predeclared")
    return survival_by_evidence_tier(cohort.records)
