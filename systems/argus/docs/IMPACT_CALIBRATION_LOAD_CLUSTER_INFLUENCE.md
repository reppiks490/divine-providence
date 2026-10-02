# ARGUS load-cluster influence audit

ARGUS now has a prospective leave-one-source-run-out sensitivity layer for the
load-stratified cluster transfer audit.

The implementation lives in
`argus.impact_calibration_load_cluster_influence`.

## Purpose

A cluster bootstrap can correctly widen uncertainty for repeated observations
inside the same source run, but a reported paper-vs-broker gap can still be
dominated by one unusual broker run or paper-emulator run.

The influence audit asks a separate question:

> How much would the paper-minus-broker calibration gap move if any one
> eligible source-run cluster were removed?

This is evaluated independently inside every predeclared liquidity-load band
and for every metric in the referenced load-cluster transfer plan.

## Prospective plan

`argus-impact-calibration-load-cluster-influence-plan-v1`
content-addresses:

- exact prospective study manifest ID;
- exact load-cluster transfer plan ID;
- plan creation time;
- minimum clusters that must remain in each evidence class after one deletion;
- maximum allowed absolute leave-one-cluster shift for every load-band/metric
  pair.

The influence plan must be registered at or before the study cohort starts.

The shift limits are therefore not chosen after seeing which run is influential.

## Baseline binding

The influence audit first reruns the registered load-cluster transfer analysis.

This revalidates:

- study manifest identity;
- locked cohort identity;
- execution-evidence receipts;
- receipt-plus-calibration lineage;
- exact source revisions;
- load bands;
- transfer metrics and tolerances;
- source-run cluster minimums;
- authority flags.

The baseline paper-minus-broker value is taken from that revalidated analysis.

## Leave-one-cluster procedure

For each load-band/metric pair:

1. build eligible broker clusters by `source_run_id`;
2. build eligible paper clusters by `source_run_id`;
3. hold the full paper side fixed and remove each broker cluster once;
4. hold the full broker side fixed and remove each paper cluster once;
5. recompute the paper-minus-broker metric after every deletion;
6. measure the absolute shift from the registered baseline;
7. identify the worst evidence class and source run;
8. compare the maximum shift with the predeclared tolerance.

No broker and paper observations are pooled.

## Minimum remaining evidence

The influence plan requires
`min_clusters_after_drop_per_kind`.

If removing one source run would leave fewer than that number of clusters in
either evidence class, the audit fails closed instead of reporting a fragile
sensitivity result from an underspecified remainder.

The audit also preserves the parent load-cluster transfer plan's registered
`min_metric_observations_per_kind_per_band`. Every leave-one-run subset must
still contain at least that many eligible observations in the affected evidence
class. A deletion that preserves enough clusters but drops below the registered
observation floor also fails closed.

This makes the procedure useful as a domination guardrail rather than a
mechanical delete-one calculation.

## Result

Every load-band/metric result reports:

- registered baseline paper-minus-broker gap;
- maximum absolute leave-one-cluster shift;
- predeclared maximum allowed shift;
- worst evidence kind;
- worst `source_run_id`;
- paper-minus-broker gap after the worst deletion;
- broker and paper cluster counts;
- number of leave-one-cluster evaluations;
- stability flag.

The aggregate audit passes only when every predeclared cell is stable.

## Interpretation boundary

This audit is a deterministic sensitivity analysis.

It is not automatically:

- a formal influence-function theorem;
- a jackknife confidence interval;
- a hypothesis test;
- a familywise or multiplicity-adjusted statement;
- proof that source-run deletion captures every dependency;
- proof of queue, routing, hidden-liquidity, or latency realism;
- proof of profitability;
- permission to relabel paper evidence as broker-confirmed;
- permission to substitute paper evidence for broker evidence;
- permission to place an order.

A stable leave-one-run result means only that the reported calibration gap is
not highly sensitive to any single eligible source-run cluster under the
predeclared metric, load partition and cohort.

## Why it complements the bootstrap

The load-cluster bootstrap answers:

> How uncertain is the paper-minus-broker gap when complete source runs are
> resampled inside a load band?

The influence audit answers:

> Is that gap disproportionately dependent on one specific run?

Both can matter. A narrow bootstrap interval can still deserve scrutiny if one
cluster deletion materially changes the point estimate.

## Computational boundary

This is offline research.

For each band and metric, the number of evaluations equals the number of
eligible broker clusters plus eligible paper clusters.

It does not run on the ICARUS live decision hot path.

## Authority

`execution_authorized=false`

`production_decision_authorized=false`

Passing the influence audit does not authorize model promotion or a broker
order.
