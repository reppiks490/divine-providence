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
    _validate_plan as _validate_transfer_plan,
    registered_load_cluster_transfer_compatibility,
)
from .impact_calibration_study import (
    ImpactCalibrationStudyCohort,
    ImpactCalibrationStudyManifest,
    _validate_manifest,
)


PLAN_SCHEMA_VERSION = (
    "argus-impact-calibration-load-cluster-influence-plan-v1"
)

_ALLOWED_METRICS = {
    "mean_fill_fraction_error",
    "mean_absolute_fill_fraction_error",
    "mean_slippage_error_ticks",
    "mean_absolute_slippage_error_ticks",
    "root_mean_squared_slippage_error_ticks",
    "slippage_underprediction_rate",
}


@dataclass(frozen=True)
class ImpactCalibrationLoadClusterInfluencePlan:
    plan_id: str
    schema_version: str
    manifest_id: str
    load_cluster_transfer_plan_id: str
    created_time_ns: int
    min_clusters_after_drop_per_kind: int
    max_abs_shift_tolerances: tuple[tuple[str, str, float], ...]
    execution_authorized: bool = False
    production_decision_authorized: bool = False


@dataclass(frozen=True)
class LoadClusterInfluenceResult:
    band_label: str
    metric: str
    baseline_paper_minus_broker: float
    max_abs_leave_one_cluster_shift: float
    max_allowed_abs_shift: float
    worst_evidence_kind: ExecutionEvidenceKind
    worst_source_run_id: str
    worst_leave_one_paper_minus_broker: float
    broker_cluster_count: int
    paper_cluster_count: int
    leave_one_evaluations: int
    stable_under_leave_one_cluster: bool
    execution_authorized: bool = False
    production_decision_authorized: bool = False


@dataclass(frozen=True)
class LoadClusterInfluenceAudit:
    plan_id: str
    manifest_id: str
    cohort_id: str
    transfer_plan_id: str
    results: tuple[LoadClusterInfluenceResult, ...]
    all_stable_under_leave_one_cluster: bool
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


