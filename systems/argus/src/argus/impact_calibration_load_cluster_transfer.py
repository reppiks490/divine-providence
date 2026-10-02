from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Callable, Iterable, Mapping

from .execution_evidence import (
    ExecutionEvidenceKind,
    LineagedImpactCalibrationObservation,
)
from .impact_calibration_study import (
    ImpactCalibrationStudyCohort,
    ImpactCalibrationStudyManifest,
    _validate_manifest,
    registered_evidence_stratified_summary,
)


PLAN_SCHEMA_VERSION = (
    "argus-impact-calibration-load-cluster-transfer-plan-v1"
)
CLUSTER_FIELD = "source_run_id"

_ALLOWED_METRICS = {
    "mean_fill_fraction_error",
    "mean_absolute_fill_fraction_error",
    "mean_slippage_error_ticks",
    "mean_absolute_slippage_error_ticks",
    "root_mean_squared_slippage_error_ticks",
    "slippage_underprediction_rate",
}

_MIN_BOOTSTRAP_REPLICATES = 200
_MAX_BOOTSTRAP_REPLICATES = 10_000
_MAX_LOAD_BANDS = 12
_MASK64 = (1 << 64) - 1
_LCG_MULT = 6364136223846793005
_LCG_INC = 1442695040888963407


@dataclass(frozen=True)
class ImpactCalibrationLoadClusterTransferPlan:
    plan_id: str
    schema_version: str
    manifest_id: str
    created_time_ns: int
    cluster_field: str
    load_bands: tuple[tuple[str, float, float | None], ...]
    confidence_alpha: float
    bootstrap_replicates: int
    bootstrap_seed: int
    min_clusters_per_kind_per_band: int
    min_metric_observations_per_kind_per_band: int
    metrics: tuple[str, ...]
    tolerances: tuple[tuple[str, str, float], ...]
    execution_authorized: bool = False
    production_decision_authorized: bool = False


@dataclass(frozen=True)
class LoadClusterTransferMetricResult:
    band_label: str
    lower_ratio_inclusive: float
    upper_ratio_exclusive: float | None
    metric: str
    broker_estimate: float
    paper_estimate: float
    paper_minus_broker: float
    lower: float
    upper: float
    tolerance: float
    within_tolerance: bool
    confidence_level: float
    alpha: float
    broker_cluster_count: int
    paper_cluster_count: int
    broker_observation_count: int
    paper_observation_count: int
    bootstrap_replicates: int
    cluster_field: str = CLUSTER_FIELD
    method: str = (
        "deterministic_load_stratified_two_sample_cluster_percentile"
    )


@dataclass(frozen=True)
class LoadClusterTransferCompatibilityResult:
    plan_id: str
    manifest_id: str
    cohort_id: str
    results: tuple[LoadClusterTransferMetricResult, ...]
    all_within_tolerance: bool
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
        raise ValueError(f"{name} must not contain surrounding whitespace")
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
        raise ValueError(f"{name} must be finite and non-negative")
    return out


def _finite_positive(name: str, value: float) -> float:
    out = _finite_nonnegative(name, value)
    if out <= 0.0:
        raise ValueError(f"{name} must be positive")
    return out


