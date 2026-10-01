from __future__ import annotations

import pytest

from argus.contracts import EvidenceTier
from argus.orderblocks import score_order_block
from argus.orderblock_lifecycle import (
    OrderBlockLifecycleConfig,
    OrderBlockObservation,
    OrderBlockState,
    advance_order_block,
    confirm_order_block,
    create_order_block_lifecycle,
)


def candidate(direction=1, tier=EvidenceTier.TRUE_DEPTH, **overrides):
    params = dict(
        direction=direction,
        lower=99.0,
        upper=100.0,
        origin_time_ns=10,
        displacement_atr=2.4,
        signed_flow_alignment=0.8,
        depth_vacuum=0.8,
        revisit_rejection=0.8,
        evidence_tier=tier,
    )
    params.update(overrides)
    return score_order_block(**params)


def confirmed(direction=1, config=None):
    lifecycle = create_order_block_lifecycle(candidate(direction=direction))
    return confirm_order_block(
        lifecycle,
        at_time_ns=11,
        config=config or OrderBlockLifecycleConfig(),
    )


def test_lifecycle_starts_created_with_stable_identity():
    block = candidate()
    first = create_order_block_lifecycle(block)
    second = create_order_block_lifecycle(block)

    assert first.state is OrderBlockState.CREATED
    assert first.block_id == second.block_id
    assert first.test_count == 0
    assert first.execution_authorized is False
    assert first.production_decision_authorized is False


def test_confirmation_requires_score_threshold():
    block = candidate(
        displacement_atr=0.1,
        signed_flow_alignment=-0.9,
        depth_vacuum=0.1,
        revisit_rejection=0.1,
    )
    lifecycle = create_order_block_lifecycle(block)
    result = confirm_order_block(
        lifecycle,
        at_time_ns=11,
        config=OrderBlockLifecycleConfig(minimum_confirmation_score=0.9),
    )

    assert result.state is OrderBlockState.CREATED
    assert result.last_reason == "confirmation_score_below_threshold"


def test_first_touch_becomes_tested_and_tracks_rejection():
    lifecycle = confirmed()
    result = advance_order_block(
        lifecycle,
        OrderBlockObservation(event_time_ns=12, low=99.8, high=100.3, close=100.2),
        config=OrderBlockLifecycleConfig(
            weaken_penetration_fraction=0.8,
            weaken_after_tests=3,
        ),
    )

    assert result.state is OrderBlockState.TESTED
    assert result.test_count == 1
    assert result.rejection_count == 1
    assert result.last_rejection is True
    assert result.last_penetration_fraction == pytest.approx(0.2)
    assert result.last_reason == "first_test"


def test_deep_penetration_weakens_long_block():
    lifecycle = confirmed()
    result = advance_order_block(
        lifecycle,
        OrderBlockObservation(event_time_ns=12, low=99.2, high=100.1, close=99.8),
        config=OrderBlockLifecycleConfig(weaken_penetration_fraction=0.65),
    )

    assert result.state is OrderBlockState.WEAKENED
    assert result.max_penetration_fraction == pytest.approx(0.8)
    assert result.last_reason == "deep_penetration"


def test_repeated_tests_weaken_block_even_when_each_touch_is_shallow():
    cfg = OrderBlockLifecycleConfig(
        weaken_penetration_fraction=0.9,
        weaken_after_tests=2,
    )
    lifecycle = confirmed(config=cfg)
    first = advance_order_block(
        lifecycle,
        OrderBlockObservation(event_time_ns=12, low=99.8, high=100.2, close=100.1),
        config=cfg,
    )
    second = advance_order_block(
        first,
        OrderBlockObservation(event_time_ns=13, low=99.75, high=100.1, close=100.0),
        config=cfg,
    )

    assert first.state is OrderBlockState.TESTED
    assert second.state is OrderBlockState.WEAKENED
    assert second.test_count == 2
    assert second.last_reason == "repeat_test"


def test_long_close_through_zone_invalidates():
    lifecycle = confirmed()
    result = advance_order_block(
        lifecycle,
        OrderBlockObservation(event_time_ns=12, low=98.5, high=99.5, close=98.9),
    )

    assert result.state is OrderBlockState.INVALIDATED
    assert result.last_reason == "invalidation_close"


