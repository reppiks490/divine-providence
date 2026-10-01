# ARGUS paper-to-broker impact-calibration transfer audit

ARGUS now has a prospective transfer-compatibility layer for asking a narrow,
important question:

> Does ICARUS paper-emulator calibration remain close enough to
> broker-confirmed calibration under tolerances chosen before the cohort starts?

The implementation lives in `argus.impact_calibration_transfer`.

## Why this layer exists

Paper-emulator fills are useful for development and shadow research, but their
execution quality can be materially more optimistic than real broker fills.

The execution-evidence firewall already prevents paper fills from being labeled
as broker-confirmed. The transfer audit goes one step further by quantifying the
gap between the two evidence classes without pooling them.

A small paper/broker gap can support further research. It does not upgrade paper
evidence into broker evidence.

## Prospective plan

`argus-impact-calibration-transfer-plan-v1` is content-addressed and pins:

- exact impact-calibration study manifest ID;
- plan creation time;
- confidence alpha;
- bootstrap replicate count;
- deterministic bootstrap seed;
- minimum eligible observations required in each evidence class;
- exact metric set;
- exact tolerance for every metric.

The plan must be created at or before the study cohort starts.

The referenced study manifest must predeclare both:

- `BROKER_CONFIRMED`;
- `ICARUS_PAPER_EMULATOR`.

## Metrics

The first supported metrics are:

- `mean_fill_fraction_error`;
- `mean_absolute_fill_fraction_error`;
- `mean_slippage_error_ticks`;
- `mean_absolute_slippage_error_ticks`;
- `root_mean_squared_slippage_error_ticks`;
- `slippage_underprediction_rate`.

Fill-fraction metrics use all eligible calibration rows.

Slippage metrics use only rows with realized slippage. Zero-fill rows are never
assigned invented slippage values.

## Comparison direction

For every metric ARGUS computes:

```text
paper_minus_broker = paper estimate - broker estimate
```

Negative values therefore mean the paper estimate is lower than the
broker-confirmed estimate for that metric.

For an adverse-execution metric such as mean slippage error, a materially
negative paper-minus-broker value can indicate paper optimism.

Interpretation remains metric-specific; ARGUS does not convert the sign into a
generic profitability claim.

## Deterministic two-sample bootstrap

Broker and paper rows are resampled independently, with replacement, inside
their own evidence classes.

For each metric and replicate, the initial pseudorandom state is derived from
SHA-256 of:

```text
bootstrap_seed | transfer | evidence_kind | metric | replicate
```

A fixed 64-bit linear congruential transition then produces the sample indices.

The reported interval is a deterministic percentile interval for the
paper-minus-broker statistic.

The two evidence classes are never pooled.

## Predeclared compatibility tolerance

Each metric has a positive tolerance chosen before the cohort starts.

A metric reports `within_tolerance=true` only when the entire bootstrap
interval lies inside:

```text
[-tolerance, +tolerance]
```

The overall result is true only when every predeclared metric satisfies its own
tolerance.

This is deliberately conservative as an engineering compatibility gate.

## What within_tolerance does not mean

The compatibility flag is not automatically:

- a formal statistical equivalence test;
- proof that paper and broker distributions are identical;
- proof that the paper emulator reproduces queue priority;
- proof of hidden-liquidity realism;
- proof of latency realism;
- proof of profitability;
- permission to substitute paper evidence for broker evidence;
- permission to send a new order.

A future formal equivalence-testing layer would need its own prospective
hypotheses, margins, error-rate control, and validation protocol.

## Validation before comparison

Before transfer analysis runs, ARGUS revalidates:

- study manifest identity;
- study cohort identity;
- execution-evidence receipts;
- receipt-plus-calibration lineage;
- exact execution-source revisions;
- cohort timing and observation cutoff;
- study latency/snapshot limits;
- transfer-plan identity;
- prospective transfer-plan creation time;
- metric tolerances;
- evidence-class sample-size minimums;
- authority flags.

Tampering with the plan or cohort fails closed before resampling.

## Computational boundary

The schema allows 200 through 10,000 bootstrap replicates.

This is offline research. It is not a live ICARUS decision-path computation.

## Authority

`execution_authorized=false`

`production_decision_authorized=false`

Even a fully compatible transfer audit does not authorize model promotion or a
broker order.


## Research export contract

`argus.impact_calibration_transfer_research_export` provides
`argus-impact-calibration-transfer-research-v1`.

Before export it recomputes the registered transfer audit, so manifest, cohort,
execution-receipt, calibration-lineage and transfer-plan validation all run
again.

The envelope preserves:

- manifest, cohort and transfer-plan IDs;
- impact-model and calibration revisions;
- exact execution-source revisions;
- confidence alpha, deterministic seed and bootstrap replicate count;
- predeclared metric tolerances;
- broker and paper eligible sample sizes by metric;
- paper-minus-broker estimates and percentile intervals;
- per-metric and aggregate tolerance outcomes;
- explicit non-promotion and authority flags.

Publication cannot precede the locked cohort. A downstream consumer must still
gate local visibility on ingestion time.

## ATHENA integration status

The export contract is transport-ready, but no always-green hub driver
fabricates broker-confirmed market fills merely to exercise the happy path.

The current deterministic hub fixtures have genuine paper-emulator provenance
but no genuine broker-confirmed execution source. Therefore the transfer export
remains an ARGUS research contract until a broker-backed fixture or recorded
broker-confirmed dataset with valid lineage is available.

Synthetic broker rows may be used inside isolated unit tests to exercise the
contract code path, but they are explicitly test fixtures and are not emitted
as empirical ATHENA research evidence.

This is intentional fail-closed behavior: lack of broker evidence is represented
as lack of broker evidence, not silently repaired by relabeling paper fills.