def _alpha(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("confidence_alpha must be numeric")
    out = float(value)
    if not math.isfinite(out) or not 0.0 < out < 1.0:
        raise ValueError(
            "confidence_alpha must be finite and strictly between 0 and 1"
        )
    return out


def _canonical_metrics(values: Iterable[str]) -> tuple[str, ...]:
    metrics = tuple(sorted(set(values)))
    if not metrics:
        raise ValueError(
            "at least one load-cluster transfer metric is required"
        )
    if any(
        not isinstance(metric, str) or not metric.strip()
        for metric in metrics
    ):
        raise ValueError(
            "load-cluster transfer metric names must be non-empty strings"
        )
    unknown = set(metrics) - _ALLOWED_METRICS
    if unknown:
        raise ValueError(
            f"unsupported load-cluster transfer metrics: {sorted(unknown)}"
        )
    return metrics


def _canonical_load_bands(
    values: Iterable[tuple[str, float, float | None]],
) -> tuple[tuple[str, float, float | None], ...]:
    bands: list[tuple[str, float, float | None]] = []
    labels: set[str] = set()

    for item in values:
        if not isinstance(item, tuple) or len(item) != 3:
            raise TypeError(
                "load_bands must contain (label, lower, upper_or_none) tuples"
            )
        label = _text("load band label", item[0])
        if label in labels:
            raise ValueError("load band labels must be unique")
        labels.add(label)

        lower = _finite_nonnegative(
            f"load band {label} lower",
            item[1],
        )
        upper = item[2]
        if upper is not None:
            upper = _finite_positive(
                f"load band {label} upper",
                upper,
            )
            if upper <= lower:
                raise ValueError(
                    "load band upper bound must exceed lower bound"
                )
        bands.append((label, lower, upper))

    if not bands:
        raise ValueError("at least one load band is required")
    if len(bands) > _MAX_LOAD_BANDS:
        raise ValueError(
            f"at most {_MAX_LOAD_BANDS} load bands are allowed"
        )

    bands.sort(key=lambda row: row[1])
    if bands[0][1] != 0.0:
        raise ValueError("load bands must begin at ratio 0.0")

    for index, (_, _, upper) in enumerate(bands):
        if index < len(bands) - 1:
            if upper is None:
                raise ValueError(
                    "only the final load band may have an open upper bound"
                )
            if upper != bands[index + 1][1]:
                raise ValueError(
                    "load bands must be contiguous with no gaps or overlaps"
                )
        elif upper is not None:
            raise ValueError(
                "final load band must have an open upper bound"
            )
    return tuple(bands)


def _canonical_tolerances(
    bands: tuple[tuple[str, float, float | None], ...],
    metrics: tuple[str, ...],
    tolerances: Mapping[tuple[str, str], float],
) -> tuple[tuple[str, str, float], ...]:
    if not isinstance(tolerances, Mapping):
        raise TypeError("tolerances must be a mapping")
    expected = {
        (label, metric)
        for label, _, _ in bands
        for metric in metrics
    }
    if set(tolerances) != expected:
        raise ValueError(
            "tolerances must define exactly one value for every "
            "load-band/metric pair"
        )
    return tuple(
        (
            label,
            metric,
            _finite_positive(
                f"tolerance[{label},{metric}]",
                tolerances[(label, metric)],
            ),
        )
        for label, _, _ in bands
        for metric in metrics
    )


def _plan_payload(
    plan: ImpactCalibrationLoadClusterTransferPlan,
) -> dict[str, Any]:
    return {
        "schema_version": plan.schema_version,
        "manifest_id": plan.manifest_id,
        "created_time_ns": plan.created_time_ns,
        "cluster_field": plan.cluster_field,
        "load_bands": plan.load_bands,
        "confidence_alpha": plan.confidence_alpha,
        "bootstrap_replicates": plan.bootstrap_replicates,
        "bootstrap_seed": plan.bootstrap_seed,
        "min_clusters_per_kind_per_band": (
            plan.min_clusters_per_kind_per_band
        ),
        "min_metric_observations_per_kind_per_band": (
            plan.min_metric_observations_per_kind_per_band
        ),
        "metrics": plan.metrics,
        "tolerances": plan.tolerances,
    }


def create_prospective_load_cluster_transfer_plan(
    manifest: ImpactCalibrationStudyManifest,
    *,
    created_time_ns: int,
    load_bands: Iterable[tuple[str, float, float | None]],
    tolerances: Mapping[tuple[str, str], float],
    confidence_alpha: float = 0.05,
    bootstrap_replicates: int = 2_000,
    bootstrap_seed: int = 0,
    min_clusters_per_kind_per_band: int = 2,
    min_metric_observations_per_kind_per_band: int = 2,
    metrics: Iterable[str] = (
        "mean_fill_fraction_error",
        "mean_absolute_fill_fraction_error",
        "mean_slippage_error_ticks",
        "mean_absolute_slippage_error_ticks",
        "root_mean_squared_slippage_error_ticks",
        "slippage_underprediction_rate",
    ),
) -> ImpactCalibrationLoadClusterTransferPlan:
    """Pre-register a load-stratified source-run cluster transfer audit."""

    _validate_manifest(manifest)
    required = {
        ExecutionEvidenceKind.BROKER_CONFIRMED,
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
    }
    if not required.issubset(set(manifest.evidence_kinds)):
        raise ValueError(
            "load-cluster transfer plan requires both BROKER_CONFIRMED and "
            "ICARUS_PAPER_EMULATOR in the study manifest"
        )

    created = _nonnegative_ns("created_time_ns", created_time_ns)
    if created > manifest.cohort_start_ns:
        raise ValueError(
            "load-cluster transfer plan must be created at or before "
            "cohort_start_ns"
        )

    bands = _canonical_load_bands(load_bands)
    metric_values = _canonical_metrics(metrics)
    tolerance_values = _canonical_tolerances(
        bands,
        metric_values,
        tolerances,
    )
    alpha = _alpha(confidence_alpha)

    reps = _positive_int(
        "bootstrap_replicates",
        bootstrap_replicates,
    )
    if not _MIN_BOOTSTRAP_REPLICATES <= reps <= _MAX_BOOTSTRAP_REPLICATES:
        raise ValueError(
            "bootstrap_replicates must be between "
            f"{_MIN_BOOTSTRAP_REPLICATES} and {_MAX_BOOTSTRAP_REPLICATES}"
        )

    seed = _nonnegative_ns("bootstrap_seed", bootstrap_seed)
    min_clusters = _positive_int(
        "min_clusters_per_kind_per_band",
        min_clusters_per_kind_per_band,
    )
    if min_clusters < 2:
        raise ValueError(
            "min_clusters_per_kind_per_band must be at least 2"
        )

    min_observations = _positive_int(
        "min_metric_observations_per_kind_per_band",
        min_metric_observations_per_kind_per_band,
    )
    if min_observations < 2:
        raise ValueError(
            "min_metric_observations_per_kind_per_band must be at least 2"
        )

    candidate = ImpactCalibrationLoadClusterTransferPlan(
        plan_id="",
        schema_version=PLAN_SCHEMA_VERSION,
        manifest_id=manifest.manifest_id,
        created_time_ns=created,
        cluster_field=CLUSTER_FIELD,
        load_bands=bands,
        confidence_alpha=alpha,
        bootstrap_replicates=reps,
        bootstrap_seed=seed,
        min_clusters_per_kind_per_band=min_clusters,
        min_metric_observations_per_kind_per_band=min_observations,
        metrics=metric_values,
        tolerances=tolerance_values,
    )
    return ImpactCalibrationLoadClusterTransferPlan(
        **{
            **candidate.__dict__,
            "plan_id": _digest(
                "impact-calibration-load-cluster-transfer-plan",
                _plan_payload(candidate),
            ),
        }
    )


def _validate_plan(
    plan: ImpactCalibrationLoadClusterTransferPlan,
    manifest: ImpactCalibrationStudyManifest,
) -> None:
    _validate_manifest(manifest)
    if not isinstance(plan, ImpactCalibrationLoadClusterTransferPlan):
        raise TypeError(
            "plan must be ImpactCalibrationLoadClusterTransferPlan"
        )
    if plan.schema_version != PLAN_SCHEMA_VERSION:
        raise ValueError(
            "unsupported load-cluster transfer plan schema_version"
        )
    if plan.manifest_id != manifest.manifest_id:
        raise ValueError(
            "load-cluster transfer plan references a different manifest"
        )
    if plan.execution_authorized or plan.production_decision_authorized:
        raise ValueError(
            "load-cluster transfer plan unexpectedly carries authority"
        )
    if plan.cluster_field != CLUSTER_FIELD:
        raise ValueError(
            "load-cluster transfer cluster_field is not supported"
        )

    required = {
        ExecutionEvidenceKind.BROKER_CONFIRMED,
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
    }
    if not required.issubset(set(manifest.evidence_kinds)):
        raise ValueError(
            "load-cluster transfer plan requires both execution evidence kinds"
        )

    created = _nonnegative_ns("created_time_ns", plan.created_time_ns)
    if created > manifest.cohort_start_ns:
        raise ValueError(
            "load-cluster transfer plan creation is not prospective"
        )

    bands = _canonical_load_bands(plan.load_bands)
    if bands != plan.load_bands:
        raise ValueError(
            "load-cluster transfer bands are not canonical"
        )

    metrics = _canonical_metrics(plan.metrics)
    if metrics != plan.metrics:
        raise ValueError(
            "load-cluster transfer metrics are not canonical"
        )

    tolerance_map = {
        (label, metric): tolerance
        for label, metric, tolerance in plan.tolerances
    }
    if _canonical_tolerances(
        plan.load_bands,
        plan.metrics,
        tolerance_map,
    ) != plan.tolerances:
        raise ValueError(
            "load-cluster transfer tolerances are not canonical"
        )

    _alpha(plan.confidence_alpha)
    reps = _positive_int(
        "bootstrap_replicates",
        plan.bootstrap_replicates,
    )
    if not _MIN_BOOTSTRAP_REPLICATES <= reps <= _MAX_BOOTSTRAP_REPLICATES:
        raise ValueError(
            "bootstrap_replicates is outside schema limits"
        )
    _nonnegative_ns("bootstrap_seed", plan.bootstrap_seed)

    min_clusters = _positive_int(
        "min_clusters_per_kind_per_band",
        plan.min_clusters_per_kind_per_band,
    )
    if min_clusters < 2:
        raise ValueError(
            "min_clusters_per_kind_per_band must be at least 2"
        )

    min_observations = _positive_int(
        "min_metric_observations_per_kind_per_band",
        plan.min_metric_observations_per_kind_per_band,
    )
    if min_observations < 2:
        raise ValueError(
            "min_metric_observations_per_kind_per_band must be at least 2"
        )

    expected = _digest(
        "impact-calibration-load-cluster-transfer-plan",
        _plan_payload(plan),
    )
    if plan.plan_id != expected:
        raise ValueError(
            "plan_id does not match load-cluster transfer plan content"
        )


def _band_for_ratio(
    bands: tuple[tuple[str, float, float | None], ...],
    ratio: float,
) -> tuple[str, float, float | None]:
    value = _finite_nonnegative(
        "requested_to_visible_ratio",
        ratio,
    )
    for band in bands:
        label, lower, upper = band
        if value >= lower and (upper is None or value < upper):
            return band
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


def _metric_function(
    metric: str,
) -> Callable[[tuple[LineagedImpactCalibrationObservation, ...]], float]:
    if metric == "mean_fill_fraction_error":
        return lambda rows: sum(
            row.calibration.fill_fraction_error for row in rows
        ) / len(rows)

    if metric == "mean_absolute_fill_fraction_error":
        return lambda rows: sum(
            abs(row.calibration.fill_fraction_error) for row in rows
        ) / len(rows)

    if metric == "mean_slippage_error_ticks":
        return lambda rows: sum(
            float(row.calibration.slippage_error_ticks)
            for row in rows
        ) / len(rows)

    if metric == "mean_absolute_slippage_error_ticks":
        return lambda rows: sum(
            abs(float(row.calibration.slippage_error_ticks))
            for row in rows
        ) / len(rows)

    if metric == "root_mean_squared_slippage_error_ticks":
        return lambda rows: math.sqrt(
            sum(
                float(row.calibration.slippage_error_ticks) ** 2
                for row in rows
            )
            / len(rows)
        )

    if metric == "slippage_underprediction_rate":
        return lambda rows: sum(
            1
            for row in rows
            if row.calibration.underpredicted_slippage is True
        ) / len(rows)

    raise ValueError(
        f"unsupported load-cluster transfer metric {metric!r}"
    )


def _clusters(
    rows: tuple[LineagedImpactCalibrationObservation, ...],
    metric: str,
) -> tuple[
    tuple[str, tuple[LineagedImpactCalibrationObservation, ...]],
    ...,
]:
    grouped: dict[
        str,
        list[LineagedImpactCalibrationObservation],
    ] = {}
    namespaces: dict[str, tuple[str, str, str]] = {}
    for row in rows:
        if not _eligible(metric, row):
            continue
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
        grouped.setdefault(
            cluster_id,
            [],
        ).append(row)

    return tuple(
        (
            cluster_id,
            tuple(
                sorted(
                    cluster_rows,
                    key=lambda row: row.lineage_id,
                )
            ),
        )
        for cluster_id, cluster_rows in sorted(grouped.items())
        if cluster_rows
    )


def _flatten(
    clusters: tuple[
        tuple[str, tuple[LineagedImpactCalibrationObservation, ...]],
        ...,
    ],
) -> tuple[LineagedImpactCalibrationObservation, ...]:
    return tuple(
        row
        for _, cluster_rows in clusters
        for row in cluster_rows
    )


def _state(
    seed: int,
    evidence_kind: ExecutionEvidenceKind,
    band_label: str,
    metric: str,
    replicate: int,
) -> int:
    raw = (
        f"{seed}|load-cluster-transfer|{CLUSTER_FIELD}|"
        f"{evidence_kind.value}|{band_label}|{metric}|{replicate}"
    ).encode("utf-8")
    return int.from_bytes(
        hashlib.sha256(raw).digest()[:8],
        "big",
    )


def _resample_clusters(
    clusters: tuple[
        tuple[str, tuple[LineagedImpactCalibrationObservation, ...]],
        ...,
    ],
    *,
    seed: int,
    evidence_kind: ExecutionEvidenceKind,
    band_label: str,
    metric: str,
    replicate: int,
) -> tuple[LineagedImpactCalibrationObservation, ...]:
    state = _state(
        seed,
        evidence_kind,
        band_label,
        metric,
        replicate,
    )
    count = len(clusters)
    out: list[LineagedImpactCalibrationObservation] = []
    for _ in range(count):
        state = (_LCG_MULT * state + _LCG_INC) & _MASK64
        _, cluster_rows = clusters[state % count]
        out.extend(cluster_rows)
    return tuple(out)


def _percentile(
    sorted_values: tuple[float, ...],
    q: float,
) -> float:
    if not sorted_values:
        raise ValueError("percentile requires values")
    if q <= 0.0:
        return sorted_values[0]
    if q >= 1.0:
        return sorted_values[-1]
    position = (len(sorted_values) - 1) * q
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    if lo == hi:
        return sorted_values[lo]
    weight = position - lo
    return (
        sorted_values[lo] * (1.0 - weight)
        + sorted_values[hi] * weight
    )


def registered_load_cluster_transfer_compatibility(
    plan: ImpactCalibrationLoadClusterTransferPlan,
    manifest: ImpactCalibrationStudyManifest,
    cohort: ImpactCalibrationStudyCohort,
) -> LoadClusterTransferCompatibilityResult:
    """Audit paper-vs-broker calibration by load with run-cluster resampling."""

    _validate_plan(plan, manifest)

    # Revalidate prospective study, receipts and calibration lineage first.
    registered_evidence_stratified_summary(manifest, cohort)

    rows_by_band_kind: dict[
        tuple[str, ExecutionEvidenceKind],
        list[LineagedImpactCalibrationObservation],
    ] = {
        (label, kind): []
        for label, _, _ in plan.load_bands
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
            plan.load_bands,
            row.calibration.requested_to_visible_ratio,
        )
        rows_by_band_kind[(label, kind)].append(row)

    tolerance_map = {
        (label, metric): tolerance
        for label, metric, tolerance in plan.tolerances
    }
    results: list[LoadClusterTransferMetricResult] = []

    for label, lower_ratio, upper_ratio in plan.load_bands:
        for metric in plan.metrics:
            broker_clusters = _clusters(
                tuple(
                    rows_by_band_kind[
                        (label, ExecutionEvidenceKind.BROKER_CONFIRMED)
                    ]
                ),
                metric,
            )
            paper_clusters = _clusters(
                tuple(
                    rows_by_band_kind[
                        (
                            label,
                            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                        )
                    ]
                ),
                metric,
            )
            broker_rows = _flatten(broker_clusters)
            paper_rows = _flatten(paper_clusters)

            min_clusters = plan.min_clusters_per_kind_per_band
            if (
                len(broker_clusters) < min_clusters
                or len(paper_clusters) < min_clusters
            ):
                raise ValueError(
                    f"{label} {metric} requires at least {min_clusters} "
                    "eligible source_run_id clusters in both evidence kinds; "
                    f"got broker={len(broker_clusters)}, "
                    f"paper={len(paper_clusters)}"
                )

            min_observations = (
                plan.min_metric_observations_per_kind_per_band
            )
            if (
                len(broker_rows) < min_observations
                or len(paper_rows) < min_observations
            ):
                raise ValueError(
                    f"{label} {metric} requires at least {min_observations} "
                    "eligible observations in both evidence kinds; "
                    f"got broker={len(broker_rows)}, paper={len(paper_rows)}"
                )

            fn = _metric_function(metric)
            broker_estimate = float(fn(broker_rows))
            paper_estimate = float(fn(paper_rows))
            observed_gap = paper_estimate - broker_estimate

            gaps = tuple(
                sorted(
                    float(
                        fn(
                            _resample_clusters(
                                paper_clusters,
                                seed=plan.bootstrap_seed,
                                evidence_kind=(
                                    ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR
                                ),
                                band_label=label,
                                metric=metric,
                                replicate=replicate,
                            )
                        )
                        - fn(
                            _resample_clusters(
                                broker_clusters,
                                seed=plan.bootstrap_seed,
                                evidence_kind=(
                                    ExecutionEvidenceKind.BROKER_CONFIRMED
                                ),
                                band_label=label,
                                metric=metric,
                                replicate=replicate,
                            )
                        )
                    )
                    for replicate in range(plan.bootstrap_replicates)
                )
            )

            lower = _percentile(
                gaps,
                plan.confidence_alpha / 2.0,
            )
            upper = _percentile(
                gaps,
                1.0 - plan.confidence_alpha / 2.0,
            )
            for name, value in (
                ("broker_estimate", broker_estimate),
                ("paper_estimate", paper_estimate),
                ("paper_minus_broker", observed_gap),
                ("lower", lower),
                ("upper", upper),
            ):
                if not math.isfinite(value):
                    raise ValueError(
                        f"load-cluster transfer {name} is not finite"
                    )

            tolerance = tolerance_map[(label, metric)]
            within = lower >= -tolerance and upper <= tolerance
            results.append(
                LoadClusterTransferMetricResult(
                    band_label=label,
                    lower_ratio_inclusive=lower_ratio,
                    upper_ratio_exclusive=upper_ratio,
                    metric=metric,
                    broker_estimate=broker_estimate,
                    paper_estimate=paper_estimate,
                    paper_minus_broker=observed_gap,
                    lower=lower,
                    upper=upper,
                    tolerance=tolerance,
                    within_tolerance=within,
                    confidence_level=1.0 - plan.confidence_alpha,
                    alpha=plan.confidence_alpha,
                    broker_cluster_count=len(broker_clusters),
                    paper_cluster_count=len(paper_clusters),
                    broker_observation_count=len(broker_rows),
                    paper_observation_count=len(paper_rows),
                    bootstrap_replicates=plan.bootstrap_replicates,
                )
            )

    result_tuple = tuple(results)
    return LoadClusterTransferCompatibilityResult(
        plan_id=plan.plan_id,
        manifest_id=manifest.manifest_id,
        cohort_id=cohort.cohort_id,
        results=result_tuple,
        all_within_tolerance=all(
            row.within_tolerance for row in result_tuple
        ),
    )