def test_short_close_above_zone_invalidates():
    lifecycle = confirmed(direction=-1)
    result = advance_order_block(
        lifecycle,
        OrderBlockObservation(event_time_ns=12, low=99.5, high=100.6, close=100.4),
    )

    assert result.state is OrderBlockState.INVALIDATED


def test_expiry_precedes_late_interaction():
    cfg = OrderBlockLifecycleConfig(max_age_ns=5)
    lifecycle = confirmed(config=cfg)
    result = advance_order_block(
        lifecycle,
        OrderBlockObservation(event_time_ns=15, low=99.8, high=100.2, close=100.1),
        config=cfg,
    )

    assert result.state is OrderBlockState.EXPIRED
    assert result.test_count == 0
    assert result.last_reason == "expired"


def test_confirmation_after_expiry_returns_expired():
    cfg = OrderBlockLifecycleConfig(max_age_ns=2)
    lifecycle = create_order_block_lifecycle(candidate())
    result = confirm_order_block(lifecycle, at_time_ns=12, config=cfg)

    assert result.state is OrderBlockState.EXPIRED
    assert result.last_reason == "expired_before_confirmation"


def test_unconfirmed_observation_does_not_create_test_state():
    lifecycle = create_order_block_lifecycle(candidate())
    result = advance_order_block(
        lifecycle,
        OrderBlockObservation(event_time_ns=11, low=99.8, high=100.2, close=100.1),
    )

    assert result.state is OrderBlockState.CREATED
    assert result.test_count == 0
    assert result.last_reason == "unconfirmed_observation_ignored"


def test_terminal_state_rejects_more_observations():
    lifecycle = confirmed()
    terminal = advance_order_block(
        lifecycle,
        OrderBlockObservation(event_time_ns=12, low=98.5, high=99.5, close=98.9),
    )
    with pytest.raises(ValueError, match="terminal"):
        advance_order_block(
            terminal,
            OrderBlockObservation(event_time_ns=13, low=99.8, high=100.2, close=100.1),
        )


def test_observation_time_must_strictly_advance():
    lifecycle = confirmed()
    with pytest.raises(ValueError, match="strictly"):
        advance_order_block(
            lifecycle,
            OrderBlockObservation(event_time_ns=11, low=99.8, high=100.2, close=100.1),
        )


@pytest.mark.parametrize(
    "kwargs, error",
    [
        ({"minimum_confirmation_score": 1.1}, "minimum_confirmation_score"),
        ({"weaken_penetration_fraction": -0.1}, "weaken_penetration_fraction"),
        ({"weaken_after_tests": 0}, "weaken_after_tests"),
        ({"invalidation_close_buffer_fraction": -0.1}, "invalidation_close_buffer_fraction"),
        ({"max_age_ns": 0}, "max_age_ns"),
    ],
)
def test_invalid_lifecycle_config_fails_closed(kwargs, error):
    with pytest.raises((TypeError, ValueError), match=error):
        OrderBlockLifecycleConfig(**kwargs)


@pytest.mark.parametrize(
    "kwargs, error",
    [
        ({"event_time_ns": -1, "low": 99.0, "high": 100.0, "close": 99.5}, "event_time_ns"),
        ({"event_time_ns": 1, "low": 101.0, "high": 100.0, "close": 100.5}, "low cannot exceed"),
        ({"event_time_ns": 1, "low": 99.0, "high": 100.0, "close": 101.0}, "close must be inside"),
    ],
)
def test_invalid_observation_fails_closed(kwargs, error):
    with pytest.raises((TypeError, ValueError), match=error):
        OrderBlockObservation(**kwargs)


def test_lifecycle_api_rejects_malformed_types():
    lifecycle = create_order_block_lifecycle(candidate())
    observation = OrderBlockObservation(event_time_ns=11, low=99.8, high=100.2, close=100.1)

    with pytest.raises(TypeError, match="lifecycle"):
        confirm_order_block("bad", at_time_ns=11)

    with pytest.raises(TypeError, match="config"):
        confirm_order_block(lifecycle, at_time_ns=11, config={})

    confirmed_lifecycle = confirm_order_block(lifecycle, at_time_ns=11)

    with pytest.raises(TypeError, match="observation"):
        advance_order_block(confirmed_lifecycle, {})

    with pytest.raises(TypeError, match="config"):
        advance_order_block(
            confirmed_lifecycle,
            observation,
            config={},
        )
