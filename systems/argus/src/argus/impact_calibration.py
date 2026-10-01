from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from .contracts import EvidenceTier
from .impact import DepthImpactCurve, DepthImpactPoint


@dataclass(frozen=True)
class RealizedExecution:
    execution_id: str
    decision_time_ns: int
    completion_time_ns: int
    side: int
    requested_size: float
    filled_size: float
    average_price: float | None


@dataclass(frozen=True)
class ImpactCalibrationObservation:
    execution_id: str
    curve_event_time_ns: int
    curve_sequence: int
    side: int
    requested_size: float
    visible_opposite_size: float
    requested_to_visible_ratio: float
    snapshot_age_ns: int
    completion_latency_ns: int
    predicted_fill_fraction: float
    realized_fill_fraction: float
    fill_fraction_error: float
    predicted_average_slippage_ticks: float
    realized_average_slippage_ticks: float | None
    slippage_error_ticks: float | None
    absolute_slippage_error_ticks: float | None
    underpredicted_slippage: bool | None
    predicted_book_exhausted: bool
    realized_complete_fill: bool
    evidence_tier: EvidenceTier = EvidenceTier.TRUE_DEPTH
    assumption: str = "static_visible_depth_only"
    execution_authorized: bool = False
    production_decision_authorized: bool = False


@dataclass(frozen=True)
class ImpactCalibrationSummary:
    observations: int
    realized_fill_observations: int
    complete_fill_observations: int
    mean_snapshot_age_ns: float
    mean_completion_latency_ns: float
    mean_fill_fraction_error: float
    mean_absolute_fill_fraction_error: float
    slippage_observations: int
    mean_slippage_error_ticks: float | None
    mean_absolute_slippage_error_ticks: float | None
    root_mean_squared_slippage_error_ticks: float | None
    slippage_underprediction_rate: float | None
    execution_authorized: bool = False
    production_decision_authorized: bool = False


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite")
    return out


def _positive(name: str, value: float) -> float:
    out = _finite(name, value)
    if out <= 0:
        raise ValueError(f"{name} must be positive")
    return out


def _nonnegative(name: str, value: float) -> float:
    out = _finite(name, value)
    if out < 0:
        raise ValueError(f"{name} must be non-negative")
    return out


