# ARGUS source-run cluster paper-to-broker calibration transfer

ARGUS now has a prospective cluster-bootstrap transfer audit for execution
calibration.

The implementation lives in
`argus.impact_calibration_cluster_transfer`.

## Why cluster resampling matters

Execution observations are often not independent.

Many fills can come from the same broker session, paper-emulator run, market
episode, or test run. Treating every fill as an independent bootstrap unit can
create pseudoreplication and understate uncertainty when observations within a
run move together.

ARGUS therefore supports a separate transfer audit that resamples complete
`source_run_id` clusters rather than individual fills.

## Prospective plan

`argus-impact-calibration-cluster-transfer-plan-v1` content-addresses:

- exact impact-calibration study manifest ID;
- plan creation time;
- fixed cluster field `source_run_id`;
- exact metric set;
- tolerance for every metric;
- confidence alpha;
- deterministic cluster-bootstrap replicate count;
- deterministic bootstrap seed;
- minimum eligible clusters required in each execution-evidence class;
- minimum eligible observations required in each execution-evidence class.

The plan must be registered at or before the study cohort starts.

The study manifest must include both:

- `BROKER_CONFIRMED`;
- `ICARUS_PAPER_EMULATOR`.

## Fixed clustering field

Version 1 fixes clustering to the execution receipt's `source_run_id`.

The cluster field is not selected after results are visible.

Within each evidence class, eligible observations are grouped by source run.
Cluster identifiers are sorted canonically before deterministic resampling.

## Supported metrics

The first supported metrics are:

- `mean_fill_fraction_error`;
- `mean_absolute_fill_fraction_error`;
- `mean_slippage_error_ticks`;
- `mean_absolute_slippage_error_ticks`;
- `root_mean_squared_slippage_error_ticks`;
- `slippage_underprediction_rate`.

Fill-fraction metrics can use zero-fill rows.

Slippage metrics require realized slippage. A cluster containing only zero-fill
rows therefore does not become a synthetic slippage cluster.

## Cluster bootstrap

For a requested metric:

1. filter to metric-eligible rows;
2. group eligible rows by `source_run_id`;
3. require the predeclared minimum number of eligible clusters and
   observations in both broker and paper evidence;
4. sample the same number of clusters with replacement from each evidence
   class;
5. preserve every eligible row inside each selected cluster;
6. compute the metric on the flattened resampled cluster set;
7. report the paper-minus-broker bootstrap distribution.

The deterministic initial state for every evidence-kind/metric/replicate is
derived from SHA-256 of:

```text
bootstrap_seed
| cluster-transfer
| source_run_id
| evidence_kind
| metric
| replicate
```

A fixed 64-bit linear congruential transition then chooses cluster indices.

## Comparison

For every metric:

```text
paper_minus_broker = paper estimate - broker estimate
```

ARGUS reports:

- broker and paper point estimates;
- paper-minus-broker point estimate;
- percentile lower and upper bounds;
- confidence level and alpha;
- broker and paper eligible cluster counts;
- broker and paper eligible observation counts;
- predeclared tolerance;
- compatibility result.

The broker and paper evidence classes are never pooled.

## Pseudoreplication guardrail

The plan separately requires:

- `min_clusters_per_kind`;
- `min_metric_observations_per_kind`.

A study with many fills but only one eligible broker run and one eligible paper
run can therefore fail closed instead of presenting those fills as many
independent experimental units.

Version 1 requires at least two eligible clusters per evidence class.

That minimum is only a schema floor, not a claim of statistical sufficiency.

## Predeclared tolerance gate

A metric reports `within_tolerance=true` only when its entire cluster-bootstrap
interval lies inside:

```text
[-tolerance, +tolerance]
```

The overall result passes only when every predeclared metric passes.

## Interpretation boundary

This cluster bootstrap is not automatically:

- a proof that `source_run_id` captures every dependency structure;
- a formal equivalence test;
- a small-sample-valid cluster-robust theorem;
- a multiple-comparison-adjusted familywise statement;
- a causal-effect estimate;
- proof of queue, hidden-liquidity, or latency realism;
- proof of profitability;
- permission to relabel paper fills as broker-confirmed;
- permission to substitute paper evidence for broker evidence;
- permission to place an order.

If dependence extends across source runs, a future protocol should predeclare a
higher-level clustering or time-block structure rather than claiming this
version solved it.

## Validation before resampling

ARGUS revalidates:

- the prospective study manifest;
- locked cohort identity;
- execution-evidence receipts;
- receipt-plus-calibration lineage;
- exact execution-source revisions;
- cohort timing;
- snapshot-age and completion-latency limits;
- cluster-plan identity;
- prospective plan creation time;
- metric set and tolerances;
- eligible cluster and observation minimums;
- authority flags.

Tampering fails closed before cluster resampling.

## Computational boundary

The schema allows 200 through 10,000 cluster-bootstrap replicates.

This is offline research. It does not run on the measured ICARUS live decision
hot path.

## Authority

`execution_authorized=false`

`production_decision_authorized=false`

Passing every cluster-bootstrap tolerance does not authorize model promotion or
a broker order.
