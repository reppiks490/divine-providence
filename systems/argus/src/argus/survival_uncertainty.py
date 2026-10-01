from __future__ import annotations

from dataclasses import dataclass
import math
from statistics import NormalDist

from .orderblock_survival import KaplanMeierCurve, KaplanMeierPoint


@dataclass(frozen=True)
class SurvivalUncertaintyPoint:
    duration_ns: int
    at_risk: int
    invalidations: int
    censored: int
    survival_probability: float
    greenwood_variance: float
    standard_error: float
    lower_confidence: float
    upper_confidence: float
    cumulative_hazard: float


@dataclass(frozen=True)
class SurvivalUncertaintyBand:
    alpha: float
    confidence_level: float
    records: int
    invalidations: int
    censored: int
    points: tuple[SurvivalUncertaintyPoint, ...]


def _probability(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    out = float(value)
    if not math.isfinite(out) or not 0.0 <= out <= 1.0:
        raise ValueError(f"{name} must be finite and in [0, 1]")
    return out


def _validate_curve(curve: KaplanMeierCurve) -> None:
    if not isinstance(curve, KaplanMeierCurve):
        raise TypeError("curve must be KaplanMeierCurve")
    if (
        isinstance(curve.records, bool)
        or not isinstance(curve.records, int)
        or curve.records <= 0
    ):
        raise ValueError("curve records must be a positive integer")
    if (
        isinstance(curve.invalidations, bool)
        or not isinstance(curve.invalidations, int)
        or curve.invalidations < 0
    ):
        raise ValueError("curve invalidations must be a non-negative integer")
    if (
        isinstance(curve.censored, bool)
        or not isinstance(curve.censored, int)
        or curve.censored < 0
    ):
        raise ValueError("curve censored must be a non-negative integer")
    if curve.invalidations + curve.censored != curve.records:
        raise ValueError("curve event and censor counts must equal records")
    if not curve.points:
        raise ValueError("curve points are required")

    expected_at_risk = curve.records
    previous_duration: int | None = None
    previous_survival = 1.0
    invalidations_total = 0
    censored_total = 0
    expected_median: int | None = None
    expected_rmst = 0.0
    previous_time = 0
    previous_step_survival = 1.0

    for point in curve.points:
        if not isinstance(point, KaplanMeierPoint):
            raise TypeError("curve points must be KaplanMeierPoint values")
        if (
            isinstance(point.duration_ns, bool)
            or not isinstance(point.duration_ns, int)
            or point.duration_ns < 0
        ):
            raise ValueError("point duration_ns must be a non-negative integer")
        if previous_duration is not None and point.duration_ns <= previous_duration:
            raise ValueError("curve point durations must be strictly increasing")
        if (
            isinstance(point.at_risk, bool)
            or not isinstance(point.at_risk, int)
            or point.at_risk <= 0
        ):
            raise ValueError("point at_risk must be a positive integer")
        if point.at_risk != expected_at_risk:
            raise ValueError("curve at-risk accounting is inconsistent")
        if (
            isinstance(point.invalidations, bool)
            or not isinstance(point.invalidations, int)
            or point.invalidations < 0
        ):
            raise ValueError("point invalidations must be a non-negative integer")
        if (
            isinstance(point.censored, bool)
            or not isinstance(point.censored, int)
            or point.censored < 0
        ):
            raise ValueError("point censored must be a non-negative integer")
        if point.invalidations + point.censored > point.at_risk:
            raise ValueError("point removals exceed at-risk population")

        observed_survival = _probability(
            "point survival_probability",
            point.survival_probability,
        )
        expected_survival = previous_survival
        if point.invalidations:
            expected_survival *= 1.0 - point.invalidations / point.at_risk
        if not math.isclose(
            observed_survival,
            expected_survival,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError("curve survival recurrence is inconsistent")
        if observed_survival > previous_survival + 1e-12:
            raise ValueError("curve survival must be non-increasing")

        expected_rmst += previous_step_survival * (
            point.duration_ns - previous_time
        )
        if expected_median is None and observed_survival <= 0.5:
            expected_median = point.duration_ns

        invalidations_total += point.invalidations
        censored_total += point.censored
        expected_at_risk -= point.invalidations + point.censored
        previous_duration = point.duration_ns
        previous_survival = observed_survival
        previous_time = point.duration_ns
        previous_step_survival = observed_survival

    if expected_at_risk != 0:
        raise ValueError("curve does not account for every record")
    if invalidations_total != curve.invalidations:
        raise ValueError("curve invalidation total is inconsistent")
    if censored_total != curve.censored:
        raise ValueError("curve censor total is inconsistent")
    if curve.median_survival_ns != expected_median:
        raise ValueError("curve median_survival_ns is inconsistent")
    if (
        isinstance(curve.restricted_mean_survival_ns, bool)
        or not isinstance(curve.restricted_mean_survival_ns, (int, float))
        or not math.isfinite(float(curve.restricted_mean_survival_ns))
        or float(curve.restricted_mean_survival_ns) < 0
    ):
        raise ValueError("curve restricted_mean_survival_ns is invalid")
    if not math.isclose(
        float(curve.restricted_mean_survival_ns),
        expected_rmst,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        raise ValueError("curve restricted_mean_survival_ns is inconsistent")


def kaplan_meier_uncertainty(
    curve: KaplanMeierCurve,
    *,
    alpha: float = 0.05,
) -> SurvivalUncertaintyBand:
    """Add pointwise asymptotic uncertainty to a validated Kaplan-Meier curve.

    Greenwood variance is accumulated over invalidation times. Pointwise
    confidence intervals use the complementary log-log transformation for
    0 < S(t) < 1. Nelson-Aalen cumulative hazard is reported alongside the
    survival estimate.

    These are descriptive uncertainty estimates, not trading probabilities,
    significance tests, or production decision authority.
    """

    _validate_curve(curve)
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)):
        raise TypeError("alpha must be numeric")
    alpha_value = float(alpha)
    if not math.isfinite(alpha_value) or not 0.0 < alpha_value < 1.0:
        raise ValueError("alpha must be finite and strictly between 0 and 1")

    z = NormalDist().inv_cdf(1.0 - alpha_value / 2.0)
    greenwood_sum = 0.0
    cumulative_hazard = 0.0
    points: list[SurvivalUncertaintyPoint] = []

    for point in curve.points:
        n = point.at_risk
        d = point.invalidations
        survival = float(point.survival_probability)

        if d:
            cumulative_hazard += d / n
            if n > d:
                greenwood_sum += d / (n * (n - d))

        if survival <= 0.0:
            variance = 0.0
            standard_error = 0.0
            lower = 0.0
            upper = 0.0
        elif survival >= 1.0:
            variance = 0.0
            standard_error = 0.0
            lower = 1.0
            upper = 1.0
        else:
            variance = survival * survival * greenwood_sum
            standard_error = math.sqrt(max(0.0, variance))

            log_survival = math.log(survival)
            transformed = math.log(-log_survival)
            transformed_se = (
                math.sqrt(greenwood_sum) / abs(log_survival)
                if greenwood_sum > 0
                else 0.0
            )
            lower = math.exp(
                -math.exp(transformed + z * transformed_se)
            )
            upper = math.exp(
                -math.exp(transformed - z * transformed_se)
            )
            lower = min(1.0, max(0.0, lower))
            upper = min(1.0, max(0.0, upper))

        points.append(
            SurvivalUncertaintyPoint(
                duration_ns=point.duration_ns,
                at_risk=n,
                invalidations=d,
                censored=point.censored,
                survival_probability=survival,
                greenwood_variance=variance,
                standard_error=standard_error,
                lower_confidence=lower,
                upper_confidence=upper,
                cumulative_hazard=cumulative_hazard,
            )
        )

    return SurvivalUncertaintyBand(
        alpha=alpha_value,
        confidence_level=1.0 - alpha_value,
        records=curve.records,
        invalidations=curve.invalidations,
        censored=curve.censored,
        points=tuple(points),
    )


def uncertainty_at(
    band: SurvivalUncertaintyBand,
    *,
    duration_ns: int,
) -> SurvivalUncertaintyPoint | None:
    """Return the latest point observed at or before duration_ns."""

    if not isinstance(band, SurvivalUncertaintyBand):
        raise TypeError("band must be SurvivalUncertaintyBand")
    if (
        isinstance(duration_ns, bool)
        or not isinstance(duration_ns, int)
        or duration_ns < 0
    ):
        raise ValueError("duration_ns must be a non-negative integer")

    latest: SurvivalUncertaintyPoint | None = None
    for point in band.points:
        if point.duration_ns > duration_ns:
            break
        latest = point
    return latest
