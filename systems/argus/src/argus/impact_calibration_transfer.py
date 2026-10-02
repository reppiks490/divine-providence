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


PLAN_SCHEMA_VERSION = "argus-impact-calibration-transfer-plan-v1"

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
_MASK64 = (1 << 64) - 1
_LCG_MULT = 6364136223846793005
_LCG_INC = 1442695040888963407


@dataclass(frozen=True)
class ImpactCalibrationTransferPlan:
    plan_id: str
    schema_version: str
    manifest_id: str
    created_time_ns: int
    confidence_alpha: float
    bootstrap_replicates: int
    bootstrap_seed: int
    min_metric_observations_per_kind: int
    metrics: tuple[str, ...]
    tolerances: tuple[tuple[str, float], ...]
    execution_authorized: bool = False
    production_decision_authorized: bool = False


@dataclass(frozen=True)
class TransferCompatibilityMetric:
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
    method: str = "deterministic_two_sample_percentile"


@dataclass(frozen=True)
class TransferCompatibilityResult:
    plan_id: str
    manifest_id: str
    cohort_id: str
    metrics: tuple[TransferCompatibilityMetric, ...]
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
        raise ValueError("at least one transfer metric is required")
    if any(
        not isinstance(metric, str) or not metric.strip()
        for metric in metrics
    ):
        raise ValueError("transfer metric names must be non-empty strings")
    unknown = set(metrics) - _ALLOWED_METRICS
    if unknown:
        raise ValueError(
            f"unsupported transfer metrics: {sorted(unknown)}"
        )
    return metrics


def _canonical_tolerances(
    metrics: tuple[str, ...],
    tolerances: Mapping[str, float],
) -> tuple[tuple[str, float], ...]:
    if not isinstance(tolerances, Mapping):
        raise TypeError("tolerances must be a mapping")
    if set(tolerances) != set(metrics):
        raise ValueError(
            "tolerances must define exactly one value for every metric"
        )
    return tuple(
        (
            metric,
            _finite_positive(
                f"tolerance[{metric}]",
                tolerances[metric],
            ),
        )
        for metric in metrics
    )


def _plan_payload(
    plan: ImpactCalibrationTransferPlan,
) -> dict[str, Any]:
    return {
        "schema_version": plan.schema_version,
        "manifest_id": plan.manifest_id,
        "created_time_ns": plan.created_time_ns,
        "confidence_alpha": plan.confidence_alpha,
        "bootstrap_replicates": plan.bootstrap_replicates,
        "bootstrap_seed": plan.bootstrap_seed,
        "min_metric_observations_per_kind": (
            plan.min_metric_observations_per_kind
        ),
        "metrics": plan.metrics,
        "tolerances": plan.tolerances,
    }


