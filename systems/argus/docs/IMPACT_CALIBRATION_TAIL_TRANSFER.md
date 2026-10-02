# ARGUS tail paper-to-broker calibration transfer audit

ARGUS now has a separate prospective tail-transfer layer for execution
calibration.

The implementation lives in
`argus.impact_calibration_tail_transfer`.

## Purpose

Mean calibration error can hide execution tails.

A paper emulator can look acceptable on average while materially
underrepresenting the upper tail of broker-confirmed slippage error.

The tail-transfer audit asks:

> At predeclared quantiles, how far does the paper-emulator calibration
> distribution sit from the broker-confirmed calibration distribution?

It never pools the two evidence classes.

## Prospective plan

`argus-impact-calibration-tail-transfer-plan-v1` content-addresses:

- exact impact-calibration study manifest ID;
- plan creation time;
- tail metric;
- exact quantiles;
- tolerance for every quantile;
- confidence alpha;
- deterministic bootstrap replicate count;
- deterministic bootstrap seed;
- minimum realized-slippage observations required in each evidence class.

The plan must be registered at or before the study cohort starts.

The referenced study manifest must include both:

- `BROKER_CONFIRMED`;
- `ICARUS_PAPER_EMULATOR`.

## Metrics

The first supported tail metrics are:

- `slippage_error_ticks`;
- `absolute_slippage_error_ticks`.

Rows without realized slippage are excluded.

A zero-fill execution therefore remains valid calibration evidence for
fill-fraction research, but it never becomes an invented slippage observation
for this tail analysis.

## Quantile definition

Quantiles use deterministic linear interpolation over the sorted sample.

For every predeclared quantile `q`, ARGUS computes:

```text
paper_minus_broker(q)
    = paper_quantile(q) - broker_quantile(q)
```

For adverse slippage metrics, materially negative upper-quantile differences
can indicate that paper execution is more optimistic than broker-confirmed
execution.

ARGUS reports the numeric difference rather than converting it into a generic
profitability claim.

## Deterministic two-sample bootstrap

Paper and broker observations are independently resampled with replacement.

For each quantile and replicate, the initial state is derived from SHA-256 of:

```text
bootstrap_seed
| tail-transfer
| evidence_kind
| metric
| quantile
| replicate
```

A fixed 64-bit linear congruential transition then generates sample indices.

The result is a deterministic percentile interval for the
paper-minus-broker quantile difference.

## Predeclared tolerance gate

Each quantile has its own positive tolerance.

`within_tolerance=true` only when the full bootstrap interval lies inside:

```text
[-tolerance, +tolerance]
```

The overall result is true only when every predeclared quantile passes.

This is an engineering compatibility gate.

## Interpretation boundary

The tail compatibility result is not automatically:

- a formal equivalence test;
- a distribution-free proof that the tails are identical;
- a multiple-comparison-adjusted familywise statement;
- proof of queue-position realism;
- proof of hidden-liquidity realism;
- proof of latency realism;
- proof of profitability;
- permission to substitute paper evidence for broker-confirmed evidence;
- permission to place an order.

A formal familywise equivalence protocol would require its own prospective
error-rate and multiplicity policy.

## Minimum evidence

The schema requires at least three eligible realized-slippage observations in
both evidence classes for every tail analysis.

That minimum is only a fail-closed floor. It is not a claim that three
observations are statistically sufficient for reliable tail inference.

Study designers should predeclare materially larger samples for serious
execution-quality conclusions.

## Validation before resampling

ARGUS revalidates:

- the prospective study manifest;
- locked cohort identity;
- execution-evidence receipts;
- receipt-plus-calibration lineage;
- exact execution-source revisions;
- cohort timing;
- snapshot-age and completion-latency limits;
- tail-plan identity;
- prospective plan creation time;
- quantiles and tolerances;
- realized-slippage sample-size minimums;
- authority flags.

Tampering fails closed before tail resampling.

## Computational boundary

The schema allows 200 through 10,000 bootstrap replicates and at most nine
predeclared quantiles.

This is offline research and does not run on ICARUS's live decision hot path.

## Authority

`execution_authorized=false`

`production_decision_authorized=false`

Passing every tail tolerance does not authorize model promotion or a broker
order.


## Research export contract

`argus.impact_calibration_tail_transfer_research_export` provides
`argus-impact-calibration-tail-transfer-research-v1`.

Before export, ARGUS recomputes the registered tail-transfer analysis. The
envelope preserves:

- study manifest and locked cohort IDs;
- tail-transfer plan ID and schema;
- exact impact-model, calibration and execution-source revisions;
- metric, quantiles and predeclared tolerances;
- confidence alpha, deterministic seed and bootstrap replicate count;
- paper and broker eligible sample sizes;
- observed paper-minus-broker quantile gaps;
- percentile bounds and per-quantile tolerance outcomes;
- explicit non-promotion and authority flags.

The export explicitly states that it is not multiplicity adjusted, does not
provide familywise coverage, is not a formal equivalence or hypothesis test,
and does not authorize broker substitution.

Publication cannot precede the cohort lock. Any downstream consumer must still
wait for local ingestion time before treating the packet as available.

## ATHENA integration status

The tail-transfer export is transport-ready, but no hub driver invents
broker-confirmed market fills to manufacture a successful cross-system demo.

The deterministic hub currently has paper-emulator provenance but no genuine
broker-confirmed execution fixture with externally valid lineage. Therefore the
tail-transfer export remains an ARGUS research contract until such broker
evidence exists.

Synthetic broker-confirmed objects are limited to isolated unit tests of the
contract code path and are not emitted as empirical ATHENA advisory evidence.

This preserves the evidence firewall instead of turning missing broker truth
into fabricated integration success.
