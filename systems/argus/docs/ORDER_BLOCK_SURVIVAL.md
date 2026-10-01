# ARGUS order-block survival research

ARGUS now includes a retrospective survival-analysis primitive for terminal
order-block lifecycles.

The implementation lives in `argus.orderblock_survival`.

## Study unit

A survival record is created only from a lifecycle that:

- was confirmed;
- reached `INVALIDATED` or `EXPIRED`;
- has a terminal time at or after confirmation.

Duration is measured from confirmation to the terminal lifecycle event.

`INVALIDATED` is treated as the survival event.

`EXPIRED` is treated as right-censoring.

An order block that expired before it was ever confirmed is not eligible for
post-confirmation survival analysis.

## Kaplan–Meier estimator

`kaplan_meier` computes a deterministic Kaplan–Meier curve over unique
block IDs.

At each observed duration it records:

- blocks at risk immediately before that duration;
- invalidations;
- censored expiries;
- survival probability after the invalidation events.

The curve also reports:

- record count;
- invalidation count;
- censor count;
- observed median survival duration when the curve reaches 0.5;
- restricted mean survival duration through the longest observed duration.

Censoring and invalidation at the same duration are handled in the standard
event-first risk set: both are at risk immediately before that duration,
invalidation changes survival, then censoring removes follow-up.

## Stratification

The first supported descriptive strata are:

- evidence tier;
- final test-count bucket: 0, 1, or 2+ tests.

Evidence-tier separation preserves the ARGUS evidence firewall.

Final test-count stratification is explicitly retrospective because final test
count is known only after the lifecycle unfolds. It must **not** be presented
as an ex-ante predictor without a separate causal study design.

## Integrity checks

The study fails closed on:

- empty studies;
- duplicate block IDs;
- negative durations;
- invalid directions;
- invalid evidence tiers;
- impossible rejection counts;
- non-finite/negative penetration;
- inconsistent invalidation flags and terminal states.

## What this proves — and does not prove

This adds a correct descriptive survival primitive. It does not establish:

- profitability;
- causal predictive power;
- stationarity;
- transferability across assets or regimes;
- statistical significance;
- production readiness.

A real empirical study must predeclare the cohort, lifecycle revision, horizon,
asset/regime filters, threshold selection data, protected evaluation period and
multiple-testing policy before using the curve as evidence.

## Next empirical steps

Useful next additions include:

- confidence intervals / uncertainty bands;
- predeclared cohort manifests;
- event-study follow-through after first/second test;
- penetration-conditioned survival;
- regime/time-of-day stratification;
- out-of-sample calibration drift;
- comparison against matched non-block control zones.

These should remain research artifacts until independently validated.

## Authority

`execution_authorized=false`

`production_decision_authorized=false`
