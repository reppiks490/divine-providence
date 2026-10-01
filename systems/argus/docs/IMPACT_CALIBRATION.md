# ARGUS realized-fill impact calibration

ARGUS now includes a retrospective calibration layer that compares the
deterministic `TRUE_DEPTH` static-book impact curve with later realized fills.

The implementation lives in `argus.impact_calibration`.

## Purpose

The existing depth-impact curve answers:

> If the displayed opposite-side book remained unchanged, what would this
> requested size consume?

Calibration asks a different question after execution is complete:

> How different was the realized fill from that static displayed-depth
> baseline?

The distinction is important. A static book walk is not a fill forecast until
its error is measured against actual fills.

## Realized execution record

A realized execution binds:

- execution ID;
- decision time;
- completion time;
- side;
- requested size;
- filled size;
- realized average price when any size filled.

The decision cannot precede the depth snapshot. Completion cannot precede the
decision. Overfills and zero-fill records carrying a fill price fail closed.

## One-observation calibration

The requested size must match exactly one size point in the impact curve.

ARGUS records:

- snapshot age at decision;
- completion latency;
- requested size / displayed opposite depth;
- predicted vs realized fill fraction;
- fill-fraction error;
- predicted average slippage from best;
- realized average slippage from the same best-price reference;
- signed slippage error;
- absolute slippage error;
- whether static depth underpredicted realized slippage;
- predicted book exhaustion;
- whether the realized execution completely filled.

Positive slippage error means realized execution was worse than the static
displayed-depth baseline. Negative error means realized execution was better.

Price improvement is allowed in the realized observation and therefore realized
slippage may be negative.

## Curve integrity

Calibration revalidates the supplied impact curve instead of trusting its
Python type.

It checks:

- TRUE_DEPTH evidence tier;
- static-visible-depth assumption;
- no authority flags;
- event/sequence geometry;
- tick, best bid/ask, spread and midpoint consistency;
- microprice remains inside the spread;
- strictly increasing requested sizes;
- fill fractions and displayed depth limits;
- slippage, marginal displacement, midpoint shortfall and microprice shortfall;
- book-exhaustion consistency;
- monotone displayed capacity thresholds.

A manually mutated curve that no longer satisfies its own arithmetic fails
closed.

## Aggregate calibration

`summarize_impact_calibration` reports:

- observation count;
- realized-fill observation count;
- complete-fill count;
- mean snapshot age;
- mean completion latency;
- mean signed fill-fraction error;
- mean absolute fill-fraction error;
- mean signed slippage error;
- mean absolute slippage error;
- root-mean-square slippage error;
- fraction of realized fills where static depth underpredicted slippage.

Observation arithmetic is self-validated again before aggregation and duplicate
execution IDs are rejected.

## Interpretation boundary

This is retrospective model calibration, not a strategy score.

The current static impact model still does not model:

- queue priority;
- hidden/iceberg liquidity;
- latency-sensitive cancellation/replenishment;
- smart-order routing;
- fees/rebates;
- temporary/permanent impact;
- adverse selection.

Those mechanisms should be added only when their inputs and realized outcomes
are available with explicit provenance.

A calibrated error distribution can later be used to determine whether the
static model is informative enough for shadow execution research. It must not be
used as broker authority merely because average error is small.

## Next step

The next integration layer should bind actual ICARUS fill telemetry to these
records with exact order/fill lineage, while preserving the rule that realized
outcomes are available only after their receipt time.

## Authority

`execution_authorized=false`

`production_decision_authorized=false`
