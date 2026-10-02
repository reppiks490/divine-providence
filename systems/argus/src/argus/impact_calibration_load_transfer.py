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


PLAN_SCHEMA_VERSION = "argus-impact-calibration-load-transfer-plan-v1"

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
class ImpactCalibrationLoadTransferPlan:
    plan_id: str
    schema_version: str
    manifest_id: str
    created_time_ns: int
    load_bands: tuple[tuple[str, float, float | None], ...]
    confidence_alpha: float
    bootstrap_replicates: int
    bootstrap_seed: int
    min_metric_observations_per_kind: int
    metrics: tuple[str, ...]
    tolerances: tuple[tuple[str, str, float], ...]
    execution_authorized: bool = False
    production_decision_authorized: bool = False


@dataclass(frozen=True)
class LoadTransferMetricResult:
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
    broker_sample_size: int
    paper_sample_size: int
    bootstrap_replicates: int
    method: str = "deterministic_load_stratified_two_sample_percentile"


@dataclass(frozen=True)
class LoadTransferCompatibilityResult:
    plan_id: str
    manifest_id: str
    cohort_id: str
    results: tuple[LoadTransferMetricResult, ...]
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
        raise ValueError("at least one load-transfer metric is required")
    if any(
        not isinstance(metric, str) or not metric.strip()
        for metric in metrics
    ):
        raise ValueError(
            "load-transfer metric names must be non-empty strings"
        )
    unknown = set(metrics) - _ALLOWED_METRICS
    if unknown:
        raise ValueError(
            f"unsupported load-transfer metrics: {sorted(unknown)}"
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

    for index, band in enumerate(bands):
        _, lower, upper = band
        if index < len(bands) - 1:
            if upper is None:
                raise ValueError(
                    "only the final load band may have an open upper bound"
                )
            next_lower = bands[index + 1][1]
            if upper != next_lower:
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
    plan: ImpactCalibrationLoadTransferPlan,
) -> dict[str, Any]:
    return {
        "schema_version": plan.schema_version,
        "manifest_id": plan.manifest_id,
        "created_time_ns": plan.created_time_ns,
        "load_bands": plan.load_bands,
        "confidence_alpha": plan.confidence_alpha,
        "bootstrap_replicates": plan.bootstrap_replicates,
        "bootstrap_seed": plan.bootstrap_seed,
        "min_metric_observations_per_kind": (
            plan.min_metric_observations_per_kind
        ),
        "metrics": plan.metrics,
        "tolerances": plan.tolerances,
    }


