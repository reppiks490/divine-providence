from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Iterable

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


PLAN_SCHEMA_VERSION = "argus-impact-calibration-tail-transfer-plan-v1"

_ALLOWED_METRICS = {
    "slippage_error_ticks",
    "absolute_slippage_error_ticks",
}

_MIN_BOOTSTRAP_REPLICATES = 200
_MAX_BOOTSTRAP_REPLICATES = 10_000
_MAX_QUANTILES = 9
_MASK64 = (1 << 64) - 1
_LCG_MULT = 6364136223846793005
_LCG_INC = 1442695040888963407


@dataclass(frozen=True)
class ImpactCalibrationTailTransferPlan:
    plan_id: str
    schema_version: str
    manifest_id: str
    created_time_ns: int
    metric: str
    quantile_tolerances: tuple[tuple[float, float], ...]
    confidence_alpha: float
    bootstrap_replicates: int
    bootstrap_seed: int
    min_metric_observations_per_kind: int
    execution_authorized: bool = False
    production_decision_authorized: bool = False


@dataclass(frozen=True)
class TailTransferQuantileResult:
    quantile: float
    broker_quantile: float
    paper_quantile: float
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
    method: str = "deterministic_two_sample_quantile_percentile"


@dataclass(frozen=True)
class TailTransferCompatibilityResult:
    plan_id: str
    manifest_id: str
    cohort_id: str
    metric: str
    quantiles: tuple[TailTransferQuantileResult, ...]
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


