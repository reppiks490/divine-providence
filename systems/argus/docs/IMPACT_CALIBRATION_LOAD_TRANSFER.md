# ARGUS load-stratified paper-to-broker calibration transfer

ARGUS now has a prospective transfer audit conditioned on execution load.

The implementation lives in
`argus.impact_calibration_load_transfer`.

## Why load stratification matters

Aggregate paper-vs-broker calibration can look acceptable even when the paper
emulator becomes optimistic as order size consumes a larger fraction of
visible opposite-side depth.

ARGUS already records:

`requested_to_visible_ratio = requested size / visible opposite-side size`

The load-transfer audit uses that pre-existing causal calibration field to test
paper-vs-broker compatibility separately across predeclared load bands.

## Prospective plan

`argus-impact-calibration-load-transfer-plan-v1` content-addresses:

- exact prospective impact-calibration study manifest ID;
- plan creation time;
- exhaustive requested-to-visible load bands;
- exact metric set;
- tolerance for every band/metric pair;
- confidence alpha;
- deterministic bootstrap replicate count;
- deterministic bootstrap seed;
- minimum eligible observations required in each evidence class, in each band,
  for each requested metric.

The plan must be created at or before the study cohort starts.

The referenced study manifest must include both:

- `BROKER_CONFIRMED`;
- `ICARUS_PAPER_EMULATOR`.

## Exhaustive load partition

Load bands must:

- begin at ratio `0.0`;
- be contiguous;
- never overlap;
- have unique labels;
- use inclusive lower bounds;
- use exclusive finite upper bounds;
- leave only the final band's upper bound open.

This prevents uncovered observations and prevents the same observation from
being counted in multiple load bands.

At most twelve bands are allowed.

## Supported metrics

The first supported bandwise metrics are:

- `mean_fill_fraction_error`;
- `mean_absolute_fill_fraction_error`;
- `mean_slippage_error_ticks`;
- `mean_absolute_slippage_error_ticks`;
- `root_mean_squared_slippage_error_ticks`;
- `slippage_underprediction_rate`.

Fill-fraction metrics can use zero-fill executions.

Slippage metrics require realized slippage. Zero-fill rows are excluded rather
than assigned invented slippage values.

## Comparison

Inside each load band and for each metric, ARGUS computes:

```text
paper_minus_broker = paper estimate - broker estimate
```

The evidence classes remain separate.

For adverse slippage metrics, a materially negative gap at high
requested-to-visible ratios can indicate that the paper emulator is more
optimistic than broker-confirmed execution specifically under heavier
liquidity load.

ARGUS reports the numeric result rather than converting it into a generic
profitability claim.

## Deterministic bandwise two-sample bootstrap

Paper and broker observations are independently resampled with replacement
inside the same predeclared load band.

For each replicate, the initial state is derived from SHA-256 of:

```text
bootstrap_seed
| load-transfer
| evidence_kind
| band_label
| metric
| replicate
```

A fixed 64-bit linear congruential transition then generates sample indices.

The result is a deterministic percentile interval for the
paper-minus-broker metric within that band.

## Predeclared tolerance gate

Every band/metric pair has its own positive tolerance.

A result reports `within_tolerance=true` only when the entire bootstrap
interval lies inside:

```text
[-tolerance, +tolerance]
```

The overall result passes only when every predeclared band/metric pair passes.

This makes it possible for low-load execution to remain compatible while a
high-load regime correctly fails.

## Evidence minimums

The plan requires at least two eligible observations in each evidence class,
inside each load band, for each requested metric.

That is a fail-closed schema floor, not a claim of statistical sufficiency.

For serious execution-quality studies, substantially larger predeclared
samples are appropriate, especially in the high-load bands where observations
may be sparse.

## Interpretation boundary

The load compatibility result is not automatically:

- a formal equivalence test;
- a multiple-comparison-adjusted familywise statement;
- proof that the paper emulator reproduces queue priority;
- proof of hidden-liquidity realism;
- proof of latency realism;
- proof of profitability;
- permission to relabel paper fills as broker-confirmed;
- permission to substitute paper evidence for broker evidence;
- permission to place an order.

A future formal conditional-equivalence protocol would need its own
prospectively registered error-rate and multiplicity controls.

## Validation before resampling

ARGUS revalidates:

- the prospective study manifest;
- locked study cohort;
- execution-evidence receipts;
- receipt-plus-calibration lineage;
- exact execution-source revisions;
- cohort timing and observation cutoff;
- snapshot-age and completion-latency limits;
- load-plan identity;
- prospective plan creation time;
- exhaustive load-band partition;
- band/metric tolerances;
- evidence-class sample-size minimums;
- authority flags.

Tampering fails closed before resampling.

## Computational boundary

The schema allows 200 through 10,000 bootstrap replicates and at most twelve
load bands.

This is offline research. It does not run on the measured ICARUS live decision
hot path.

## Authority

`execution_authorized=false`

`production_decision_authorized=false`

Passing all load-band tolerances does not authorize model promotion or a
broker order.


## Research export contract

`argus.impact_calibration_load_transfer_research_export` provides
`argus-impact-calibration-load-transfer-research-v1`.

Before export, ARGUS recomputes the registered load-stratified transfer audit.
The envelope preserves:

- study manifest and locked cohort IDs;
- load-transfer plan ID and schema;
- exact impact-model, calibration and execution-source revisions;
- exhaustive requested-to-visible load bands;
- metric set and per-band/per-metric tolerances;
- confidence alpha, deterministic seed and bootstrap replicate count;
- evidence-specific eligible sample sizes;
- paper-minus-broker estimates and percentile intervals for every band/metric;
- aggregate and per-band tolerance outcomes;
- explicit non-promotion and authority flags.

The export explicitly states that it is not a formal equivalence test, is not
multiplicity adjusted, does not provide familywise coverage, does not estimate a
causal effect, does not promote paper evidence and does not authorize broker
substitution.

Publication cannot precede cohort lock. A downstream consumer must still gate
local availability on ingestion time.

## ATHENA integration status

The load-transfer export is transport-ready, but the deterministic hub does not
contain a genuine broker-confirmed execution fixture with externally valid
lineage.

Accordingly no ATHENA happy-path driver fabricates broker evidence merely to
make this research export appear cross-system complete.

Synthetic broker-confirmed objects are confined to isolated unit tests of the
contract code path and are not emitted as empirical ATHENA advisory evidence.

This is intentional fail-closed behavior: missing broker truth remains missing
broker truth.