def create_prospective_transfer_plan(
    manifest: ImpactCalibrationStudyManifest,
    *,
    created_time_ns: int,
    tolerances: Mapping[str, float],
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
) -> ImpactCalibrationTransferPlan:
    """Pre-register a paper-vs-broker calibration compatibility audit."""

    _validate_manifest(manifest)
    required = {
        ExecutionEvidenceKind.BROKER_CONFIRMED,
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
    }
    if not required.issubset(set(manifest.evidence_kinds)):
        raise ValueError(
            "transfer plan requires both BROKER_CONFIRMED and "
            "ICARUS_PAPER_EMULATOR in the study manifest"
        )

    created = _nonnegative_ns("created_time_ns", created_time_ns)
    if created < manifest.created_time_ns:
        raise ValueError(
            "transfer plan cannot predate manifest created_time_ns"
        )
    if created > manifest.cohort_start_ns:
        raise ValueError(
            "transfer plan must be created at or before cohort_start_ns"
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

    metric_values = _canonical_metrics(metrics)
    tolerance_values = _canonical_tolerances(
        metric_values,
        tolerances,
    )

    candidate = ImpactCalibrationTransferPlan(
        plan_id="",
        schema_version=PLAN_SCHEMA_VERSION,
        manifest_id=manifest.manifest_id,
        created_time_ns=created,
        confidence_alpha=alpha,
        bootstrap_replicates=reps,
        bootstrap_seed=seed,
        min_metric_observations_per_kind=minimum,
        metrics=metric_values,
        tolerances=tolerance_values,
    )
    return ImpactCalibrationTransferPlan(
        **{
            **candidate.__dict__,
            "plan_id": _digest(
                "impact-calibration-transfer-plan",
                _plan_payload(candidate),
            ),
        }
    )


def _validate_plan(
    plan: ImpactCalibrationTransferPlan,
    manifest: ImpactCalibrationStudyManifest,
) -> None:
    _validate_manifest(manifest)
    if not isinstance(plan, ImpactCalibrationTransferPlan):
        raise TypeError("plan must be ImpactCalibrationTransferPlan")
    if plan.schema_version != PLAN_SCHEMA_VERSION:
        raise ValueError("unsupported transfer plan schema_version")
    if plan.manifest_id != manifest.manifest_id:
        raise ValueError("transfer plan references a different manifest")
    if plan.execution_authorized or plan.production_decision_authorized:
        raise ValueError("transfer plan unexpectedly carries authority")

    required = {
        ExecutionEvidenceKind.BROKER_CONFIRMED,
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
    }
    if not required.issubset(set(manifest.evidence_kinds)):
        raise ValueError(
            "transfer plan requires both execution evidence kinds"
        )

    created = _nonnegative_ns("created_time_ns", plan.created_time_ns)
    if created < manifest.created_time_ns:
        raise ValueError("transfer plan predates manifest creation")
    if created > manifest.cohort_start_ns:
        raise ValueError("transfer plan creation is not prospective")

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

    metrics = _canonical_metrics(plan.metrics)
    if metrics != plan.metrics:
        raise ValueError("transfer plan metrics are not canonical")
    tolerance_map = dict(plan.tolerances)
    canonical_tolerances = _canonical_tolerances(
        plan.metrics,
        tolerance_map,
    )
    if canonical_tolerances != plan.tolerances:
        raise ValueError("transfer plan tolerances are not canonical")

    expected = _digest(
        "impact-calibration-transfer-plan",
        _plan_payload(plan),
    )
    if plan.plan_id != expected:
        raise ValueError("plan_id does not match transfer plan content")


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

    raise ValueError(f"unsupported transfer metric {metric!r}")


def _state(
    seed: int,
    evidence_kind: ExecutionEvidenceKind,
    metric: str,
    replicate: int,
) -> int:
    raw = (
        f"{seed}|transfer|{evidence_kind.value}|{metric}|{replicate}"
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
    metric: str,
    replicate: int,
) -> tuple[LineagedImpactCalibrationObservation, ...]:
    state = _state(
        seed,
        evidence_kind,
        metric,
        replicate,
    )
    out: list[LineagedImpactCalibrationObservation] = []
    size = len(rows)
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


def registered_transfer_compatibility(
    plan: ImpactCalibrationTransferPlan,
    manifest: ImpactCalibrationStudyManifest,
    cohort: ImpactCalibrationStudyCohort,
) -> TransferCompatibilityResult:
    """Compare paper and broker calibration strata without pooling them.

    The interval is a deterministic two-sample percentile bootstrap interval
    for paper minus broker. The within_tolerance field is a predeclared
    descriptive compatibility gate, not a hypothesis test or execution
    authorization.
    """

    _validate_plan(plan, manifest)

    # Revalidates the manifest, cohort, execution receipts, calibration
    # lineage, source revisions, timing constraints and authority flags.
    registered_evidence_stratified_summary(manifest, cohort)

    grouped: dict[
        ExecutionEvidenceKind,
        list[LineagedImpactCalibrationObservation],
    ] = {
        ExecutionEvidenceKind.BROKER_CONFIRMED: [],
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR: [],
    }
    for subject in cohort.subjects:
        kind = subject.row.receipt.evidence_kind
        if kind in grouped:
            grouped[kind].append(subject.row)

    tolerance_map = dict(plan.tolerances)
    results: list[TransferCompatibilityMetric] = []
    for metric in plan.metrics:
        broker = _eligible_rows(
            metric,
            tuple(grouped[ExecutionEvidenceKind.BROKER_CONFIRMED]),
        )
        paper = _eligible_rows(
            metric,
            tuple(grouped[ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR]),
        )
        minimum = plan.min_metric_observations_per_kind
        if len(broker) < minimum or len(paper) < minimum:
            raise ValueError(
                f"{metric} requires at least {minimum} eligible observations "
                "in both BROKER_CONFIRMED and ICARUS_PAPER_EMULATOR; "
                f"got broker={len(broker)}, paper={len(paper)}"
            )

        fn = _metric_function(metric)
        broker_estimate = float(fn(broker))
        paper_estimate = float(fn(paper))
        observed_gap = paper_estimate - broker_estimate

        bootstrap_gaps = tuple(
            sorted(
                float(
                    fn(
                        _resample(
                            paper,
                            seed=plan.bootstrap_seed,
                            evidence_kind=(
                                ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR
                            ),
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
                            metric=metric,
                            replicate=replicate,
                        )
                    )
                )
                for replicate in range(plan.bootstrap_replicates)
            )
        )

        lower = _percentile(
            bootstrap_gaps,
            plan.confidence_alpha / 2.0,
        )
        upper = _percentile(
            bootstrap_gaps,
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
                    f"transfer compatibility {name} is not finite"
                )

        tolerance = tolerance_map[metric]
        within = lower >= -tolerance and upper <= tolerance
        results.append(
            TransferCompatibilityMetric(
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

    metric_tuple = tuple(results)
    return TransferCompatibilityResult(
        plan_id=plan.plan_id,
        manifest_id=manifest.manifest_id,
        cohort_id=cohort.cohort_id,
        metrics=metric_tuple,
        all_within_tolerance=all(
            row.within_tolerance for row in metric_tuple
        ),
    )