def _nonnegative_ns(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _canonical_id(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{name} must not contain surrounding whitespace")
    return value


def _close(left: float, right: float, *, abs_tol: float = 1e-9) -> bool:
    return math.isclose(left, right, rel_tol=1e-12, abs_tol=abs_tol)


def _validate_point(
    point: DepthImpactPoint,
    *,
    curve: DepthImpactCurve,
    previous_size: float | None,
) -> float:
    if not isinstance(point, DepthImpactPoint):
        raise TypeError("curve points must be DepthImpactPoint values")

    requested = _positive("point requested_size", point.requested_size)
    filled = _nonnegative("point filled_size", point.filled_size)
    fill_fraction = _nonnegative("point fill_fraction", point.fill_fraction)
    if fill_fraction > 1.0:
        raise ValueError("point fill_fraction cannot exceed 1")
    if filled > requested + 1e-9:
        raise ValueError("point filled_size cannot exceed requested_size")
    if previous_size is not None and requested <= previous_size:
        raise ValueError("curve requested sizes must be strictly increasing")
    if not _close(fill_fraction, filled / requested):
        raise ValueError("point fill_fraction is inconsistent")

    if filled > curve.visible_opposite_size + 1e-9:
        raise ValueError("point filled_size exceeds visible opposite depth")

    if filled == 0:
        if point.average_price is not None or point.marginal_price is not None:
            raise ValueError("unfilled point cannot carry fill prices")
        if point.average_slippage_ticks_from_best is not None:
            raise ValueError("unfilled point cannot carry average slippage")
    else:
        average = _positive("point average_price", point.average_price)
        marginal = _positive("point marginal_price", point.marginal_price)
        best = curve.best_ask if curve.side == 1 else curve.best_bid
        expected_slippage = ((average - best) * curve.side) / curve.tick_size
        if point.average_slippage_ticks_from_best is None or not _close(
            float(point.average_slippage_ticks_from_best),
            expected_slippage,
        ):
            raise ValueError("point average slippage is inconsistent")
        expected_marginal = ((marginal - best) * curve.side) / curve.tick_size
        if (
            point.marginal_displacement_ticks_from_best is None
            or not _close(
                float(point.marginal_displacement_ticks_from_best),
                expected_marginal,
            )
        ):
            raise ValueError("point marginal displacement is inconsistent")
        expected_mid = ((average - curve.midprice) * curve.side) / curve.tick_size
        if (
            point.implementation_shortfall_ticks_from_mid is None
            or not _close(
                float(point.implementation_shortfall_ticks_from_mid),
                expected_mid,
            )
        ):
            raise ValueError("point midprice shortfall is inconsistent")
        expected_micro = (
            (average - curve.microprice) * curve.side / curve.tick_size
        )
        if (
            point.implementation_shortfall_ticks_from_microprice is None
            or not _close(
                float(point.implementation_shortfall_ticks_from_microprice),
                expected_micro,
            )
        ):
            raise ValueError("point microprice shortfall is inconsistent")

    if type(point.book_exhausted) is not bool:
        raise TypeError("point book_exhausted must be bool")
    if point.book_exhausted and filled >= requested - 1e-9:
        raise ValueError("book_exhausted point must be partially filled")
    if not point.book_exhausted and filled < requested - 1e-9:
        raise ValueError("partial fill must mark book_exhausted")

    if (
        isinstance(point.consumed_levels, bool)
        or not isinstance(point.consumed_levels, int)
        or point.consumed_levels < 0
    ):
        raise ValueError("point consumed_levels must be a non-negative integer")

    return requested


def _validate_curve(curve: DepthImpactCurve) -> None:
    if not isinstance(curve, DepthImpactCurve):
        raise TypeError("curve must be DepthImpactCurve")
    _nonnegative_ns("curve event_time_ns", curve.event_time_ns)
    _nonnegative_ns("curve sequence", curve.sequence)
    if isinstance(curve.side, bool) or curve.side not in (-1, 1):
        raise ValueError("curve side must be +/-1")
    tick = _positive("curve tick_size", curve.tick_size)
    best_bid = _positive("curve best_bid", curve.best_bid)
    best_ask = _positive("curve best_ask", curve.best_ask)
    if best_bid >= best_ask:
        raise ValueError("curve best_bid must be below best_ask")

    expected_spread = (best_ask - best_bid) / tick
    if not _close(_nonnegative("curve spread_ticks", curve.spread_ticks), expected_spread):
        raise ValueError("curve spread_ticks is inconsistent")
    expected_mid = (best_bid + best_ask) / 2.0
    if not _close(_positive("curve midprice", curve.midprice), expected_mid):
        raise ValueError("curve midprice is inconsistent")
    micro = _positive("curve microprice", curve.microprice)
    if not best_bid <= micro <= best_ask:
        raise ValueError("curve microprice must remain inside the spread")
    _positive("curve visible_opposite_size", curve.visible_opposite_size)

    if curve.evidence_tier is not EvidenceTier.TRUE_DEPTH:
        raise ValueError("impact calibration requires TRUE_DEPTH")
    if curve.assumption != "static_visible_depth_only":
        raise ValueError("unsupported impact-curve assumption")
    if curve.execution_authorized or curve.production_decision_authorized:
        raise ValueError("impact curve unexpectedly carries authority")
    if not curve.points:
        raise ValueError("impact curve points are required")

    previous_size: float | None = None
    for point in curve.points:
        previous_size = _validate_point(
            point,
            curve=curve,
            previous_size=previous_size,
        )

    previous_threshold: float | None = None
    previous_capacity = -1.0
    for threshold, capacity in curve.capacity_at_marginal_ticks:
        threshold_value = _nonnegative("capacity threshold", threshold)
        capacity_value = _nonnegative("capacity value", capacity)
        if (
            previous_threshold is not None
            and threshold_value <= previous_threshold
        ):
            raise ValueError("capacity thresholds must be strictly increasing")
        if capacity_value + 1e-9 < previous_capacity:
            raise ValueError("displayed capacity cannot decrease with threshold")
        if capacity_value > curve.visible_opposite_size + 1e-9:
            raise ValueError("capacity exceeds visible opposite depth")
        previous_threshold = threshold_value
        previous_capacity = capacity_value


def _validate_execution(execution: RealizedExecution) -> None:
    if not isinstance(execution, RealizedExecution):
        raise TypeError("execution must be RealizedExecution")
    _canonical_id("execution_id", execution.execution_id)
    decision = _nonnegative_ns("decision_time_ns", execution.decision_time_ns)
    completion = _nonnegative_ns(
        "completion_time_ns",
        execution.completion_time_ns,
    )
    if completion < decision:
        raise ValueError("completion_time_ns cannot precede decision_time_ns")
    if isinstance(execution.side, bool) or execution.side not in (-1, 1):
        raise ValueError("execution side must be +/-1")

    requested = _positive("requested_size", execution.requested_size)
    filled = _nonnegative("filled_size", execution.filled_size)
    if filled > requested + 1e-9:
        raise ValueError("filled_size cannot exceed requested_size")

    if filled == 0:
        if execution.average_price is not None:
            raise ValueError("zero-fill execution cannot carry average_price")
    else:
        _positive("average_price", execution.average_price)


def _matching_point(
    curve: DepthImpactCurve,
    requested_size: float,
) -> DepthImpactPoint:
    matches = [
        point
        for point in curve.points
        if _close(point.requested_size, requested_size)
    ]
    if len(matches) != 1:
        raise ValueError(
            "realized requested_size must match exactly one impact-curve point"
        )
    return matches[0]


def calibrate_impact(
    curve: DepthImpactCurve,
    execution: RealizedExecution,
) -> ImpactCalibrationObservation:
    """Compare one static TRUE_DEPTH prediction with one later realized fill.

    This is retrospective calibration evidence only. The realized fill is
    deliberately required to occur at/after the snapshot and is never fed back
    into the prediction being evaluated.
    """

    _validate_curve(curve)
    _validate_execution(execution)

    if execution.side != curve.side:
        raise ValueError("execution side does not match impact curve")
    if execution.decision_time_ns < curve.event_time_ns:
        raise ValueError("execution decision cannot precede impact snapshot")

    point = _matching_point(curve, execution.requested_size)
    best = curve.best_ask if curve.side == 1 else curve.best_bid

    predicted_slippage = point.average_slippage_ticks_from_best
    if predicted_slippage is None:
        raise ValueError("validated impact point unexpectedly lacks slippage")

    realized_fraction = execution.filled_size / execution.requested_size
    realized_slippage: float | None = None
    slippage_error: float | None = None
    absolute_slippage_error: float | None = None
    underpredicted: bool | None = None

    if execution.filled_size > 0:
        average = float(execution.average_price)
        realized_slippage = (
            (average - best) * execution.side / curve.tick_size
        )
        slippage_error = realized_slippage - float(predicted_slippage)
        absolute_slippage_error = abs(slippage_error)
        underpredicted = slippage_error > 1e-12

    return ImpactCalibrationObservation(
        execution_id=execution.execution_id,
        curve_event_time_ns=curve.event_time_ns,
        curve_sequence=curve.sequence,
        side=curve.side,
        requested_size=execution.requested_size,
        visible_opposite_size=curve.visible_opposite_size,
        requested_to_visible_ratio=(
            execution.requested_size / curve.visible_opposite_size
        ),
        snapshot_age_ns=execution.decision_time_ns - curve.event_time_ns,
        completion_latency_ns=(
            execution.completion_time_ns - execution.decision_time_ns
        ),
        predicted_fill_fraction=point.fill_fraction,
        realized_fill_fraction=realized_fraction,
        fill_fraction_error=realized_fraction - point.fill_fraction,
        predicted_average_slippage_ticks=float(predicted_slippage),
        realized_average_slippage_ticks=realized_slippage,
        slippage_error_ticks=slippage_error,
        absolute_slippage_error_ticks=absolute_slippage_error,
        underpredicted_slippage=underpredicted,
        predicted_book_exhausted=point.book_exhausted,
        realized_complete_fill=_close(
            execution.filled_size,
            execution.requested_size,
        ),
    )


def summarize_impact_calibration(
    observations: Iterable[ImpactCalibrationObservation],
) -> ImpactCalibrationSummary:
    """Aggregate retrospective calibration error without producing a trade score."""

    rows = tuple(observations)
    if not rows:
        raise ValueError("at least one calibration observation is required")

    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, ImpactCalibrationObservation):
            raise TypeError(
                "observations must contain ImpactCalibrationObservation values"
            )
        if row.execution_id in seen:
            raise ValueError("duplicate execution_id in calibration summary")
        seen.add(row.execution_id)
        if row.evidence_tier is not EvidenceTier.TRUE_DEPTH:
            raise ValueError("calibration observation lost TRUE_DEPTH evidence")
        if row.assumption != "static_visible_depth_only":
            raise ValueError("unsupported calibration assumption")
        if row.execution_authorized or row.production_decision_authorized:
            raise ValueError("calibration observation unexpectedly carries authority")

    fill_errors = [row.fill_fraction_error for row in rows]
    slippage_errors = [
        row.slippage_error_ticks
        for row in rows
        if row.slippage_error_ticks is not None
    ]

    mean_slippage: float | None = None
    mae_slippage: float | None = None
    rmse_slippage: float | None = None
    underprediction_rate: float | None = None
    if slippage_errors:
        mean_slippage = sum(slippage_errors) / len(slippage_errors)
        mae_slippage = (
            sum(abs(value) for value in slippage_errors)
            / len(slippage_errors)
        )
        rmse_slippage = math.sqrt(
            sum(value * value for value in slippage_errors)
            / len(slippage_errors)
        )
        underprediction_rate = (
            sum(
                1
                for row in rows
                if row.underpredicted_slippage is True
            )
            / len(slippage_errors)
        )

    return ImpactCalibrationSummary(
        observations=len(rows),
        realized_fill_observations=len(slippage_errors),
        complete_fill_observations=sum(
            1 for row in rows if row.realized_complete_fill
        ),
        mean_snapshot_age_ns=sum(row.snapshot_age_ns for row in rows) / len(rows),
        mean_completion_latency_ns=(
            sum(row.completion_latency_ns for row in rows) / len(rows)
        ),
        mean_fill_fraction_error=sum(fill_errors) / len(fill_errors),
        mean_absolute_fill_fraction_error=(
            sum(abs(value) for value in fill_errors) / len(fill_errors)
        ),
        slippage_observations=len(slippage_errors),
        mean_slippage_error_ticks=mean_slippage,
        mean_absolute_slippage_error_ticks=mae_slippage,
        root_mean_squared_slippage_error_ticks=rmse_slippage,
        slippage_underprediction_rate=underprediction_rate,
    )
