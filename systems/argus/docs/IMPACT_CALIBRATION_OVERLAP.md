# ARGUS paper-vs-broker observable support overlap audit

ARGUS now has a prospective support-overlap audit for the load-stratified
source-run transfer layer.

The implementation lives in
`argus.impact_calibration_overlap`.

## Why overlap matters

A paper-emulator calibration gap can be misleading even when the analysis is:

- prospective;
- separated by broker versus paper evidence;
- stratified by liquidity load;
- cluster-bootstrapped by source run.

The compared broker and paper observations can still occupy materially
different parts of observable execution space.

For example, broker-confirmed fills may mostly come from fresh impact snapshots
with short completion latency while paper fills in the same load band may come
from stale snapshots with much longer completion latency.

In that case, a paper-minus-broker gap mixes emulator transfer quality with
observable covariate shift.

ARGUS therefore adds a separate predeclared overlap diagnostic before treating
paper/broker calibration as a comparable research population.

## Prospective plan

`argus-impact-calibration-overlap-plan-v1` content-addresses:

- exact prospective study manifest ID;
- exact load-cluster transfer plan ID;
- plan creation time;
- exact observable covariate set;
- exhaustive fixed bins for every covariate;
- maximum allowed total-variation distance for every load-band/covariate cell;
- minimum observations required in each evidence class inside every load band.

The plan must be registered at or before the study cohort starts.

Bin boundaries and support tolerances therefore cannot be selected after the
paper/broker distributions are visible.

## Supported covariates

Version 1 supports:

- `requested_to_visible_ratio`;
- `snapshot_age_ns`;
- `completion_latency_ns`.

These are already bound into the realized impact-calibration lineage.

The overlap layer does not introduce a new post-hoc data source.

## Exhaustive bins

Every requested covariate uses a contiguous partition that:

1. begins at zero;
2. has no gaps;
3. has no overlaps;
4. ends with an open-ended final bin.

Version 1 supports at most 16 bins per covariate.

This avoids quietly dropping an inconvenient tail observation because it lies
outside the registered support grid.

## Load conditioning

The overlap audit uses the exact liquidity-load bands already frozen in the
referenced load-cluster transfer plan.

For every load band and covariate, ARGUS separately constructs broker and paper
histograms.

The evidence classes are never pooled.

## Total-variation support distance

For broker probabilities `p_i` and paper probabilities `q_i` over the
predeclared bins:

```text
TV = 0.5 * sum_i |p_i - q_i|
```

ARGUS also reports:

```text
overlap coefficient = 1 - TV
```

Interpretation:

- `TV = 0` means identical empirical bin proportions;
- `TV = 1` means disjoint empirical support across the registered bins.

Each load-band/covariate cell reports:

- broker and paper observation counts;
- bin counts and probabilities;
- absolute probability gap in every bin;
- total-variation distance;
- overlap coefficient;
- maximum absolute bin-probability gap;
- predeclared maximum allowed total variation;
- support-adequacy flag.

A cell is adequate only when its total-variation distance is no greater than the
predeclared limit.

The aggregate audit passes only when every registered cell passes.

## Minimum sample floor

The plan independently requires
`min_observations_per_kind_per_band`.

If either broker-confirmed or paper-emulator evidence has too few observations
inside a load band, the audit fails closed rather than reporting a fragile
histogram comparison.

This is only a schema floor. It is not a statement that the minimum is
statistically sufficient for every scientific claim.

## Binding to the transfer analysis

Before computing overlap, ARGUS reruns the referenced registered load-cluster
transfer audit.

That revalidates:

- prospective study manifest identity;
- locked cohort identity;
- execution-evidence receipts;
- receipt-plus-calibration lineage;
- exact source revisions;
- load bands;
- source-run cluster structure;
- transfer metrics and tolerances;
- minimum cluster and observation counts;
- authority flags.

The overlap result records whether the baseline transfer audit was within its
engineering tolerances, but it does not replace that transfer result.

## Interpretation boundary

This audit is a descriptive observable-support diagnostic.

It is not automatically:

- a propensity score;
- inverse-probability weighting;
- covariate adjustment;
- a causal identification theorem;
- proof of exchangeability;
- proof of no unmeasured confounding;
- a formal equivalence test;
- a hypothesis test;
- a multiplicity-adjusted familywise statement;
- proof of queue, hidden-liquidity, routing, or latency realism;
- proof of profitability;
- permission to promote paper evidence to broker-confirmed evidence;
- permission to substitute paper evidence for broker evidence;
- permission to place an order.

Good overlap means only that the selected observable covariates have sufficiently
similar empirical support under the predeclared bins and tolerances.

Poor overlap is evidence that a paper-vs-broker comparison deserves additional
conditioning, matching, redesign, or abstention rather than stronger claims.

## Why it complements load-cluster transfer

The load-cluster transfer audit asks:

> How far apart are paper and broker calibration outcomes after conditioning on
> liquidity load and respecting source-run dependence?

The overlap audit asks:

> Were the observable paper and broker populations inside those same load bands
> actually comparable on predeclared execution-state variables?

Both matter.

A small calibration gap from poorly overlapping populations can be as
misleading as a large gap from well-overlapping populations.

## Computational boundary

This is an offline research path.

Its cost is linear in the cohort size times the number of registered
load-band/covariate cells.

It does not run on ICARUS's measured live decision hot path.

## Authority

`execution_authorized=false`

`production_decision_authorized=false`

Passing every overlap threshold does not authorize model promotion, paper-to-
broker substitution, or a broker order.
