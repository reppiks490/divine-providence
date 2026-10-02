from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Iterable, Mapping

from .execution_evidence import (
    ExecutionEvidenceKind,
    LineagedImpactCalibrationObservation,
)
from .impact_calibration_load_cluster_transfer import (
    ImpactCalibrationLoadClusterTransferPlan,
    _band_for_ratio,
    _validate_plan as _validate_transfer_plan,
    registered_load_cluster_transfer_compatibility,
)
from .impact_calibration_study import (
    ImpactCalibrationStudyCohort,
    ImpactCalibrationStudyManifest,
    _validate_manifest,
)


PLAN_SCHEMA_VERSION = "argus-impact-calibration-overlap-plan-v1"

_ALLOWED_COVARIATES = (
    "requested_to_visible_ratio",
    "snapshot_age_ns",
    "completion_latency_ns",
)

_MAX_COVARIATE_BINS = 16


@dataclass(frozen=True)
class ImpactCalibrationOverlapPlan:
    plan_id: str
    schema_version: str
    manifest_id: str
    load_cluster_transfer_plan_id: str
    created_time_ns: int
    covariates: tuple[str, ...]
    covariate_bins: tuple[
        tuple[str, tuple[tuple[float, float | None], ...]],
        ...
    ]
    max_total_variation: tuple[tuple[str, str, float], ...]
    min_observations_per_kind_per_band: int
    execution_authorized: bool = False
    production_decision_authorized: bool = False


@dataclass(frozen=True)
class OverlapBin:
    lower_inclusive: float
    upper_exclusive: float | None
    broker_count: int
    paper_count: int
    broker_probability: float
    paper_probability: float
    absolute_probability_gap: float


@dataclass(frozen=True)
class OverlapCovariateResult:
    band_label: str
    covariate: str
    covariate_timing: str
    broker_clusters: int
    paper_clusters: int
    broker_observations: int
    paper_observations: int
    bins: tuple[OverlapBin, ...]
    total_variation_distance: float
    overlap_coefficient: float
    max_absolute_bin_probability_gap: float
    max_allowed_total_variation: float
    support_adequate: bool
    execution_authorized: bool = False
    production_decision_authorized: bool = False