def _nonnegative_ns(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _positive_int(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _finite_positive(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    out = float(value)
    if not math.isfinite(out) or out <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return out


def _canonical_shift_tolerances(
    transfer_plan: ImpactCalibrationLoadClusterTransferPlan,
    values: Mapping[tuple[str, str], float],
) -> tuple[tuple[str, str, float], ...]:
    if not isinstance(values, Mapping):
        raise TypeError("max_abs_shift_tolerances must be a mapping")

    expected = {
        (label, metric)
        for label, _, _ in transfer_plan.load_bands
        for metric in transfer_plan.metrics
    }
    if set(values) != expected:
        raise ValueError(
            "max_abs_shift_tolerances must define exactly one value for every "
            "load-band/metric pair"
        )

    return tuple(
        (
            label,
            metric,
            _finite_positive(
                f"max_abs_shift_tolerance[{label},{metric}]",
                values[(label, metric)],
            ),
        )
        for label, _, _ in transfer_plan.load_bands
        for metric in transfer_plan.metrics
    )


def _plan_payload(
    plan: ImpactCalibrationLoadClusterInfluencePlan,
) -> dict[str, Any]:
    return {
        "schema_version": plan.schema_version,
        "manifest_id": plan.manifest_id,
        "load_cluster_transfer_plan_id": (
            plan.load_cluster_transfer_plan_id
        ),
        "created_time_ns": plan.created_time_ns,
        "min_clusters_after_drop_per_kind": (
            plan.min_clusters_after_drop_per_kind
        ),
        "max_abs_shift_tolerances": (
            plan.max_abs_shift_tolerances
        ),
    }


def create_prospective_load_cluster_influence_plan(
    manifest: ImpactCalibrationStudyManifest,
    transfer_plan: ImpactCalibrationLoadClusterTransferPlan,
    *,
    created_time_ns: int,
    max_abs_shift_tolerances: Mapping[tuple[str, str], float],
    min_clusters_after_drop_per_kind: int = 2,
) -> ImpactCalibrationLoadClusterInfluencePlan:
    """Pre-register a leave-one-source-run-out fragility audit."""

    _validate_manifest(manifest)
    _validate_transfer_plan(transfer_plan, manifest)

    created = _nonnegative_ns("created_time_ns", created_time_ns)
    if created > manifest.cohort_start_ns:
        raise ValueError(
            "influence plan must be created at or before cohort_start_ns"
        )

    minimum = _positive_int(
        "min_clusters_after_drop_per_kind",
        min_clusters_after_drop_per_kind,
    )

    tolerances = _canonical_shift_tolerances(
        transfer_plan,
        max_abs_shift_tolerances,
    )

    candidate = ImpactCalibrationLoadClusterInfluencePlan(
        plan_id="",
        schema_version=PLAN_SCHEMA_VERSION,
        manifest_id=manifest.manifest_id,
        load_cluster_transfer_plan_id=transfer_plan.plan_id,
        created_time_ns=created,
        min_clusters_after_drop_per_kind=minimum,
        max_abs_shift_tolerances=tolerances,
    )
    return ImpactCalibrationLoadClusterInfluencePlan(
        **{
            **candidate.__dict__,
            "plan_id": _digest(
                "impact-calibration-load-cluster-influence-plan",
                _plan_payload(candidate),
            ),
        }
    )


def _validate_plan(
    plan: ImpactCalibrationLoadClusterInfluencePlan,
    manifest: ImpactCalibrationStudyManifest,
    transfer_plan: ImpactCalibrationLoadClusterTransferPlan,
) -> None:
    _validate_manifest(manifest)
    _validate_transfer_plan(transfer_plan, manifest)

    if not isinstance(
        plan,
        ImpactCalibrationLoadClusterInfluencePlan,
    ):
        raise TypeError(
            "plan must be ImpactCalibrationLoadClusterInfluencePlan"
        )
    if plan.schema_version != PLAN_SCHEMA_VERSION:
        raise ValueError(
            "unsupported load-cluster influence plan schema_version"
        )
    if plan.manifest_id != manifest.manifest_id:
        raise ValueError(
            "influence plan references a different manifest"
        )
    if (
        plan.load_cluster_transfer_plan_id
        != transfer_plan.plan_id
    ):
        raise ValueError(
            "influence plan references a different load-cluster transfer plan"
        )
    if plan.execution_authorized or plan.production_decision_authorized:
        raise ValueError(
            "load-cluster influence plan unexpectedly carries authority"
        )

    created = _nonnegative_ns("created_time_ns", plan.created_time_ns)
    if created > manifest.cohort_start_ns:
        raise ValueError(
            "load-cluster influence plan creation is not prospective"
        )

    _positive_int(
        "min_clusters_after_drop_per_kind",
        plan.min_clusters_after_drop_per_kind,
    )

    tolerance_map = {
        (band, metric): tolerance
        for band, metric, tolerance in plan.max_abs_shift_tolerances
    }
    if _canonical_shift_tolerances(
        transfer_plan,
        tolerance_map,
    ) != plan.max_abs_shift_tolerances:
        raise ValueError(
            "load-cluster influence tolerances are not canonical"
        )

    expected = _digest(
        "impact-calibration-load-cluster-influence-plan",
        _plan_payload(plan),
    )
    if plan.plan_id != expected:
        raise ValueError(
            "plan_id does not match influence plan content"
        )


def _band_for_ratio(
    transfer_plan: ImpactCalibrationLoadClusterTransferPlan,
    ratio: float,
) -> str:
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)):
        raise TypeError("requested_to_visible_ratio must be numeric")
    value = float(ratio)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(
            "requested_to_visible_ratio must be finite and non-negative"
        )

    for label, lower, upper in transfer_plan.load_bands:
        if value >= lower and (upper is None or value < upper):
            return label
    raise ValueError(
        "requested_to_visible_ratio was not covered by load bands"
    )


def _eligible(
    metric: str,
    row: LineagedImpactCalibrationObservation,
) -> bool:
    if metric in {
        "mean_fill_fraction_error",
        "mean_absolute_fill_fraction_error",
    }:
        return True
    return row.calibration.slippage_error_ticks is not None


def _metric_value(
    metric: str,
    rows: tuple[LineagedImpactCalibrationObservation, ...],
) -> float:
    if not rows:
        raise ValueError("metric requires observations")

    if metric == "mean_fill_fraction_error":
        value = sum(
            row.calibration.fill_fraction_error
            for row in rows
        ) / len(rows)
    elif metric == "mean_absolute_fill_fraction_error":
        value = sum(
            abs(row.calibration.fill_fraction_error)
            for row in rows
        ) / len(rows)
    elif metric == "mean_slippage_error_ticks":
        value = sum(
            float(row.calibration.slippage_error_ticks)
            for row in rows
        ) / len(rows)
    elif metric == "mean_absolute_slippage_error_ticks":
        value = sum(
            abs(float(row.calibration.slippage_error_ticks))
            for row in rows
        ) / len(rows)
    elif metric == "root_mean_squared_slippage_error_ticks":
        value = math.sqrt(
            sum(
                float(row.calibration.slippage_error_ticks) ** 2
                for row in rows
            ) / len(rows)
        )
    elif metric == "slippage_underprediction_rate":
        value = sum(
            1
            for row in rows
            if row.calibration.underpredicted_slippage is True
        ) / len(rows)
    else:
        raise ValueError(
            f"unsupported load-cluster influence metric {metric!r}"
        )

    out = float(value)
    if not math.isfinite(out):
        raise ValueError("influence metric result is not finite")
    return out


def _clusters_for(
    cohort: ImpactCalibrationStudyCohort,
    transfer_plan: ImpactCalibrationLoadClusterTransferPlan,
    *,
    band_label: str,
    evidence_kind: ExecutionEvidenceKind,
    metric: str,
) -> tuple[
    tuple[str, tuple[LineagedImpactCalibrationObservation, ...]],
    ...,
]:
    grouped: dict[
        str,
        list[LineagedImpactCalibrationObservation],
    ] = {}

    for subject in cohort.subjects:
        row = subject.row
        if row.receipt.evidence_kind is not evidence_kind:
            continue
        if (
            _band_for_ratio(
                transfer_plan,
                row.calibration.requested_to_visible_ratio,
            )
            != band_label
        ):
            continue
        if not _eligible(metric, row):
            continue
        grouped.setdefault(
            row.receipt.source_run_id,
            [],
        ).append(row)

    return tuple(
        (
            cluster_id,
            tuple(
                sorted(
                    rows,
                    key=lambda row: row.lineage_id,
                )
            ),
        )
        for cluster_id, rows in sorted(grouped.items())
        if rows
    )


def _flatten(
    clusters: tuple[
        tuple[str, tuple[LineagedImpactCalibrationObservation, ...]],
        ...,
    ],
) -> tuple[LineagedImpactCalibrationObservation, ...]:
    return tuple(
        row
        for _, rows in clusters
        for row in rows
    )


def registered_load_cluster_influence_audit(
    plan: ImpactCalibrationLoadClusterInfluencePlan,
    transfer_plan: ImpactCalibrationLoadClusterTransferPlan,
    manifest: ImpactCalibrationStudyManifest,
    cohort: ImpactCalibrationStudyCohort,
) -> LoadClusterInfluenceAudit:
    """Measure leave-one-source-run-out fragility inside every load band."""

    _validate_plan(plan, manifest, transfer_plan)

    baseline = registered_load_cluster_transfer_compatibility(
        transfer_plan,
        manifest,
        cohort,
    )
    baseline_map = {
        (row.band_label, row.metric): row
        for row in baseline.results
    }
    tolerance_map = {
        (band, metric): tolerance
        for band, metric, tolerance in plan.max_abs_shift_tolerances
    }

    results: list[LoadClusterInfluenceResult] = []
    min_after = plan.min_clusters_after_drop_per_kind

    for band_label, _, _ in transfer_plan.load_bands:
        for metric in transfer_plan.metrics:
            base_row = baseline_map[(band_label, metric)]
            baseline_gap = base_row.paper_minus_broker

            broker_clusters = _clusters_for(
                cohort,
                transfer_plan,
                band_label=band_label,
                evidence_kind=ExecutionEvidenceKind.BROKER_CONFIRMED,
                metric=metric,
            )
            paper_clusters = _clusters_for(
                cohort,
                transfer_plan,
                band_label=band_label,
                evidence_kind=(
                    ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR
                ),
                metric=metric,
            )

            if len(broker_clusters) - 1 < min_after:
                raise ValueError(
                    f"{band_label} {metric} leaves fewer than {min_after} "
                    "broker clusters after one-cluster deletion"
                )
            if len(paper_clusters) - 1 < min_after:
                raise ValueError(
                    f"{band_label} {metric} leaves fewer than {min_after} "
                    "paper clusters after one-cluster deletion"
                )

            full_broker = _flatten(broker_clusters)
            full_paper = _flatten(paper_clusters)
            full_broker_value = _metric_value(metric, full_broker)
            full_paper_value = _metric_value(metric, full_paper)

            candidates: list[
                tuple[
                    float,
                    ExecutionEvidenceKind,
                    str,
                    float,
                ]
            ] = []

            min_observations_after_drop = (
                transfer_plan.min_metric_observations_per_kind_per_band
            )

            for index, (cluster_id, _) in enumerate(broker_clusters):
                kept = tuple(
                    cluster
                    for j, cluster in enumerate(broker_clusters)
                    if j != index
                )
                kept_rows = _flatten(kept)
                if len(kept_rows) < min_observations_after_drop:
                    raise ValueError(
                        f"{band_label} {metric} leaves fewer than "
                        f"{min_observations_after_drop} broker observations "
                        "after one-cluster deletion"
                    )
                broker_value = _metric_value(
                    metric,
                    kept_rows,
                )
                gap = full_paper_value - broker_value
                candidates.append(
                    (
                        abs(gap - baseline_gap),
                        ExecutionEvidenceKind.BROKER_CONFIRMED,
                        cluster_id,
                        gap,
                    )
                )

            for index, (cluster_id, _) in enumerate(paper_clusters):
                kept = tuple(
                    cluster
                    for j, cluster in enumerate(paper_clusters)
                    if j != index
                )
                kept_rows = _flatten(kept)
                if len(kept_rows) < min_observations_after_drop:
                    raise ValueError(
                        f"{band_label} {metric} leaves fewer than "
                        f"{min_observations_after_drop} paper observations "
                        "after one-cluster deletion"
                    )
                paper_value = _metric_value(
                    metric,
                    kept_rows,
                )
                gap = paper_value - full_broker_value
                candidates.append(
                    (
                        abs(gap - baseline_gap),
                        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                        cluster_id,
                        gap,
                    )
                )

            if not candidates:
                raise ValueError(
                    "leave-one-cluster audit produced no evaluations"
                )

            candidates.sort(
                key=lambda row: (
                    -row[0],
                    row[1].value,
                    row[2],
                )
            )
            max_shift, worst_kind, worst_id, worst_gap = candidates[0]
            tolerance = tolerance_map[(band_label, metric)]
            stable = max_shift <= tolerance

            results.append(
                LoadClusterInfluenceResult(
                    band_label=band_label,
                    metric=metric,
                    baseline_paper_minus_broker=baseline_gap,
                    max_abs_leave_one_cluster_shift=max_shift,
                    max_allowed_abs_shift=tolerance,
                    worst_evidence_kind=worst_kind,
                    worst_source_run_id=worst_id,
                    worst_leave_one_paper_minus_broker=worst_gap,
                    broker_cluster_count=len(broker_clusters),
                    paper_cluster_count=len(paper_clusters),
                    leave_one_evaluations=(
                        len(broker_clusters) + len(paper_clusters)
                    ),
                    stable_under_leave_one_cluster=stable,
                )
            )

    result_tuple = tuple(results)
    return LoadClusterInfluenceAudit(
        plan_id=plan.plan_id,
        manifest_id=manifest.manifest_id,
        cohort_id=cohort.cohort_id,
        transfer_plan_id=transfer_plan.plan_id,
        results=result_tuple,
        all_stable_under_leave_one_cluster=all(
            row.stable_under_leave_one_cluster
            for row in result_tuple
        ),
    )