def _quantile(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("quantile must be numeric")
    out = float(value)
    if not math.isfinite(out) or not 0.0 < out < 1.0:
        raise ValueError("quantile must be finite and strictly between 0 and 1")
    return out


def _canonical_quantile_tolerances(
    values: Iterable[tuple[float, float]],
) -> tuple[tuple[float, float], ...]:
    out: dict[float, float] = {}
    for item in values:
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError(
                "quantile_tolerances must contain (quantile, tolerance) tuples"
            )
        q = _quantile(item[0])
        tolerance = _finite_positive(
            f"tolerance[{q}]",
            item[1],
        )
        if q in out:
            raise ValueError("quantile_tolerances contain duplicate quantiles")
        out[q] = tolerance

    if not out:
        raise ValueError("at least one quantile tolerance is required")
    if len(out) > _MAX_QUANTILES:
        raise ValueError(
            f"at most {_MAX_QUANTILES} quantiles are allowed"
        )
    return tuple(sorted(out.items()))


def _plan_payload(
    plan: ImpactCalibrationTailTransferPlan,
) -> dict[str, Any]:
    return {
        "schema_version": plan.schema_version,
        "manifest_id": plan.manifest_id,
        "created_time_ns": plan.created_time_ns,
        "metric": plan.metric,
        "quantile_tolerances": plan.quantile_tolerances,
        "confidence_alpha": plan.confidence_alpha,
        "bootstrap_replicates": plan.bootstrap_replicates,
        "bootstrap_seed": plan.bootstrap_seed,
        "min_metric_observations_per_kind": (
            plan.min_metric_observations_per_kind
        ),
    }


def create_prospective_tail_transfer_plan(
    manifest: ImpactCalibrationStudyManifest,
    *,
    created_time_ns: int,
    metric: str,
    quantile_tolerances: Iterable[tuple[float, float]],
    confidence_alpha: float = 0.05,
    bootstrap_replicates: int = 2_000,
    bootstrap_seed: int = 0,
    min_metric_observations_per_kind: int = 3,
) -> ImpactCalibrationTailTransferPlan:
    """Pre-register tail compatibility between paper and broker calibration."""

    _validate_manifest(manifest)
    required = {
        ExecutionEvidenceKind.BROKER_CONFIRMED,
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
    }
    if not required.issubset(set(manifest.evidence_kinds)):
        raise ValueError(
            "tail transfer plan requires both BROKER_CONFIRMED and "
            "ICARUS_PAPER_EMULATOR in the study manifest"
        )

    created = _nonnegative_ns("created_time_ns", created_time_ns)
    if created > manifest.cohort_start_ns:
        raise ValueError(
            "tail transfer plan must be created at or before cohort_start_ns"
        )

    if not isinstance(metric, str) or metric not in _ALLOWED_METRICS:
        raise ValueError(
            f"unsupported tail transfer metric {metric!r}"
        )

    q_values = _canonical_quantile_tolerances(
        quantile_tolerances
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
    if minimum < 3:
        raise ValueError(
            "min_metric_observations_per_kind must be at least 3"
        )

    candidate = ImpactCalibrationTailTransferPlan(
        plan_id="",
        schema_version=PLAN_SCHEMA_VERSION,
        manifest_id=manifest.manifest_id,
        created_time_ns=created,
        metric=metric,
        quantile_tolerances=q_values,
        confidence_alpha=alpha,
        bootstrap_replicates=reps,
        bootstrap_seed=seed,
        min_metric_observations_per_kind=minimum,
    )
    return ImpactCalibrationTailTransferPlan(
        **{
            **candidate.__dict__,
            "plan_id": _digest(
                "impact-calibration-tail-transfer-plan",
                _plan_payload(candidate),
            ),
        }
    )


def _validate_plan(
    plan: ImpactCalibrationTailTransferPlan,
    manifest: ImpactCalibrationStudyManifest,
) -> None:
    _validate_manifest(manifest)
    if not isinstance(plan, ImpactCalibrationTailTransferPlan):
        raise TypeError("plan must be ImpactCalibrationTailTransferPlan")
    if plan.schema_version != PLAN_SCHEMA_VERSION:
        raise ValueError("unsupported tail transfer plan schema_version")
    if plan.manifest_id != manifest.manifest_id:
        raise ValueError("tail transfer plan references a different manifest")
    if plan.execution_authorized or plan.production_decision_authorized:
        raise ValueError("tail transfer plan unexpectedly carries authority")

    required = {
        ExecutionEvidenceKind.BROKER_CONFIRMED,
        ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR,
    }
    if not required.issubset(set(manifest.evidence_kinds)):
        raise ValueError(
            "tail transfer plan requires both execution evidence kinds"
        )

    created = _nonnegative_ns("created_time_ns", plan.created_time_ns)
    if created > manifest.cohort_start_ns:
        raise ValueError("tail transfer plan creation is not prospective")

    if plan.metric not in _ALLOWED_METRICS:
        raise ValueError("tail transfer metric is not supported")

    canonical_quantiles = _canonical_quantile_tolerances(
        plan.quantile_tolerances
    )
    if canonical_quantiles != plan.quantile_tolerances:
        raise ValueError(
            "tail transfer quantile tolerances are not canonical"
        )

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
    if minimum < 3:
        raise ValueError(
            "min_metric_observations_per_kind must be at least 3"
        )

    expected = _digest(
        "impact-calibration-tail-transfer-plan",
        _plan_payload(plan),
    )
    if plan.plan_id != expected:
        raise ValueError(
            "plan_id does not match tail transfer plan content"
        )


def _values(
    metric: str,
    rows: tuple[LineagedImpactCalibrationObservation, ...],
) -> tuple[float, ...]:
    values: list[float] = []
    for row in rows:
        error = row.calibration.slippage_error_ticks
        if error is None:
            continue
        value = float(error)
        if metric == "absolute_slippage_error_ticks":
            value = abs(value)
        if not math.isfinite(value):
            raise ValueError("tail transfer metric contains non-finite value")
        values.append(value)
    return tuple(values)


def _sample_quantile(
    values: tuple[float, ...],
    q: float,
) -> float:
    if not values:
        raise ValueError("quantile requires observations")
    ordered = tuple(sorted(values))
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lo = int(math.floor(position))
    hi = int(math.ceil(position))
    if lo == hi:
        return ordered[lo]
    weight = position - lo
    return ordered[lo] * (1.0 - weight) + ordered[hi] * weight


def _state(
    seed: int,
    evidence_kind: ExecutionEvidenceKind,
    metric: str,
    q: float,
    replicate: int,
) -> int:
    raw = (
        f"{seed}|tail-transfer|{evidence_kind.value}|"
        f"{metric}|{q:.17g}|{replicate}"
    ).encode("utf-8")
    return int.from_bytes(
        hashlib.sha256(raw).digest()[:8],
        "big",
    )


def _resample_values(
    values: tuple[float, ...],
    *,
    seed: int,
    evidence_kind: ExecutionEvidenceKind,
    metric: str,
    q: float,
    replicate: int,
) -> tuple[float, ...]:
    state = _state(
        seed,
        evidence_kind,
        metric,
        q,
        replicate,
    )
    size = len(values)
    out: list[float] = []
    for _ in range(size):
        state = (_LCG_MULT * state + _LCG_INC) & _MASK64
        out.append(values[state % size])
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


def registered_tail_transfer_compatibility(
    plan: ImpactCalibrationTailTransferPlan,
    manifest: ImpactCalibrationStudyManifest,
    cohort: ImpactCalibrationStudyCohort,
) -> TailTransferCompatibilityResult:
    """Audit upper/lower distributional transfer without pooling evidence."""

    _validate_plan(plan, manifest)

    # Revalidates study identity, execution receipts, calibration lineage,
    # source revisions, timing constraints and authority flags.
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

    broker = _values(
        plan.metric,
        tuple(grouped[ExecutionEvidenceKind.BROKER_CONFIRMED]),
    )
    paper = _values(
        plan.metric,
        tuple(grouped[ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR]),
    )

    minimum = plan.min_metric_observations_per_kind
    if len(broker) < minimum or len(paper) < minimum:
        raise ValueError(
            "tail transfer requires at least "
            f"{minimum} realized-slippage observations in both evidence kinds; "
            f"got broker={len(broker)}, paper={len(paper)}"
        )

    results: list[TailTransferQuantileResult] = []
    for q, tolerance in plan.quantile_tolerances:
        broker_q = _sample_quantile(broker, q)
        paper_q = _sample_quantile(paper, q)
        observed_gap = paper_q - broker_q

        gaps = tuple(
            sorted(
                _sample_quantile(
                    _resample_values(
                        paper,
                        seed=plan.bootstrap_seed,
                        evidence_kind=(
                            ExecutionEvidenceKind.ICARUS_PAPER_EMULATOR
                        ),
                        metric=plan.metric,
                        q=q,
                        replicate=replicate,
                    ),
                    q,
                )
                - _sample_quantile(
                    _resample_values(
                        broker,
                        seed=plan.bootstrap_seed,
                        evidence_kind=(
                            ExecutionEvidenceKind.BROKER_CONFIRMED
                        ),
                        metric=plan.metric,
                        q=q,
                        replicate=replicate,
                    ),
                    q,
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
            ("broker_quantile", broker_q),
            ("paper_quantile", paper_q),
            ("paper_minus_broker", observed_gap),
            ("lower", lower),
            ("upper", upper),
        ):
            if not math.isfinite(value):
                raise ValueError(
                    f"tail transfer {name} is not finite"
                )

        within = lower >= -tolerance and upper <= tolerance
        results.append(
            TailTransferQuantileResult(
                quantile=q,
                broker_quantile=broker_q,
                paper_quantile=paper_q,
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
    return TailTransferCompatibilityResult(
        plan_id=plan.plan_id,
        manifest_id=manifest.manifest_id,
        cohort_id=cohort.cohort_id,
        metric=plan.metric,
        quantiles=result_tuple,
        all_within_tolerance=all(
            row.within_tolerance for row in result_tuple
        ),
    )
