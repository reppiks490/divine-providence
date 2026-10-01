from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable

from .contracts import EvidenceTier
from .orderblock_lifecycle import OrderBlockLifecycle, OrderBlockState


@dataclass(frozen=True)
class OrderBlockSurvivalRecord:
    block_id: str
    direction: int
    evidence_tier: EvidenceTier
    duration_ns: int
    invalidated: bool
    test_count: int
    rejection_count: int
    max_penetration_fraction: float
    terminal_state: OrderBlockState


@dataclass(frozen=True)
class KaplanMeierPoint:
    duration_ns: int
    at_risk: int
    invalidations: int
    censored: int
    survival_probability: float


@dataclass(frozen=True)
class KaplanMeierCurve:
    records: int
    invalidations: int
    censored: int
    points: tuple[KaplanMeierPoint, ...]
    median_survival_ns: int | None
    restricted_mean_survival_ns: float


@dataclass(frozen=True)
class SurvivalStratum:
    label: str
    curve: KaplanMeierCurve


def record_from_lifecycle(
    lifecycle: OrderBlockLifecycle,
) -> OrderBlockSurvivalRecord:
    """Convert one terminal confirmed lifecycle into a survival-study record."""

    if not isinstance(lifecycle, OrderBlockLifecycle):
        raise TypeError("lifecycle must be OrderBlockLifecycle")
    if lifecycle.state not in (
        OrderBlockState.INVALIDATED,
        OrderBlockState.EXPIRED,
    ):
        raise ValueError("survival record requires a terminal lifecycle")
    if lifecycle.confirmation_time_ns is None:
        raise ValueError("survival record requires a confirmed lifecycle")
    if lifecycle.last_event_time_ns < lifecycle.confirmation_time_ns:
        raise ValueError("terminal time cannot precede confirmation")

    return OrderBlockSurvivalRecord(
        block_id=lifecycle.block_id,
        direction=lifecycle.candidate.direction,
        evidence_tier=lifecycle.candidate.evidence_tier,
        duration_ns=lifecycle.last_event_time_ns - lifecycle.confirmation_time_ns,
        invalidated=lifecycle.state is OrderBlockState.INVALIDATED,
        test_count=lifecycle.test_count,
        rejection_count=lifecycle.rejection_count,
        max_penetration_fraction=lifecycle.max_penetration_fraction,
        terminal_state=lifecycle.state,
    )


def _validated_records(
    records: Iterable[OrderBlockSurvivalRecord],
) -> tuple[OrderBlockSurvivalRecord, ...]:
    rows = tuple(records)
    if not rows:
        raise ValueError("at least one survival record is required")

    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, OrderBlockSurvivalRecord):
            raise TypeError("records must contain OrderBlockSurvivalRecord values")
        if not row.block_id:
            raise ValueError("block_id is required")
        if row.block_id in seen:
            raise ValueError("duplicate block_id in survival study")
        seen.add(row.block_id)

        if isinstance(row.duration_ns, bool) or not isinstance(row.duration_ns, int) or row.duration_ns < 0:
            raise ValueError("duration_ns must be a non-negative integer")
        if isinstance(row.direction, bool) or row.direction not in (-1, 1):
            raise ValueError("direction must be +/-1")
        if not isinstance(row.evidence_tier, EvidenceTier):
            raise TypeError("evidence_tier must be EvidenceTier")
        if type(row.invalidated) is not bool:
            raise TypeError("invalidated must be bool")
        if (
            isinstance(row.test_count, bool)
            or not isinstance(row.test_count, int)
            or row.test_count < 0
        ):
            raise ValueError("test_count must be a non-negative integer")
        if (
            isinstance(row.rejection_count, bool)
            or not isinstance(row.rejection_count, int)
            or row.rejection_count < 0
            or row.rejection_count > row.test_count
        ):
            raise ValueError("rejection_count must be in [0, test_count]")
        if (
            isinstance(row.max_penetration_fraction, bool)
            or not isinstance(row.max_penetration_fraction, (int, float))
            or not math.isfinite(float(row.max_penetration_fraction))
            or float(row.max_penetration_fraction) < 0
        ):
            raise ValueError("max_penetration_fraction must be finite and non-negative")
        expected_state = (
            OrderBlockState.INVALIDATED
            if row.invalidated
            else OrderBlockState.EXPIRED
        )
        if row.terminal_state is not expected_state:
            raise ValueError("terminal_state does not match invalidated flag")

    return rows