def create_prospective_load_transfer_plan(
    manifest: ImpactCalibrationStudyManifest,
    *,
    created_time_ns: int,
    load_bands: Iterable[tuple[str, float, float | None]],
    tolerances: Mapping[tuple[str, str], float],
    confidence_alpha: float = 0.05,
    bootstrap_replicates: int = 2_000,
    bootstrap_seed: int = 0,
    min_metric_observations_per_kind: int = 2,
    metrics: Iterable[str] = (
        "mean_fill_fraction_error",
        "mean_absolute_fill_fraction_error",
        "mean_slippage_error_ticks",
        "mean_absolute_slippage_error_ticks",
        "root_mean_squared_slippage_error_ticks",
        "slippage_underprediction_rate",
    ),
) -> ImpactCalibrationLoadTransferPlan:
    """Pre-register transfer calibration across requested/visible load bands."""

    _validate_manifest(manifest)
    required = {
        ExecutionEvidenceKind.BROKER_CONFIRMED,
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
    }
    if not required.issubset(set(manifest.evidence_kinds)):
        raise ValueError(
            "load transfer plan requires both BROKER_CONFIRMED and "
            "ICARUS_PAPER_EMULATOR in the study manifest"
        )

    created = _nonnegative_ns("created_time_ns", created_time_ns)
    if created > manifest.cohort_start_ns:
        raise ValueError(
            "load transfer plan must be created at or before cohort_start_ns"
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
    minimum = _positive_int(
        "min_metric_observations_per_kind",
        min_metric_observations_per_kind,
    )
    if minimum < 2:
        raise ValueError(
            "min_metric_observations_per_kind must be at least 2"
        )

    candidate = ImpactCalibrationLoadTransferPlan(
        plan_id="",
        schema_version=PLAN_SCHEMA_VERSION,
        manifest_id=manifest.manifest_id,
        created_time_ns=created,
        load_bands=bands,
        confidence_alpha=alpha,
        bootstrap_replicates=reps,
        bootstrap_seed=seed,
        min_metric_observations_per_kind=minimum,
        metrics=metric_values,
        tolerances=tolerance_values,
    )
    return ImpactCalibrationLoadTransferPlan(
        **{
            **candidate.__dict__,
            "plan_id": _digest(
                "impact-calibration-load-transfer-plan",
                _plan_payload(candidate),
            ),
        }
    )


def _validate_plan(
    plan: ImpactCalibrationLoadTransferPlan,
    manifest: ImpactCalibrationStudyManifest,
) -> None:
    _validate_manifest(manifest)
    if not isinstance(plan, ImpactCalibrationLoadTransferPlan):
        raise TypeError("plan must be ImpactCalibrationLoadTransferPlan")
    if plan.schema_version != PLAN_SCHEMA_VERSION:
        raise ValueError("unsupported load transfer plan schema_version")
    if plan.manifest_id != manifest.manifest_id:
        raise ValueError("load transfer plan references a different manifest")
    if plan.execution_authorized or plan.production_decision_authorized:
        raise ValueError("load transfer plan unexpectedly carries authority")

    required = {
        ExecutionEvidenceKind.BROKER_CONFIRMED,
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
    }
    if not required.issubset(set(manifest.evidence_kinds)):
        raise ValueError(
            "load transfer plan requires both execution evidence kinds"
        )

    created = _nonnegative_ns("created_time_ns", plan.created_time_ns)
    if created > manifest.cohort_start_ns:
        raise ValueError("load transfer plan creation is not prospective")

    bands = _canonical_load_bands(plan.load_bands)
    if bands != plan.load_bands:
        raise ValueError("load transfer bands are not canonical")

    metrics = _canonical_metrics(plan.metrics)
    if metrics != plan.metrics:
        raise ValueError("load transfer metrics are not canonical")

    tolerance_map = {
        (label, metric): tolerance
        for label, metric, tolerance in plan.tolerances
    }
    canonical_tolerances = _canonical_tolerances(
        plan.load_bands,
        plan.metrics,
        tolerance_map,
    )
    if canonical_tolerances != plan.tolerances:
        raise ValueError("load transfer tolerances are not canonical")

    _alpha(plan.confidence_alpha)
    reps = _positive_int(
        "bootstrap_replicates",
        plan.bootstrap_replicates,
    )
    if not _MIN_BOOTSTRAP_REPLICATES <= reps <= _MAX_BOOTSTRAP_REPLICATES:
        raise ValueError("bootstrap_replicates is outside schema limits")

    _nonnegative_ns("bootstrap_seed", plan.bootstrap_seed)
    minimum = _positive_int(
        "min_metric_observations_per_kind",
        plan.min_metric_observations_per_kind,
    )
    if minimum < 2:
        raise ValueError(
            "min_metric_observations_per_kind must be at least 2"
        )

    expected = _digest(
        "impact-calibration-load-transfer-plan",
        _plan_payload(plan),
    )
    if plan.plan_id != expected:
        raise ValueError(
            "plan_id does not match load transfer plan content"
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


def _eligible_rows(
    metric: str,
    rows: tuple[LineagedImpactCalibrationObservation, ...],
) -> tuple[LineagedImpactCalibrationObservation, ...]:
    if metric in {
        "mean_fill_fraction_error",
        "mean_absolute_fill_fraction_error",
    }:
        return rows
    return tuple(
        row
        for row in rows
        if row.calibration.slippage_error_ticks is not None
    )


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

    raise ValueError(f"unsupported load transfer metric {metric!r}")


def _state(
    seed: int,
    evidence_kind: ExecutionEvidenceKind,
    band_label: str,
    metric: str,
    replicate: int,
) -> int:
    raw = (
        f"{seed}|load-transfer|{evidence_kind.value}|"
        f"{band_label}|{metric}|{replicate}"
    ).encode("utf-8")
    return int.from_bytes(
        hashlib.sha256(raw).digest()[:8],
        "big",
    )


def _resample(
    rows: tuple[LineagedImpactCalibrationObservation, ...],
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
    size = len(rows)
    out: list[LineagedImpactCalibrationObservation] = []
    for _ in range(size):
        state = (_LCG_MULT * state + _LCG_INC) & _MASK64
        out.append(rows[state % size])
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


def registered_load_transfer_compatibility(
    plan: ImpactCalibrationLoadTransferPlan,
    manifest: ImpactCalibrationStudyManifest,
    cohort: ImpactCalibrationStudyCohort,
) -> LoadTransferCompatibilityResult:
    """Compare paper and broker calibration inside predeclared load bands."""

    _validate_plan(plan, manifest)

    # Revalidate the prospective study and all execution/calibration lineage.
    registered_evidence_stratified_summary(manifest, cohort)

    grouped: dict[
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
        grouped[(label, kind)].append(row)

    tolerance_map = {
        (label, metric): tolerance
        for label, metric, tolerance in plan.tolerances
    }
    results: list[LoadTransferMetricResult] = []

    for label, lower_ratio, upper_ratio in plan.load_bands:
        for metric in plan.metrics:
            broker = _eligible_rows(
                metric,
                tuple(
                    grouped[
                        (label, ExecutionEvidenceKind.BROKER_CONFIRMED)
                    ]
                ),
            )
            paper = _eligible_rows(
                metric,
                tuple(
                    grouped[
                        (
                            label,
                            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
                        )
                    ]
                ),
            )
            minimum = plan.min_metric_observations_per_kind
            if len(broker) < minimum or len(paper) < minimum:
                raise ValueError(
                    f"{label} {metric} requires at least {minimum} eligible "
                    "observations in both BROKER_CONFIRMED and "
                    "ICARUS_PAPER_EMULATOR; "
                    f"got broker={len(broker)}, paper={len(paper)}"
                )

            fn = _metric_function(metric)
            broker_estimate = float(fn(broker))
            paper_estimate = float(fn(paper))
            observed_gap = paper_estimate - broker_estimate

            gaps = tuple(
                sorted(
                    float(
                        fn(
                            _resample(
                                paper,
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
                            _resample(
                                broker,
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
                    for replicate in range(
                        plan.bootstrap_replicates
                    )
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
                        f"load transfer {name} is not finite"
                    )

            tolerance = tolerance_map[(label, metric)]
            within = lower >= -tolerance and upper <= tolerance
            results.append(
                LoadTransferMetricResult(
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
                    broker_sample_size=len(broker),
                    paper_sample_size=len(paper),
                    bootstrap_replicates=plan.bootstrap_replicates,
                )
            )

    result_tuple = tuple(results)
    return LoadTransferCompatibilityResult(
        plan_id=plan.plan_id,
        manifest_id=manifest.manifest_id,
        cohort_id=cohort.cohort_id,
        results=result_tuple,
        all_within_tolerance=all(
            row.within_tolerance for row in result_tuple
        ),
    )
