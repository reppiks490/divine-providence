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

The plan cannot predate either the study manifest or the referenced load-cluster transfer plan, and it must be registered at or before the study cohort starts.

Bin boundaries and support tolerances therefore cannot be selected after the
paper/broker distributions are visible.

## Supported covariates

Version 1 supports:

- `requested_to_visible_ratio`;
- `snapshot_age_ns`;
- `completion_latency_ns`.

These are already bound into the realized impact-calibration lineage.

Their timing is not interchangeable:

- `requested_to_visible_ratio` is labeled `decision_time`;
- `snapshot_age_ns` is labeled `decision_time`;
- `completion_latency_ns` is labeled `post_decision_realized`.

A completion-latency overlap result is therefore a descriptive realized-outcome
support diagnostic. It must not be treated as a predecision covariate,
confounder adjustment, or feature that could have been known when the original
order decision was made.

The overlap layer does not introduce a new post-hoc data source, but it preserves
this timing distinction explicitly in every result.

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

- broker and paper source-run cluster counts;
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

## Minimum support floors

The overlap plan independently requires
`min_observations_per_kind_per_band`.

The referenced load-cluster transfer plan also supplies
`min_clusters_per_kind_per_band`. Before any overlap histogram is reported,
each evidence class inside the load band must satisfy both the observation floor
and that registered source-run cluster floor.

A reused `source_run_id` inside one evidence class must resolve to the same
`source_system`, `source_repo`, and `source_commit`. Cross-lineage run-ID
collisions fail closed, including rows that may be ineligible for a transfer
metric but are still present in the overlap population.

This prevents many rows from one source run from masquerading as broad support
and prevents unrelated runs from being silently merged by identifier.

These are schema floors, not claims that the resulting sample is statistically
sufficient for every scientific conclusion.

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


## Research export contract

`argus.impact_calibration_overlap_research_export` provides
`argus-impact-calibration-overlap-research-v1`.

Before export, ARGUS recomputes the registered overlap audit, which itself
revalidates the referenced load-cluster transfer analysis.

The export preserves:

- study manifest and locked cohort IDs;
- load-cluster transfer plan ID and schema;
- overlap plan ID and schema;
- exact impact-model, calibration and execution-source revisions;
- registered covariates, their explicit decision-time versus
  post-decision-realized timing labels, and their exhaustive fixed bins;
- predeclared total-variation limits;
- parent load-cluster source-run minimums;
- overlap observation minimums;
- broker and paper source-run cluster counts;
- broker and paper bin counts and probabilities;
- total-variation distance;
- overlap coefficient;
- maximum absolute bin-probability gap;
- per-cell and aggregate support-adequacy results;
- baseline transfer compatibility state;
- explicit non-promotion and authority flags.

The export explicitly states that it is not:

- a formal equivalence test;
- a propensity score;
- inverse-probability weighting;
- proof of exchangeability;
- a causal-identification claim;
- a hypothesis test;
- a multiplicity-adjusted familywise statement;
- permission to substitute paper evidence for broker-confirmed evidence.

Publication cannot precede the locked cohort time. Local downstream use must
still wait until ingestion time.

## ATHENA integration status

The overlap export is transport-ready as an ARGUS research contract.

No ATHENA happy-path driver fabricates broker-confirmed execution observations
when externally valid broker lineage is absent. Synthetic broker-confirmed
objects remain confined to isolated unit tests of the contract path and are
not emitted as empirical advisory evidence.

This preserves the execution-evidence firewall while making observable support
mismatch explicit for future genuine broker-confirmed cohorts.