def kaplan_meier(
    records: Iterable[OrderBlockSurvivalRecord],
) -> KaplanMeierCurve:
    """Estimate block survival with invalidation as event and expiry as censoring.

    This is retrospective descriptive research. It does not estimate a trading
    return, causal treatment effect, or production probability.
    """

    rows = _validated_records(records)
    by_time: dict[int, list[OrderBlockSurvivalRecord]] = {}
    for row in rows:
        by_time.setdefault(row.duration_ns, []).append(row)

    survival = 1.0
    points: list[KaplanMeierPoint] = []
    median: int | None = None
    rmst = 0.0
    previous_time = 0
    previous_survival = 1.0

    for duration in sorted(by_time):
        rmst += previous_survival * (duration - previous_time)
        group = by_time[duration]
        at_risk = sum(1 for row in rows if row.duration_ns >= duration)
        invalidations = sum(1 for row in group if row.invalidated)
        censored = len(group) - invalidations

        if at_risk <= 0:
            raise ValueError("invalid at-risk set")
        if invalidations:
            survival *= 1.0 - (invalidations / at_risk)

        point = KaplanMeierPoint(
            duration_ns=duration,
            at_risk=at_risk,
            invalidations=invalidations,
            censored=censored,
            survival_probability=survival,
        )
        points.append(point)
        if median is None and survival <= 0.5:
            median = duration

        previous_time = duration
        previous_survival = survival

    return KaplanMeierCurve(
        records=len(rows),
        invalidations=sum(1 for row in rows if row.invalidated),
        censored=sum(1 for row in rows if not row.invalidated),
        points=tuple(points),
        median_survival_ns=median,
        restricted_mean_survival_ns=rmst,
    )


def survival_probability_at(
    curve: KaplanMeierCurve,
    *,
    duration_ns: int,
) -> float:
    if not isinstance(curve, KaplanMeierCurve):
        raise TypeError("curve must be KaplanMeierCurve")
    if isinstance(duration_ns, bool) or not isinstance(duration_ns, int) or duration_ns < 0:
        raise ValueError("duration_ns must be a non-negative integer")

    probability = 1.0
    for point in curve.points:
        if point.duration_ns > duration_ns:
            break
        probability = point.survival_probability
    return probability


def survival_by_evidence_tier(
    records: Iterable[OrderBlockSurvivalRecord],
) -> tuple[SurvivalStratum, ...]:
    rows = _validated_records(records)
    strata: list[SurvivalStratum] = []
    for tier in EvidenceTier:
        selected = tuple(row for row in rows if row.evidence_tier is tier)
        if selected:
            strata.append(
                SurvivalStratum(
                    label=tier.name,
                    curve=kaplan_meier(selected),
                )
            )
    return tuple(strata)


def survival_by_test_count(
    records: Iterable[OrderBlockSurvivalRecord],
) -> tuple[SurvivalStratum, ...]:
    """Retrospective terminal stratification by final test count.

    This grouping uses final lifecycle information and therefore must not be
    interpreted as an ex-ante predictor without separate causal validation.
    """

    rows = _validated_records(records)
    groups = (
        ("tests=0", lambda row: row.test_count == 0),
        ("tests=1", lambda row: row.test_count == 1),
        ("tests>=2", lambda row: row.test_count >= 2),
    )
    strata: list[SurvivalStratum] = []
    for label, predicate in groups:
        selected = tuple(row for row in rows if predicate(row))
        if selected:
            strata.append(
                SurvivalStratum(
                    label=label,
                    curve=kaplan_meier(selected),
                )
            )
    return tuple(strata)
