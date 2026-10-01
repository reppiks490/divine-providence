from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json
import math

from .contracts import OrderBlockCandidate
from .orderblocks import composite_score


class OrderBlockState(str, Enum):
    CREATED = "CREATED"
    CONFIRMED = "CONFIRMED"
    TESTED = "TESTED"
    WEAKENED = "WEAKENED"
    INVALIDATED = "INVALIDATED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class OrderBlockLifecycleConfig:
    minimum_confirmation_score: float = 0.55
    weaken_penetration_fraction: float = 0.65
    weaken_after_tests: int = 2
    invalidation_close_buffer_fraction: float = 0.0
    max_age_ns: int | None = None

    def __post_init__(self) -> None:
        for name in (
            "minimum_confirmation_score",
            "weaken_penetration_fraction",
            "invalidation_close_buffer_fraction",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be numeric")
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")

        if not 0.0 <= float(self.minimum_confirmation_score) <= 1.0:
            raise ValueError("minimum_confirmation_score must be in [0, 1]")
        if not 0.0 <= float(self.weaken_penetration_fraction) <= 1.0:
            raise ValueError("weaken_penetration_fraction must be in [0, 1]")
        if float(self.invalidation_close_buffer_fraction) < 0.0:
            raise ValueError("invalidation_close_buffer_fraction must be non-negative")
        if (
            isinstance(self.weaken_after_tests, bool)
            or not isinstance(self.weaken_after_tests, int)
            or self.weaken_after_tests < 1
        ):
            raise ValueError("weaken_after_tests must be a positive integer")
        if self.max_age_ns is not None and (
            isinstance(self.max_age_ns, bool)
            or not isinstance(self.max_age_ns, int)
            or self.max_age_ns <= 0
        ):
            raise ValueError("max_age_ns must be a positive integer or None")


@dataclass(frozen=True)
class OrderBlockObservation:
    event_time_ns: int
    low: float
    high: float
    close: float

    def __post_init__(self) -> None:
        if (
            isinstance(self.event_time_ns, bool)
            or not isinstance(self.event_time_ns, int)
            or self.event_time_ns < 0
        ):
            raise ValueError("event_time_ns must be a non-negative integer")

        values: list[float] = []
        for name in ("low", "high", "close"):
            raw = getattr(self, name)
            if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                raise TypeError(f"{name} must be numeric")
            value = float(raw)
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            values.append(value)
        low, high, close = values
        if low > high:
            raise ValueError("low cannot exceed high")
        if close < low or close > high:
            raise ValueError("close must be inside [low, high]")


@dataclass(frozen=True)
class OrderBlockLifecycle:
    block_id: str
    candidate: OrderBlockCandidate
    state: OrderBlockState
    created_time_ns: int
    confirmation_time_ns: int | None
    last_event_time_ns: int
    last_test_time_ns: int | None
    test_count: int
    rejection_count: int
    max_penetration_fraction: float
    last_penetration_fraction: float
    last_rejection: bool
    last_reason: str
    execution_authorized: bool = False
    production_decision_authorized: bool = False


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite")
    return out


def _validate_candidate(candidate: OrderBlockCandidate) -> None:
    if candidate.direction not in (-1, 1):
        raise ValueError("candidate direction must be +/-1")
    lower = _finite("candidate lower", candidate.lower)
    upper = _finite("candidate upper", candidate.upper)
    if lower >= upper:
        raise ValueError("candidate lower must be below upper")
    if (
        isinstance(candidate.origin_time_ns, bool)
        or not isinstance(candidate.origin_time_ns, int)
        or candidate.origin_time_ns < 0
    ):
        raise ValueError("candidate origin_time_ns must be a non-negative integer")

    for name in (
        "impulse_score",
        "flow_score",
        "liquidity_score",
        "survival_score",
    ):
        value = _finite(name, getattr(candidate, name))
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be in [0, 1]")


def _block_id(candidate: OrderBlockCandidate) -> str:
    body = {
        "direction": candidate.direction,
        "lower": float(candidate.lower),
        "upper": float(candidate.upper),
        "origin_time_ns": candidate.origin_time_ns,
        "impulse_score": float(candidate.impulse_score),
        "flow_score": float(candidate.flow_score),
        "liquidity_score": float(candidate.liquidity_score),
        "survival_score": float(candidate.survival_score),
        "evidence_tier": candidate.evidence_tier.name,
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "order-block:" + hashlib.sha256(raw).hexdigest()


def create_order_block_lifecycle(
    candidate: OrderBlockCandidate,
    *,
    created_time_ns: int | None = None,
) -> OrderBlockLifecycle:
    _validate_candidate(candidate)
    created = candidate.origin_time_ns if created_time_ns is None else created_time_ns
    if (
        isinstance(created, bool)
        or not isinstance(created, int)
        or created < candidate.origin_time_ns
    ):
        raise ValueError("created_time_ns must be an integer at or after origin_time_ns")

    return OrderBlockLifecycle(
        block_id=_block_id(candidate),
        candidate=candidate,
        state=OrderBlockState.CREATED,
        created_time_ns=created,
        confirmation_time_ns=None,
        last_event_time_ns=created,
        last_test_time_ns=None,
        test_count=0,
        rejection_count=0,
        max_penetration_fraction=0.0,
        last_penetration_fraction=0.0,
        last_rejection=False,
        last_reason="created",
    )


def confirm_order_block(
    lifecycle: OrderBlockLifecycle,
    *,
    at_time_ns: int,
    config: OrderBlockLifecycleConfig = OrderBlockLifecycleConfig(),
) -> OrderBlockLifecycle:
    if lifecycle.state is not OrderBlockState.CREATED:
        raise ValueError("only CREATED blocks can be confirmed")
    if (
        isinstance(at_time_ns, bool)
        or not isinstance(at_time_ns, int)
        or at_time_ns < lifecycle.last_event_time_ns
    ):
        raise ValueError("confirmation time cannot precede lifecycle time")

    score = composite_score(lifecycle.candidate)
    if score < config.minimum_confirmation_score:
        return replace(
            lifecycle,
            last_event_time_ns=at_time_ns,
            last_reason="confirmation_score_below_threshold",
        )

    return replace(
        lifecycle,
        state=OrderBlockState.CONFIRMED,
        confirmation_time_ns=at_time_ns,
        last_event_time_ns=at_time_ns,
        last_reason="confirmed",
    )


def _touch_penetration(
    candidate: OrderBlockCandidate,
    observation: OrderBlockObservation,
) -> tuple[bool, float, bool]:
    lower = float(candidate.lower)
    upper = float(candidate.upper)
    width = upper - lower

    touched = observation.low <= upper and observation.high >= lower
    if not touched:
        return False, 0.0, False

    if candidate.direction == 1:
        penetration = max(0.0, (upper - observation.low) / width)
        rejection = observation.close >= upper
    else:
        penetration = max(0.0, (observation.high - lower) / width)
        rejection = observation.close <= lower

    return True, penetration, rejection


def _invalidated(
    candidate: OrderBlockCandidate,
    observation: OrderBlockObservation,
    config: OrderBlockLifecycleConfig,
) -> bool:
    width = float(candidate.upper) - float(candidate.lower)
    buffer = float(config.invalidation_close_buffer_fraction) * width
    if candidate.direction == 1:
        return observation.close <= float(candidate.lower) - buffer
    return observation.close >= float(candidate.upper) + buffer


def advance_order_block(
    lifecycle: OrderBlockLifecycle,
    observation: OrderBlockObservation,
    *,
    config: OrderBlockLifecycleConfig = OrderBlockLifecycleConfig(),
) -> OrderBlockLifecycle:
    """Advance one order-block hypothesis with one causal price observation."""

    if lifecycle.state in (OrderBlockState.INVALIDATED, OrderBlockState.EXPIRED):
        raise ValueError("terminal order-block lifecycle cannot accept observations")
    if observation.event_time_ns <= lifecycle.last_event_time_ns:
        raise ValueError("observations must advance lifecycle time strictly")

    age_ns = observation.event_time_ns - lifecycle.created_time_ns
    if config.max_age_ns is not None and age_ns >= config.max_age_ns:
        return replace(
            lifecycle,
            state=OrderBlockState.EXPIRED,
            last_event_time_ns=observation.event_time_ns,
            last_penetration_fraction=0.0,
            last_rejection=False,
            last_reason="expired",
        )

    if lifecycle.state is OrderBlockState.CREATED:
        return replace(
            lifecycle,
            last_event_time_ns=observation.event_time_ns,
            last_penetration_fraction=0.0,
            last_rejection=False,
            last_reason="unconfirmed_observation_ignored",
        )

    touched, penetration, rejection = _touch_penetration(
        lifecycle.candidate,
        observation,
    )

    if _invalidated(lifecycle.candidate, observation, config):
        return replace(
            lifecycle,
            state=OrderBlockState.INVALIDATED,
            last_event_time_ns=observation.event_time_ns,
            last_test_time_ns=(
                observation.event_time_ns if touched else lifecycle.last_test_time_ns
            ),
            test_count=lifecycle.test_count + (1 if touched else 0),
            rejection_count=lifecycle.rejection_count + (1 if rejection else 0),
            max_penetration_fraction=max(
                lifecycle.max_penetration_fraction,
                penetration,
            ),
            last_penetration_fraction=penetration,
            last_rejection=rejection,
            last_reason="invalidation_close",
        )

    if not touched:
        return replace(
            lifecycle,
            last_event_time_ns=observation.event_time_ns,
            last_penetration_fraction=0.0,
            last_rejection=False,
            last_reason="no_zone_interaction",
        )

    test_count = lifecycle.test_count + 1
    rejection_count = lifecycle.rejection_count + (1 if rejection else 0)
    max_penetration = max(lifecycle.max_penetration_fraction, penetration)

    weakened = (
        lifecycle.state is OrderBlockState.WEAKENED
        or penetration >= config.weaken_penetration_fraction
        or test_count >= config.weaken_after_tests
    )
    new_state = OrderBlockState.WEAKENED if weakened else OrderBlockState.TESTED

    if lifecycle.state is OrderBlockState.WEAKENED:
        reason = "weakened_retest"
    elif penetration >= config.weaken_penetration_fraction:
        reason = "deep_penetration"
    elif test_count >= config.weaken_after_tests:
        reason = "repeat_test"
    else:
        reason = "first_test"

    return replace(
        lifecycle,
        state=new_state,
        last_event_time_ns=observation.event_time_ns,
        last_test_time_ns=observation.event_time_ns,
        test_count=test_count,
        rejection_count=rejection_count,
        max_penetration_fraction=max_penetration,
        last_penetration_fraction=penetration,
        last_rejection=rejection,
        last_reason=reason,
    )
