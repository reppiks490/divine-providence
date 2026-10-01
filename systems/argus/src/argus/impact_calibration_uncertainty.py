from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Callable, Iterable

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


PLAN_SCHEMA_VERSION = "argus-impact-calibration-bootstrap-plan-v1"

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
class ImpactCalibrationBootstrapPlan:
    plan_id: str
    schema_version: str
    manifest_id: str
    created_time_ns: int
    confidence_alpha: float
    bootstrap_replicates: int
    bootstrap_seed: int
    min_metric_observations: int
    metrics: tuple[str, ...]
    execution_authorized: bool = False
    production_decision_authorized: bool = False


@dataclass(frozen=True)
class BootstrapInterval:
    metric: str
    estimate: float
    lower: float
    upper: float
    confidence_level: float
    alpha: float
    sample_size: int
    bootstrap_replicates: int
    method: str = "deterministic_nonparametric_percentile"


@dataclass(frozen=True)
class EvidenceStratumBootstrapUncertainty:
    evidence_kind: ExecutionEvidenceKind
    market_fill_confirmed: bool
    broker_confirmed: bool
    observations: int
    intervals: tuple[BootstrapInterval, ...]
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


def _alpha(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("confidence_alpha must be numeric")
    out = float(value)
    if not math.isfinite(out) or not 0.0 < out < 1.0:
        raise ValueError(
            "confidence_alpha must be finite and strictly between 0 and 1"
        )
    return out


def _plan_payload(plan: ImpactCalibrationBootstrapPlan) -> dict[str, Any]:
    return {
        "schema_version": plan.schema_version,
        "manifest_id": plan.manifest_id,
        "created_time_ns": plan.created_time_ns,
        "confidence_alpha": plan.confidence_alpha,
        "bootstrap_replicates": plan.bootstrap_replicates,
        "bootstrap_seed": plan.bootstrap_seed,
        "min_metric_observations": plan.min_metric_observations,
        "metrics": plan.metrics,
    }


def create_prospective_bootstrap_plan(
    manifest: ImpactCalibrationStudyManifest,
    *,
    created_time_ns: int,
    confidence_alpha: float = 0.05,
    bootstrap_replicates: int = 2_000,
    bootstrap_seed: int = 0,
    min_metric_observations: int = 2,
    metrics: Iterable[str] = (
        "mean_fill_fraction_error",
        "mean_absolute_fill_fraction_error",
        "mean_slippage_error_ticks",
        "mean_absolute_slippage_error_ticks",
        "root_mean_squared_slippage_error_ticks",
        "slippage_underprediction_rate",
    ),
) -> ImpactCalibrationBootstrapPlan:
    """Register a deterministic bootstrap addendum before the cohort starts."""

    _validate_manifest(manifest)
    created = _nonnegative_ns("created_time_ns", created_time_ns)
    if created > manifest.cohort_start_ns:
        raise ValueError(
            "bootstrap plan must be created at or before cohort_start_ns"
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
        "min_metric_observations",
        min_metric_observations,
    )
    if minimum < 2:
        raise ValueError(
            "min_metric_observations must be at least 2"
        )

    metric_values = tuple(sorted(set(metrics)))
    if not metric_values:
        raise ValueError("at least one bootstrap metric is required")
    if any(
        not isinstance(metric, str) or not metric.strip()
        for metric in metric_values
    ):
        raise ValueError("bootstrap metric names must be non-empty strings")
    unknown = set(metric_values) - _ALLOWED_METRICS
    if unknown:
        raise ValueError(
            f"unsupported bootstrap metrics: {sorted(unknown)}"
        )

    candidate = ImpactCalibrationBootstrapPlan(
        plan_id="",
        schema_version=PLAN_SCHEMA_VERSION,
        manifest_id=manifest.manifest_id,
        created_time_ns=created,
        confidence_alpha=alpha,
        bootstrap_replicates=reps,
        bootstrap_seed=seed,
        min_metric_observations=minimum,
        metrics=metric_values,
    )
    return ImpactCalibrationBootstrapPlan(
        **{
            **candidate.__dict__,
            "plan_id": _digest(
                "impact-calibration-bootstrap-plan",
                _plan_payload(candidate),
            ),
        }
    )


def _validate_plan(
    plan: ImpactCalibrationBootstrapPlan,
    manifest: ImpactCalibrationStudyManifest,
) -> None:
    _validate_manifest(manifest)
    if not isinstance(plan, ImpactCalibrationBootstrapPlan):
        raise TypeError("plan must be ImpactCalibrationBootstrapPlan")
    if plan.schema_version != PLAN_SCHEMA_VERSION:
        raise ValueError("unsupported bootstrap plan schema_version")
    if plan.manifest_id != manifest.manifest_id:
        raise ValueError("bootstrap plan references a different manifest")
    if plan.execution_authorized or plan.production_decision_authorized:
        raise ValueError("bootstrap plan unexpectedly carries authority")

    created = _nonnegative_ns("created_time_ns", plan.created_time_ns)
    if created > manifest.cohort_start_ns:
        raise ValueError("bootstrap plan creation is not prospective")

    _alpha(plan.confidence_alpha)
    reps = _positive_int(
        "bootstrap_replicates",
        plan.bootstrap_replicates,
    )
    if not _MIN_BOOTSTRAP_REPLICATES <= reps <= _MAX_BOOTSTRAP_REPLICATES:
        raise ValueError("bootstrap_replicates is outside schema limits")

    _nonnegative_ns("bootstrap_seed", plan.bootstrap_seed)
    minimum = _positive_int(
        "min_metric_observations",
        plan.min_metric_observations,
    )
    if minimum < 2:
        raise ValueError("min_metric_observations must be at least 2")

    if (
        not plan.metrics
        or plan.metrics != tuple(sorted(set(plan.metrics)))
        or set(plan.metrics) - _ALLOWED_METRICS
    ):
        raise ValueError("bootstrap plan metrics are not canonical")

    expected = _digest(
        "impact-calibration-bootstrap-plan",
        _plan_payload(plan),
    )
    if plan.plan_id != expected:
        raise ValueError("plan_id does not match bootstrap plan content")


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

    raise ValueError(f"unsupported bootstrap metric {metric!r}")


def _replicate_state(
    seed: int,
    evidence_kind: ExecutionEvidenceKind,
    metric: str,
    replicate: int,
) -> int:
    raw = (
        f"{seed}|{evidence_kind.value}|{metric}|{replicate}"
    ).encode("utf-8")
    return int.from_bytes(
        hashlib.sha256(raw).digest()[:8],
        "big",
    )


def _bootstrap_sample(
    rows: tuple[LineagedImpactCalibrationObservation, ...],
    *,
    seed: int,
    evidence_kind: ExecutionEvidenceKind,
    metric: str,
    replicate: int,
) -> tuple[LineagedImpactCalibrationObservation, ...]:
    state = _replicate_state(
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


def _interval(
    plan: ImpactCalibrationBootstrapPlan,
    evidence_kind: ExecutionEvidenceKind,
    metric: str,
    rows: tuple[LineagedImpactCalibrationObservation, ...],
) -> BootstrapInterval:
    eligible = _eligible_rows(metric, rows)
    if len(eligible) < plan.min_metric_observations:
        raise ValueError(
            f"{evidence_kind.value} {metric} has "
            f"{len(eligible)} eligible observations; "
            f"requires {plan.min_metric_observations}"
        )

    fn = _metric_function(metric)
    estimate = float(fn(eligible))
    values = tuple(
        sorted(
            float(
                fn(
                    _bootstrap_sample(
                        eligible,
                        seed=plan.bootstrap_seed,
                        evidence_kind=evidence_kind,
                        metric=metric,
                        replicate=replicate,
                    )
                )
            )
            for replicate in range(plan.bootstrap_replicates)
        )
    )

    lower = _percentile(values, plan.confidence_alpha / 2.0)
    upper = _percentile(
        values,
        1.0 - plan.confidence_alpha / 2.0,
    )
    for name, value in (
        ("estimate", estimate),
        ("lower", lower),
        ("upper", upper),
    ):
        if not math.isfinite(value):
            raise ValueError(f"bootstrap {name} is not finite")

    return BootstrapInterval(
        metric=metric,
        estimate=estimate,
        lower=lower,
        upper=upper,
        confidence_level=1.0 - plan.confidence_alpha,
        alpha=plan.confidence_alpha,
        sample_size=len(eligible),
        bootstrap_replicates=plan.bootstrap_replicates,
    )


def registered_bootstrap_uncertainty(
    plan: ImpactCalibrationBootstrapPlan,
    manifest: ImpactCalibrationStudyManifest,
    cohort: ImpactCalibrationStudyCohort,
) -> tuple[EvidenceStratumBootstrapUncertainty, ...]:
    """Run the prospective deterministic bootstrap addendum.

    Intervals are descriptive nonparametric percentile intervals. They are not
    hypothesis tests, simultaneous bands, or production decision authority.
    """

    _validate_plan(plan, manifest)

    # Revalidates the manifest, cohort, execution receipts, calibration lineage,
    # source revisions, timing limits, stratum minimums and authority flags.
    registered_evidence_stratified_summary(manifest, cohort)

    grouped: dict[
        ExecutionEvidenceKind,
        list[LineagedImpactCalibrationObservation],
    ] = {
        kind: [] for kind in manifest.evidence_kinds
    }
    for subject in cohort.subjects:
        grouped[subject.row.receipt.evidence_kind].append(subject.row)

    out: list[EvidenceStratumBootstrapUncertainty] = []
    for kind in manifest.evidence_kinds:
        rows = tuple(grouped[kind])
        intervals = tuple(
            _interval(plan, kind, metric, rows)
            for metric in plan.metrics
        )
        confirmed = kind is ExecutionEvidenceKind.BROKER_CONFIRMED
        out.append(
            EvidenceStratumBootstrapUncertainty(
                evidence_kind=kind,
                market_fill_confirmed=confirmed,
                broker_confirmed=confirmed,
                observations=len(rows),
                intervals=intervals,
            )
        )
    return tuple(out)
