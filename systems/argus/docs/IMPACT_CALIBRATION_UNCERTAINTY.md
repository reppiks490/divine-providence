# ARGUS prospective bootstrap uncertainty for impact calibration

ARGUS now has a separately pre-registered uncertainty addendum for prospective
impact-calibration studies.

The implementation lives in `argus.impact_calibration_uncertainty`.

## Why this is a separate plan

The existing `argus-impact-calibration-study-v1` manifest is already a stable,
content-addressed research contract.

Rather than silently change that schema, uncertainty policy is registered in a
separate content-addressed plan that references the exact study manifest.

The bootstrap plan must be created at or before the study cohort starts.

## Plan identity

`argus-impact-calibration-bootstrap-plan-v1` pins:

- exact study manifest ID;
- plan creation time;
- confidence alpha;
- bootstrap replicate count;
- deterministic bootstrap seed;
- minimum eligible observations required for every requested metric;
- exact metric set.

Changing any of those fields changes the plan ID.

## Supported metrics

The first supported metrics are:

- `mean_fill_fraction_error`;
- `mean_absolute_fill_fraction_error`;
- `mean_slippage_error_ticks`;
- `mean_absolute_slippage_error_ticks`;
- `root_mean_squared_slippage_error_ticks`;
- `slippage_underprediction_rate`.

Fill-fraction metrics use all calibration observations.

Slippage metrics use only observations that have a realized slippage value.
Zero-fill observations therefore remain valid for fill-fraction analysis but do
not become invented slippage observations.

Each requested metric must meet the predeclared
`min_metric_observations` threshold.

## Deterministic resampling

The bootstrap uses nonparametric resampling with replacement.

It does not depend on process-global randomness.

For each evidence stratum, metric and replicate, ARGUS derives a deterministic
64-bit initial state from SHA-256 of:

```text
bootstrap_seed | evidence_kind | metric | replicate
```

A fixed 64-bit linear congruential transition then produces the resample
indices.

This makes the same plan + cohort reproducible without relying on Python's
process-global random state.

## Interval definition

The current method is:

`deterministic_nonparametric_percentile`

For each requested metric ARGUS reports:

- observed point estimate;
- lower percentile bound;
- upper percentile bound;
- confidence level;
- alpha;
- eligible sample size;
- bootstrap replicate count;
- method identifier.

Percentiles use deterministic linear interpolation over the sorted bootstrap
distribution.

## Evidence separation

Bootstrap uncertainty is computed independently for every evidence class in the
prospective study manifest.

`BROKER_CONFIRMED` and `ICARUS_PAPER_EMULATOR` observations are never pooled
by this analysis.

The result carries the evidence class and its market/broker-confirmation flags.

## Validation before resampling

Before any bootstrap computation, ARGUS revalidates:

- the prospective study manifest;
- the bootstrap plan identity;
- plan creation time;
- study cohort identity;
- execution-evidence receipts;
- receipt-plus-calibration lineage;
- source revisions;
- cohort timing;
- snapshot-age and completion-latency limits;
- study stratum minimums;
- authority flags.

If the plan or cohort was modified after registration, resampling does not run.

## Statistical boundary

These are descriptive nonparametric percentile intervals.

They are **not** automatically:

- hypothesis tests;
- p-values;
- simultaneous confidence bands;
- multiple-testing-adjusted intervals;
- causal-effect estimates;
- guarantees of future execution quality;
- proof of profitability.

Bootstrap intervals can also be unstable in small or non-representative
samples. The predeclared minimum eligible sample size is a guardrail, not a
claim of statistical sufficiency.

Future inference layers should explicitly pre-register any simultaneous-band,
hypothesis-testing, multiplicity or sequential-monitoring policy rather than
retrofit it after results are visible.

## Computational boundary

The schema requires between 200 and 10,000 bootstrap replicates.

This is an offline research path. It is not permitted on ICARUS's measured live
decision hot path.

## Authority

`execution_authorized=false`

`production_decision_authorized=false`

A narrow bootstrap interval does not authorize a new order or promote a model.
