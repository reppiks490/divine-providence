# ARGUS empirical order-block lifecycle foundation

ARGUS now treats an order block as a time-causal hypothesis with lifecycle
state rather than as a permanent chart rectangle.

The lifecycle implementation lives in
`argus.orderblock_lifecycle`.

## States

```text
CREATED -> CONFIRMED -> TESTED -> WEAKENED
                         |           |
                         +-------> INVALIDATED
CREATED / CONFIRMED / TESTED / WEAKENED -> EXPIRED
```

Terminal states are `INVALIDATED` and `EXPIRED`.

## Confirmation

A candidate begins in `CREATED`.

`confirm_order_block` compares the existing evidence-tier-aware
`composite_score` against an explicit confirmation threshold. A candidate
below the threshold remains CREATED and records the blocker instead of being
silently promoted.

The original evidence tier is part of the stable block identity, so a candle
proxy and a TRUE_DEPTH candidate with otherwise identical geometry are distinct
hypotheses.

## Price interaction

Each `OrderBlockObservation` contains one causal observation time plus low,
high and close.

For a bullish block, penetration is measured from the upper/proximal boundary
down through the zone. For a bearish block it is measured from the
lower/proximal boundary upward.

A first valid touch becomes `TESTED`.

A block becomes `WEAKENED` when either:

- penetration reaches the configured weakening fraction; or
- the configured number of tests has been reached.

Repeated tests do not restore a WEAKENED block to TESTED.

The lifecycle separately records:

- test count;
- rejection count;
- maximum penetration fraction;
- latest penetration fraction;
- whether the latest touch rejected back through the proximal boundary;
- last test time;
- last transition reason.

## Invalidation

Invalidation is close-based and direction-aware.

For a bullish block, a close at/below the lower boundary plus the configured
buffer invalidates it. For a bearish block, a close at/above the upper boundary
plus the buffer invalidates it.

This is an explicit deterministic rule, not a claim that every market should
use the same threshold. The buffer belongs to the lifecycle configuration and
must be selected/validated outside protected evaluation data.

## Expiry

`max_age_ns` is optional. When configured, expiry is checked before processing
a later price interaction. A block cannot be revived by a touch that occurs
after its lifetime has ended.

Confirmation attempted after expiry also yields EXPIRED rather than silently
reactivating the hypothesis.

## Causal integrity

Observations must strictly advance lifecycle time. Terminal lifecycles reject
further observations.

The lifecycle never fetches future data and does not infer a missing sequence
of observations.

## What this does not prove

This state machine is the deterministic lifecycle foundation required before
survival/event-study validation. It is **not yet** evidence that order blocks
have predictive value.

The next empirical layer must evaluate untouched later outcomes such as:

- survival probability by test count;
- hazard of invalidation versus penetration;
- conditional rejection/follow-through after first and repeated tests;
- evidence-tier stratification;
- regime/time-of-day stratification;
- calibration drift.

Threshold selection must remain separate from protected evaluation outcomes.

## Authority

Order-block lifecycle state is research evidence only.

`execution_authorized=false`

`production_decision_authorized=false`
