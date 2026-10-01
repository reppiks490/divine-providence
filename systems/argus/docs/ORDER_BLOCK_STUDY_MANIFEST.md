# ARGUS prospective order-block study manifests

ARGUS now supports immutable prospective study contracts for order-block
survival research.

The implementation lives in `argus.orderblock_study`.

## Why this exists

A survival curve can be technically correct and still be scientifically weak if
the cohort is selected after outcomes are visible.

The prospective manifest fixes the major sample-selection decisions before the
cohort begins:

- study name;
- manifest creation time;
- cohort start and end;
- follow-up cutoff;
- exact lifecycle revision;
- allowed assets;
- allowed evidence tiers;
- allowed directions;
- optional fixed analysis horizon;
- allowed analysis plan.

The manifest is canonicalized and content-addressed. Input order and duplicate
configuration entries do not change its identity.

The contract identity also pins its own schema revision.

- `argus-orderblock-study-v1` is preserved for exact historical replay.
- `argus-orderblock-study-v2` adds a predeclared confidence-alpha field and
  registered Kaplan-Meier uncertainty analysis.

This prevents a future cohort-selection or uncertainty-policy code revision
from silently reinterpreting an old manifest under the same ID. The v1 payload
shape is preserved exactly so historical v1 manifest IDs continue to verify.

## Prospective lock

A manifest must be created at or before `cohort_start_ns`.

The cohort window is half-open:

`cohort_start_ns <= confirmation_time_ns < cohort_end_ns`

The follow-up cutoff must be at or after the cohort end.

## Subject inclusion

Each subject binds:

- one validated terminal survival record;
- asset ID;
- confirmation time;
- exact lifecycle revision.

Subjects are filtered only by the predeclared manifest. Exclusion reasons are
retained explicitly:

- lifecycle revision mismatch;
- asset not in manifest;
- evidence tier not in manifest;
- direction not in manifest;
- confirmation before cohort;
- confirmation at/after cohort end.

Malformed survival records fail closed even if they would otherwise be
excluded. Invalid evidence cannot hide behind an exclusion rule.

## Administrative censoring

For an included block, observable follow-up is capped by:

1. the absolute follow-up cutoff minus confirmation time; and
2. the optional predeclared analysis horizon, when present.

If the recorded terminal outcome occurs strictly after that cap, the study
record is administratively censored at the cap.

The cohort receipt stores both the administrative-censor count and the exact
sorted block IDs that were censored by this rule.

An invalidation exactly at the cap remains observed.

This prevents later information from leaking past the study's declared data
freeze or horizon.

## Cohort identity

The locked cohort is also content-addressed from:

- manifest ID;
- deterministic included records;
- explicit exclusions.

Input subject order does not change cohort identity.

Duplicate block IDs fail closed.

Manifest and cohort objects are self-verified before registered analyses run:
their schema/content must reproduce their stored content-addressed IDs. A
manually constructed or mutated dataclass cannot bypass the factory by merely
copying a manifest ID.

## Registered analyses

The v1 allowed analysis-plan entries are:

- `kaplan_meier`
- `evidence_tier_strata`

The v2 allowed entries add:

- `kaplan_meier_uncertainty`

A v2 manifest pins `confidence_alpha` with `0 < alpha < 1` before the cohort
begins. Registered uncertainty analysis must use that exact predeclared alpha;
callers cannot swap confidence levels after seeing the survival curve.

A locked cohort can only run an analysis that was declared in its own manifest.
A cohort cannot be reused under a different manifest.

## What this improves

This closes several common research loopholes:

- post-outcome cohort selection;
- silent revision mixing;
- silent evidence-tier mixing;
- changing the horizon after observing outcomes;
- using future terminal outcomes past the data cutoff;
- silently dropping malformed records.

## What this still does not prove

A prospectively locked survival study is stronger evidence, but it still does
not automatically prove:

- profitability;
- causality;
- statistical significance;
- robustness across assets or regimes;
- production readiness.

Pointwise confidence intervals are available in v2, but matched controls,
event-study return definitions, simultaneous confidence bands, hypothesis
testing and multiple-testing policy remain separate research layers.

## Authority

`execution_authorized=false`

`production_decision_authorized=false`
