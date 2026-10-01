# ARGUS survival uncertainty and cumulative hazard

ARGUS order-block survival research now includes pointwise uncertainty around
the Kaplan-Meier curve.

The implementation lives in `argus.survival_uncertainty`.

## Reported quantities

For every validated Kaplan-Meier time point, ARGUS reports:

- survival probability;
- Greenwood variance;
- Greenwood standard error;
- pointwise lower/upper confidence bounds;
- Nelson-Aalen cumulative hazard;
- the original at-risk, invalidation, and censor counts.

The result also records `alpha` and the corresponding confidence level.

## Greenwood uncertainty

For event times where the risk set is larger than the number of events, ARGUS
accumulates the Greenwood term:

```text
sum d_i / (n_i * (n_i - d_i))
```

The pointwise Kaplan-Meier variance is:

```text
S(t)^2 * GreenwoodSum(t)
```

Censor-only times do not change the accumulated Greenwood term.

If the Kaplan-Meier curve reaches exactly zero because the entire remaining risk
set fails at an event time, the public boundary is reported as zero survival
with zero-width `[0, 0]` interval rather than exposing an infinite intermediate
Greenwood expression.

An all-censored curve remains at survival 1 with a zero-width `[1, 1]`
pointwise interval.

## Confidence transform

For `0 < S(t) < 1`, ARGUS uses a complementary-log-log / log-log transformed
pointwise confidence interval.

This keeps the reported interval inside `[0, 1]` and behaves more sensibly near
the survival boundaries than an unbounded normal interval on the raw survival
scale.

The normal quantile comes from Python's standard-library
`statistics.NormalDist`; no extra statistical package is required.

## Nelson-Aalen cumulative hazard

ARGUS also accumulates:

```text
H(t) = sum d_i / n_i
```

at invalidation times.

This is a descriptive cumulative hazard estimator. It is not a trade-entry
score and is not converted into order authority.

## Curve self-validation

Before uncertainty is computed, the supplied Kaplan-Meier curve is revalidated.

ARGUS checks:

- positive record count;
- total invalidations + censors equals records;
- strictly increasing time points;
- exact risk-set accounting from one point to the next;
- non-negative event/censor counts that do not exceed the risk set;
- Kaplan-Meier survival recurrence;
- non-increasing survival;
- invalidation and censor totals;
- median-survival consistency;
- restricted-mean-survival consistency.

This prevents a manually constructed or mutated curve object from being treated
as valid uncertainty input merely because it has the correct Python type.

## Interpretation boundary

These intervals are **pointwise asymptotic descriptive uncertainty**.

They are not:

- simultaneous confidence bands over the entire curve;
- a hypothesis test;
- a p-value;
- a multiple-testing correction;
- evidence of profitability;
- evidence of causal predictive power;
- a production probability.

For small strata, sparse events, or heavy censoring they may be wide or
uninformative. That is evidence about uncertainty, not a reason to suppress it.

## Prospective research discipline

The v2 prospective-study contract now pins `confidence_alpha` before the
cohort begins and can predeclare `kaplan_meier_uncertainty` as a registered
analysis. Registered uncertainty analysis is required to use that exact alpha.

The legacy v1 study schema remains verifiable for historical replay but cannot
predeclare or execute the registered uncertainty analysis.

## Authority

`execution_authorized=false`

`production_decision_authorized=false`