@dataclass(frozen=True)
class ImpactCalibrationOverlapAudit:
    plan_id: str
    manifest_id: str
    cohort_id: str
    load_cluster_transfer_plan_id: str
    baseline_transfer_all_within_tolerance: bool
    results: tuple[OverlapCovariateResult, ...]
    all_support_adequate: bool
    execution_authorized: bool = False
    production_decision_authorized: bool = False


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(prefix: str, value: Any) -> str:
    return f"{prefix}:" + hashlib.sha256(
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
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _finite_nonnegative(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    out = float(value)
    if not math.isfinite(out) or out < 0.0:
        raise ValueError(
            f"{name} must be finite and non-negative"
        )
    return out


def _unit_interval(name: str, value: float) -> float:
    out = _finite_nonnegative(name, value)
    if out > 1.0:
        raise ValueError(f"{name} must be <= 1")
    return out


def _canonical_covariates(
    values: Iterable[str],
) -> tuple[str, ...]:
    raw = tuple(values)
    if not raw:
        raise ValueError("at least one overlap covariate is required")
    if any(
        not isinstance(value, str) or not value.strip()
        for value in raw
    ):
        raise ValueError(
            "overlap covariate names must be non-empty strings"
        )
    unique = set(raw)
    unknown = unique - set(_ALLOWED_COVARIATES)
    if unknown:
        raise ValueError(
            f"unsupported overlap covariates: {sorted(unknown)}"
        )
    return tuple(
        value for value in _ALLOWED_COVARIATES if value in unique
    )


def _canonical_partition(
    covariate: str,
    values: Iterable[tuple[float, float | None]],
) -> tuple[tuple[float, float | None], ...]:
    bins: list[tuple[float, float | None]] = []
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError(
                f"{covariate} bins must contain (lower, upper_or_none) tuples"
            )
        lower = _finite_nonnegative(
            f"{covariate} bin lower",
            item[0],
        )
        upper = item[1]
        if upper is not None:
            upper = _finite_nonnegative(
                f"{covariate} bin upper",
                upper,
            )
            if upper <= lower:
                raise ValueError(
                    f"{covariate} bin upper must exceed lower"
                )
        bins.append((lower, upper))

    if not bins:
        raise ValueError(f"{covariate} requires at least one bin")
    if len(bins) > _MAX_COVARIATE_BINS:
        raise ValueError(
            f"{covariate} supports at most {_MAX_COVARIATE_BINS} bins"
        )

    bins.sort(key=lambda item: item[0])
    if bins[0][0] != 0.0:
        raise ValueError(
            f"{covariate} bins must begin at 0.0"
        )
    for index, (_, upper) in enumerate(bins):
        if index < len(bins) - 1:
            if upper is None:
                raise ValueError(
                    f"only final {covariate} bin may be open-ended"
                )
            if upper != bins[index + 1][0]:
                raise ValueError(
                    f"{covariate} bins must be contiguous"
                )
        elif upper is not None:
            raise ValueError(
                f"final {covariate} bin must be open-ended"
            )
    return tuple(bins)


def _canonical_covariate_bins(
    covariates: tuple[str, ...],
    values: Mapping[str, Iterable[tuple[float, float | None]]],
) -> tuple[
    tuple[str, tuple[tuple[float, float | None], ...]],
    ...
]:
    if not isinstance(values, Mapping):
        raise TypeError("covariate_bins must be a mapping")
    if set(values) != set(covariates):
        raise ValueError(
            "covariate_bins must define every requested covariate exactly once"
        )
    return tuple(
        (
            covariate,
            _canonical_partition(covariate, values[covariate]),
        )
        for covariate in covariates
    )


def _canonical_tv_limits(
    transfer_plan: ImpactCalibrationLoadClusterTransferPlan,
    covariates: tuple[str, ...],
    values: Mapping[tuple[str, str], float],
) -> tuple[tuple[str, str, float], ...]:
    if not isinstance(values, Mapping):
        raise TypeError("max_total_variation must be a mapping")

    expected = {
        (label, covariate)
        for label, _, _ in transfer_plan.load_bands
        for covariate in covariates
    }
    if set(values) != expected:
        raise ValueError(
            "max_total_variation must define every load-band/covariate pair"
        )
    return tuple(
        (
            label,
            covariate,
            _unit_interval(
                f"max_total_variation[{label},{covariate}]",
                values[(label, covariate)],
            ),
        )
        for label, _, _ in transfer_plan.load_bands
        for covariate in covariates
    )


def _plan_payload(
    plan: ImpactCalibrationOverlapPlan,
) -> dict[str, Any]:
    return {
        "schema_version": plan.schema_version,
        "manifest_id": plan.manifest_id,
        "load_cluster_transfer_plan_id": (
            plan.load_cluster_transfer_plan_id
        ),
        "created_time_ns": plan.created_time_ns,
        "covariates": plan.covariates,
        "covariate_bins": plan.covariate_bins,
        "max_total_variation": plan.max_total_variation,
        "min_observations_per_kind_per_band": (
            plan.min_observations_per_kind_per_band
        ),
    }


def create_prospective_overlap_plan(
    manifest: ImpactCalibrationStudyManifest,
    transfer_plan: ImpactCalibrationLoadClusterTransferPlan,
    *,
    created_time_ns: int,
    covariates: Iterable[str],
    covariate_bins: Mapping[
        str,
        Iterable[tuple[float, float | None]],
    ],
    max_total_variation: Mapping[tuple[str, str], float],
    min_observations_per_kind_per_band: int = 4,
) -> ImpactCalibrationOverlapPlan:
    """Pre-register observable support-overlap diagnostics."""

    _validate_manifest(manifest)
    _validate_transfer_plan(transfer_plan, manifest)

    created = _nonnegative_ns(
        "created_time_ns",
        created_time_ns,
    )
    if created < manifest.created_time_ns:
        raise ValueError(
            "overlap plan cannot predate manifest created_time_ns"
        )
    if created < transfer_plan.created_time_ns:
        raise ValueError(
            "overlap plan cannot predate load-cluster transfer plan"
        )
    if created > manifest.cohort_start_ns:
        raise ValueError(
            "overlap plan must be created at or before cohort_start_ns"
        )

    covariate_values = _canonical_covariates(covariates)
    bin_values = _canonical_covariate_bins(
        covariate_values,
        covariate_bins,
    )
    tv_values = _canonical_tv_limits(
        transfer_plan,
        covariate_values,
        max_total_variation,
    )
    minimum = _positive_int(
        "min_observations_per_kind_per_band",
        min_observations_per_kind_per_band,
    )
    if minimum < 2:
        raise ValueError(
            "min_observations_per_kind_per_band must be at least 2"
        )

    candidate = ImpactCalibrationOverlapPlan(
        plan_id="",
        schema_version=PLAN_SCHEMA_VERSION,
        manifest_id=manifest.manifest_id,
        load_cluster_transfer_plan_id=transfer_plan.plan_id,
        created_time_ns=created,
        covariates=covariate_values,
        covariate_bins=bin_values,
        max_total_variation=tv_values,
        min_observations_per_kind_per_band=minimum,
    )
    return ImpactCalibrationOverlapPlan(
        **{
            **candidate.__dict__,
            "plan_id": _digest(
                "impact-calibration-overlap-plan",
                _plan_payload(candidate),
            ),
        }
    )


def _validate_plan(
    plan: ImpactCalibrationOverlapPlan,
    manifest: ImpactCalibrationStudyManifest,
    transfer_plan: ImpactCalibrationLoadClusterTransferPlan,
) -> None:
    _validate_manifest(manifest)
    _validate_transfer_plan(transfer_plan, manifest)

    if not isinstance(plan, ImpactCalibrationOverlapPlan):
        raise TypeError("plan must be ImpactCalibrationOverlapPlan")
    if plan.schema_version != PLAN_SCHEMA_VERSION:
        raise ValueError("unsupported overlap plan schema_version")
    if plan.manifest_id != manifest.manifest_id:
        raise ValueError("overlap plan references a different manifest")
    if (
        plan.load_cluster_transfer_plan_id
        != transfer_plan.plan_id
    ):
        raise ValueError(
            "overlap plan references a different load-cluster transfer plan"
        )
    if plan.execution_authorized or plan.production_decision_authorized:
        raise ValueError("overlap plan unexpectedly carries authority")

    created = _nonnegative_ns(
        "created_time_ns",
        plan.created_time_ns,
    )
    if created < manifest.created_time_ns:
        raise ValueError("overlap plan predates manifest creation")
    if created < transfer_plan.created_time_ns:
        raise ValueError("overlap plan predates transfer-plan creation")
    if created > manifest.cohort_start_ns:
        raise ValueError("overlap plan creation is not prospective")

    covariates = _canonical_covariates(plan.covariates)
    if covariates != plan.covariates:
        raise ValueError("overlap covariates are not canonical")

    bin_map = dict(plan.covariate_bins)
    bins = _canonical_covariate_bins(
        plan.covariates,
        bin_map,
    )
    if bins != plan.covariate_bins:
        raise ValueError("overlap covariate bins are not canonical")

    tv_map = {
        (label, covariate): value
        for label, covariate, value in plan.max_total_variation
    }
    limits = _canonical_tv_limits(
        transfer_plan,
        plan.covariates,
        tv_map,
    )
    if limits != plan.max_total_variation:
        raise ValueError(
            "overlap total-variation limits are not canonical"
        )

    minimum = _positive_int(
        "min_observations_per_kind_per_band",
        plan.min_observations_per_kind_per_band,
    )
    if minimum < 2:
        raise ValueError(
            "min_observations_per_kind_per_band must be at least 2"
        )

    expected = _digest(
        "impact-calibration-overlap-plan",
        _plan_payload(plan),
    )
    if plan.plan_id != expected:
        raise ValueError(
            "plan_id does not match overlap plan content"
        )


def _source_run_cluster_count(
    rows: tuple[LineagedImpactCalibrationObservation, ...],
) -> int:
    namespaces: dict[str, tuple[str, str, str]] = {}
    for row in rows:
        cluster_id = row.receipt.source_run_id
        namespace = (
            row.receipt.source_system,
            row.receipt.source_repo,
            row.receipt.source_commit,
        )
        existing = namespaces.get(cluster_id)
        if existing is None:
            namespaces[cluster_id] = namespace
        elif existing != namespace:
            raise ValueError(
                "source_run_id collision across execution-source lineage: "
                f"{cluster_id!r}"
            )
    return len(namespaces)


def _covariate_timing(covariate: str) -> str:
    if covariate in {
        "requested_to_visible_ratio",
        "snapshot_age_ns",
    }:
        return "decision_time"
    if covariate == "completion_latency_ns":
        return "post_decision_realized"
    raise ValueError(f"unsupported overlap covariate {covariate!r}")


def _covariate_value(
    row: LineagedImpactCalibrationObservation,
    covariate: str,
) -> float:
    calibration = row.calibration
    if covariate == "requested_to_visible_ratio":
        return _finite_nonnegative(
            covariate,
            calibration.requested_to_visible_ratio,
        )
    if covariate == "snapshot_age_ns":
        return _finite_nonnegative(
            covariate,
            calibration.snapshot_age_ns,
        )
    if covariate == "completion_latency_ns":
        return _finite_nonnegative(
            covariate,
            calibration.completion_latency_ns,
        )
    raise ValueError(f"unsupported overlap covariate {covariate!r}")


def _bin_index(
    bins: tuple[tuple[float, float | None], ...],
    value: float,
) -> int:
    for index, (lower, upper) in enumerate(bins):
        if value >= lower and (upper is None or value < upper):
            return index
    raise ValueError("covariate value is not covered by predeclared bins")


def registered_overlap_audit(
    plan: ImpactCalibrationOverlapPlan,
    manifest: ImpactCalibrationStudyManifest,
    transfer_plan: ImpactCalibrationLoadClusterTransferPlan,
    cohort: ImpactCalibrationStudyCohort,
) -> ImpactCalibrationOverlapAudit:
    """Audit observable paper/broker support inside each load band.

    Total-variation overlap is a descriptive support diagnostic. It is not a
    causal identification theorem, propensity score, or permission to relabel
    paper-emulator evidence as broker-confirmed evidence.
    """

    _validate_plan(plan, manifest, transfer_plan)

    # Revalidate study, execution evidence, load partition and clustered
    # transfer contract before inspecting covariate support.
    baseline = registered_load_cluster_transfer_compatibility(
        transfer_plan,
        manifest,
        cohort,
    )

    rows_by_band_kind: dict[
        tuple[str, ExecutionEvidenceKind],
        list[LineagedImpactCalibrationObservation],
    ] = {
        (label, kind): []
        for label, _, _ in transfer_plan.load_bands
        for kind in (
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
        )
    }

    for subject in cohort.subjects:
        row = subject.row
        kind = row.receipt.evidence_kind
        if kind not in {
            ExecutionEvidenceKind.BROKER_CONFIRMED,
            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
        }:
            continue
        label, _, _ = _band_for_ratio(
            transfer_plan.load_bands,
            row.calibration.requested_to_visible_ratio,
        )
        rows_by_band_kind[(label, kind)].append(row)

    bin_map = dict(plan.covariate_bins)
    limit_map = {
        (label, covariate): value
        for label, covariate, value in plan.max_total_variation
    }
    results: list[OverlapCovariateResult] = []

    for label, _, _ in transfer_plan.load_bands:
        broker_rows = tuple(
            rows_by_band_kind[
                (label, ExecutionEvidenceKind.BROKER_CONFIRMED)
            ]
        )
        paper_rows = tuple(
            rows_by_band_kind[
                (
                    label,
                    ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                )
            ]
        )
        broker_clusters = _source_run_cluster_count(broker_rows)
        paper_clusters = _source_run_cluster_count(paper_rows)
        cluster_minimum = transfer_plan.min_clusters_per_kind_per_band
        if (
            broker_clusters < cluster_minimum
            or paper_clusters < cluster_minimum
        ):
            raise ValueError(
                f"{label} overlap audit requires at least {cluster_minimum} "
                "source_run_id clusters in both evidence kinds; "
                f"got broker={broker_clusters}, paper={paper_clusters}"
            )

        minimum = plan.min_observations_per_kind_per_band
        if len(broker_rows) < minimum or len(paper_rows) < minimum:
            raise ValueError(
                f"{label} overlap audit requires at least {minimum} "
                "observations in both evidence kinds; "
                f"got broker={len(broker_rows)}, paper={len(paper_rows)}"
            )

        for covariate in plan.covariates:
            bins = bin_map[covariate]
            broker_counts = [0] * len(bins)
            paper_counts = [0] * len(bins)

            for row in broker_rows:
                value = _covariate_value(row, covariate)
                broker_counts[_bin_index(bins, value)] += 1

            for row in paper_rows:
                value = _covariate_value(row, covariate)
                paper_counts[_bin_index(bins, value)] += 1

            broker_n = len(broker_rows)
            paper_n = len(paper_rows)
            details: list[OverlapBin] = []
            probability_gaps: list[float] = []
            for index, (lower, upper) in enumerate(bins):
                broker_probability = (
                    broker_counts[index] / broker_n
                )
                paper_probability = (
                    paper_counts[index] / paper_n
                )
                gap = abs(
                    broker_probability - paper_probability
                )
                probability_gaps.append(gap)
                details.append(
                    OverlapBin(
                        lower_inclusive=lower,
                        upper_exclusive=upper,
                        broker_count=broker_counts[index],
                        paper_count=paper_counts[index],
                        broker_probability=broker_probability,
                        paper_probability=paper_probability,
                        absolute_probability_gap=gap,
                    )
                )

            tv = 0.5 * sum(probability_gaps)
            overlap = 1.0 - tv
            max_gap = max(probability_gaps)
            limit = limit_map[(label, covariate)]
            adequate = tv <= limit

            results.append(
                OverlapCovariateResult(
                    band_label=label,
                    covariate=covariate,
                    covariate_timing=_covariate_timing(covariate),
                    broker_clusters=broker_clusters,
                    paper_clusters=paper_clusters,
                    broker_observations=broker_n,
                    paper_observations=paper_n,
                    bins=tuple(details),
                    total_variation_distance=tv,
                    overlap_coefficient=overlap,
                    max_absolute_bin_probability_gap=max_gap,
                    max_allowed_total_variation=limit,
                    support_adequate=adequate,
                )
            )

    result_tuple = tuple(results)
    return ImpactCalibrationOverlapAudit(
        plan_id=plan.plan_id,
        manifest_id=manifest.manifest_id,
        cohort_id=cohort.cohort_id,
        load_cluster_transfer_plan_id=transfer_plan.plan_id,
        baseline_transfer_all_within_tolerance=(
            baseline.all_within_tolerance
        ),
        results=result_tuple,
        all_support_adequate=all(
            row.support_adequate for row in result_tuple
        ),
    )
