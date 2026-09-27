# ICARUS COMPLETE WORK PRODUCT — ALL-IN-ONE EXPORT

This file concatenates the Markdown work product in the ZIP package.


---

# FILE: 00_READ_ME_FIRST.md

# ICARUS Complete Work Product — 2026-09-24

This package is the complete handoff for the ICARUS empirical research / architecture loop performed in this ChatGPT thread through the current stopping point.

## Truth boundary

This package distinguishes five different states:

1. **WRITTEN TO REPOSITORY** — documentation/handoff artifacts actually committed to the GitHub integration branch.
2. **VERIFIED BY DIRECT REPO INSPECTION** — claims supported by direct inspection of the pinned repository revision.
3. **VERIFIED EXTERNAL/DATA CAPABILITY** — provider/literature facts observed through connected tools.
4. **DESIGNED / PLANNED** — architecture and implementation contracts that have not yet been implemented.
5. **NOT TESTED / NOT IMPLEMENTED** — explicitly listed so nothing is accidentally represented as completed.

## Repository state

Repository: `reppiks490/Icarus`

Pinned main revision inspected:
`007e70189945b8e112904cf92b2b1a12e43792d6`

Integration branch created:
`icarus-loop-integration-2026-09-24`

Current branch head after README-preservation correction:
`8e2292b372978ae2fb25abc99802f3f7456961ce`

Draft PR:
`https://github.com/reppiks490/Icarus/pull/20`

PR status at creation:
- open
- draft
- 2 commits ahead of main
- 14 changed files
- 1,386 additions
- 0 deletions
- no engine/strategy/runtime source files changed by this loop handoff

`execution_authorized=false`

## What is inside this ZIP

- Current state and resume checkpoint
- Progressive S3 empirical-edge registry
- Attempt ledger
- Direct repository audit
- Event/macro defect audit
- XGBoost5 lineage findings
- Correlation/dependence findings
- Carry/data-source unblocking work
- Provider capability matrix
- S4 point-in-time Curve Research Plane design
- Test-first implementation plan
- Architectural rulings that corrected the implementation plan
- Proposed code interfaces and test cases
- Exact repo branch/commit/PR receipt
- Actual verification performed
- Explicit list of tests that were NOT run
- Intake protocol for the other loops
- Continue point for this same loop
- SHA-256 manifest for package integrity

## Most important current rule

The system must preserve:

`Observable market state != estimator != predictive relationship != incremental alpha != executable edge`

No connected plugin, attractive backtest, composite score, or correlated confirmation is allowed to skip those layers.


---

# FILE: 01_MASTER_HANDOFF.md

# ICARUS Master Handoff

## Purpose

Expand ICARUS by discovering, decomposing, falsifying, stress-testing, and architecting quantitative futures edges without manufacturing claims, duplicating evidence, introducing temporal leakage, or granting execution authority prematurely.

The work moved from broad S3 empirical edge discovery toward S4 Architecture Extraction Forge.

## Governing control state

- Pipeline schema: `icarus-pipeline-v1`
- Policy: `icarus-control-v1`
- Pinned repo revision: `007e70189945b8e112904cf92b2b1a12e43792d6`
- `MULTIPLE_TESTING_STATUS=UNCONTROLLED`
- `execution_authorized=false`
- Next major stage: `ARCHITECTURE_EXTRACTION_FORGE`

## S3 families covered

The loop researched or audited:

- trend / time-series momentum
- order flow / queue imbalance
- commodity carry / term structure / basis
- variance risk premium
- intraday / session effects
- macro/event behavior
- cross-market lead/lag
- short-horizon reversal
- basis reversal
- liquidity provision / market making
- regime conditioning
- dispersion / correlation / conditional dependence
- confluence / evidence independence
- trained-model versus hand-built-composite lineage
- BTC perpetual funding as a separate mechanism

## Major conclusions

### No edge has reached full empirical promotion

No ICARUS edge independently satisfied the complete promotion requirements for `EMPIRICALLY_SUPPORTED`.

### Multiple testing remains uncontrolled

The effective trial universe must include failed and abandoned attempts, not only surviving variants.

### XGBoost5 is not trained XGBoost

Direct repository inspection established that the Pulse `XGBoost5` path is a hand-built `DERIVED_COMPOSITE` built from existing indicators such as ADX, Hurst, FDI, supply/demand distance, cycle state, and `rate_regime`.

The separate trainable XGB slot in `icarus_engine/trainers/xgb_slot.py` still raises `NotImplementedError`.

The active baseline trainer is logistic regression.

### Correlation is not causal/predictive authority

The current ICARUS correlation tooling correctly treats correlation as association. Research formalized:

`Correlation != independence != lead/lag != directional alpha`

and the architecture ladder:

`Association -> Risk State -> Predictive Lead -> Incremental Alpha`

### Event/calendar semantics contain verified defects

The current event research path has defects involving:

- reversed asymmetric event-window semantics
- hard-coded UTC timing for U.S. releases across DST
- current `fomc` / `any_macro` redundancy under the seed-only FOMC path
- event scope/asset not fully enforced
- realized surprise values potentially exposed to pre-release bars in broader event annotation

The current logistic trainer does not consume `surprise_abs`, so that specific leakage risk should not be falsely described as contamination of current fitted logit models.

### Safer point-in-time semantics already exist

`icarus_engine/advisory.py` contains stronger concepts such as source constraints, asset IDs, observed/published/received ordering, and `as_of` queries. The S4 event architecture should reuse these semantics rather than inventing a competing provenance system.

### True commodity carry was partially unblocked for GC

The data state for GC carry moved from fully `DATA_BLOCKED` toward `PARTIAL` because connected sources demonstrated:

- point-in-time explicit futures contract metadata
- contract-specific historical futures prices / settlements
- historical XAU/USD capability
- historical Treasury-rate capability
- independent current metals spot cross-checks

But the current ICARUS metals runtime path still does not provide genuine term structure.

### Continuous/front symbols cannot identify carry

`GC=F`, `GC1!`, back-adjusted or stitched continuous series are not substitutes for a simultaneous explicit maturity cross-section.

This claim was rejected:

`S3-CARRY-CONTINUOUS-001 — continuous contract alone identifies commodity carry`

### Existing roll logic is not a metals curve engine

Direct repo inspection found explicit `ContractRoll` logic centered on NQ/ES/YM, while GC/SI/PL/PA are configured differently and cannot safely inherit the same semantics as a research term-structure layer.

### BTC funding stays separate

Current BTC perpetual funding was observable through Bybit, but an adequate historical point-in-time funding series was not established in this cycle.

Commodity carry, commodity convenience-yield hypotheses, and crypto perpetual funding remain separate mechanisms.

## Current S4 architecture

A point-in-time research-only `CurveSnapshot` layer was designed.

The intended information path is:

External providers
-> provider adapters
-> point-in-time synchronizer
-> immutable CurveSnapshot
-> independent estimators
-> falsification / ablation laboratory
-> evidence registry

There is no allowed direct path:

`CurveSnapshot -> Pulse`

at this stage.

## Core fail-closed invariant

`Uncertainty can reduce authority, but can never increase it.`

Missing data, source disagreement, temporal ambiguity, estimator instability, uncontrolled multiple testing, or execution uncertainty must reduce confidence or block promotion.


---

# FILE: 02_ACTIVITY_RECEIPT.md

# Activity Receipt

## Repository actions actually performed

1. Directly inspected the public GitHub repository `reppiks490/Icarus`.
2. Pinned work to main revision:
   `007e70189945b8e112904cf92b2b1a12e43792d6`.
3. Created integration branch:
   `icarus-loop-integration-2026-09-24`.
4. Created the initial documentation tree commit:
   `7577ebb9c025d15e6cd6493cae24a1e434f96ca5`.
5. Corrected README handling to preserve all pre-existing README text and make the change additive.
6. Resulting branch head:
   `8e2292b372978ae2fb25abc99802f3f7456961ce`.
7. Opened Draft PR #20:
   `https://github.com/reppiks490/Icarus/pull/20`.

## Files written to the integration branch

- `HANDOFF_LOG.md`
- `ICARUS_LOOP_INDEX.md`
- `README.md` (additive link section only after correction)
- `docs/icarus/README.md`
- `docs/icarus/audits/REPO_EVIDENCE_2026-09-24.md`
- `docs/icarus/decisions/ARCHITECTURAL_RULINGS_2026-09-24.md`
- `docs/icarus/handoffs/CURRENT_LOOP_HANDOFF_2026-09-24.md`
- `docs/icarus/handoffs/INBOX_PROTOCOL.md`
- `docs/icarus/providers/PROVIDER_CAPABILITY_MATRIX.md`
- `docs/icarus/research/ATTEMPT_LEDGER.md`
- `docs/icarus/research/S3_EMPIRICAL_EDGE_REGISTRY.md`
- `docs/icarus/status/CURRENT_STATE.md`
- `docs/superpowers/plans/2026-09-24-icarus-curve-research.md`
- `docs/superpowers/specs/2026-09-24-icarus-curve-research-design.md`

## GitHub verification actually performed

A compare operation against pinned main showed:

- branch status: ahead
- ahead by: 2 commits
- behind by: 0
- changed files: 14
- PR additions: 1,386
- PR deletions: 0
- no engine/strategy/runtime source path changed in that documentation handoff

The canonical entry point, current-state file, S4 design spec, and implementation plan were re-fetched from the integration branch after write and spot-read.

## README correction

Initial branch write unintentionally rewrote some pre-existing README wording while adding the loop index.

This was detected during verification.

A second commit restored the original README body and only appended the ICARUS loop-integration section.

## Production changes

No trading strategy, Pine code, broker path, runtime engine, execution sizing, or activation state was changed by this loop handoff.

`execution_authorized=false`.


---

# FILE: 03_TEST_AND_VERIFICATION_STATUS.md

# Test and Verification Status

This file is intentionally strict.

## What WAS verified

### Repository evidence

Direct inspection was performed on relevant files including:

- `icarus_engine/strategy/pulse.py`
- `icarus_engine/trainers/xgb_slot.py`
- `icarus_engine/trainers/run.py`
- `icarus_engine/trainers/logit.py`
- `icarus_engine/spec.py`
- `icarus_engine/trainers/dataset.py`
- `icarus_engine/correlations.py`
- `icarus_engine/research.py`
- `icarus_engine/events/calendar.py`
- `icarus_engine/events/candidate.py`
- `icarus_engine/events/__init__.py`
- `icarus_engine/advisory.py`
- `icarus_engine/contracts.py`
- `icarus_engine/assets.py`
- `tests_engine/test_events.py`
- `tests_engine/test_fomc.py`
- `tests_engine/test_futures.py`
- `tests_engine/test_market_sources.py`
- `EVENTS_GROK.md`
- `history/events/macro.example.csv`

### Provider/data capability probes

Observed during the research cycle:

- Massive explicit GC contract metadata capability
- Massive contract-specific historical aggregate capability
- Massive futures live snapshot entitlement failure on connected plan
- FMP historical Treasury curve capability
- Twelve Data XAU/USD capability
- StackerScan metals spot capability
- Bybit current BTCUSDT perpetual funding capability
- U.S. Gold Bureau connection blocked by IP allowlist
- Scite core literature verification followed later by monthly quota exhaustion
- DataBlue public search capability
- Runway authenticated creative workspace
- Figma authenticated design workspace

### Branch/package verification

GitHub compare operation verified documentation-only branch delta against pinned main.

## What was NOT run

The curve research Python subsystem described by the S4 plan does not exist yet in the repository.

Therefore none of these planned test commands has been run:

- `pytest tests_engine/test_curve_models.py -v`
- `pytest tests_engine/test_curve_provenance.py -v`
- `pytest tests_engine/test_curve_contracts.py -v`
- `pytest tests_engine/test_curve_synchronization.py -v`
- `pytest tests_engine/test_curve_quality.py -v`
- `pytest tests_engine/test_curve_estimators.py -v`
- `pytest tests_engine/test_curve_experiment.py -v`
- `pytest tests_engine/test_curve_isolation.py -v`

No claim is made that those tests pass.

## Full suite

This loop did not run `pytest tests_engine -q` against a newly implemented curve subsystem because no such production implementation was applied.

## Meaning

Architecture/design and research findings can be mature while implementation verification remains incomplete.

Do not conflate a detailed implementation plan with working code.


---

# FILE: 05_PACKAGE_SCOPE_AND_LIMITATIONS.md

# Package Scope and Limitations

## Included

This ZIP contains all substantive work product created in this loop:
research registry, attempt ledger, verified findings, provider findings, architecture,
implementation plan, proposed interfaces, GitHub actions/receipts, current state,
loop intake protocol, and resume point.

## Not included as raw copies

The entire Icarus repository source tree is not duplicated in this ZIP.

Reason:
the source is already durably identified by exact repository and pinned commit.
The work product records every material file inspected and the exact integration branch/PR.

## Important non-claim

No unimplemented curve-research Python module is presented as if it exists.

No unrun pytest suite is presented as passing.

No literature quota failure is converted into evidence.

No market-data entitlement failure is silently replaced with another vendor.

No execution authorization was granted.


---

# FILE: audits/REPO_EVIDENCE.md

# Direct Repository Evidence

Pinned baseline:
`reppiks490/Icarus@007e70189945b8e112904cf92b2b1a12e43792d6`

## XGBoost5 lineage

Direct inspection of `icarus_engine/strategy/pulse.py` showed the named XGBoost5 path is a fixed hand-built composite using existing transformed state rather than a fitted booster.

Direct inspection of `icarus_engine/trainers/xgb_slot.py` showed the trainable XGBoost slot still raises `NotImplementedError`.

Direct inspection of `trainers/run.py` and `trainers/logit.py` showed logistic regression is the active baseline.

## Trainer features

`icarus_engine/spec.py` active `FEATURE_KEYS`:
`ret_1, ret_3, body, range, close_loc, tide, run, fomc, any_macro`.

Optional keys such as `cpi, nfp, earnings, vix_z, tnx_z, dxy_z` are not the same as active baseline trainer inputs.

## Correlation

`icarus_engine/correlations.py` and `research.return_correlation` explicitly preserve point-in-time constraints and describe the calculation as association rather than causality/lead.

## Event defects

EVT-WINDOW-001:
documented asymmetric event window and implemented predicate reverse the intended pre/post asymmetry.

EVT-TIME-002:
fixed UTC release hours are unsafe for U.S. releases defined in Eastern Time across DST and half-hour release times.

EVT-REDUNDANCY-003:
seed-only FOMC trainer path makes active `fomc` and `any_macro` duplicate-source features.

EVT-SCOPE-004:
event asset/scope is collected but not fully enforced in the broader path.

EVT-SURPRISE-005:
realized surprise values can exist in a window that includes pre-event bars. Current logit does not consume `surprise_abs`; this is an interface-level leakage risk, not evidence that the current fitted logit is contaminated.

## Existing safer semantics

`icarus_engine/advisory.py` already models observed/published/received ordering and asset scoping more safely.

## Futures curve gap

`icarus_engine/contracts.py` explicit roll logic is centered on NQ/ES/YM.

GC/SI/PL/PA cannot be treated as if the current continuous/front symbol path were a genuine simultaneous term-structure curve.


---

# FILE: decisions/ARCHITECTURAL_RULINGS.md

# Architectural Rulings

R1 — Contract metadata itself is point-in-time:
require both `definition_asof <= snapshot_date` and `definition_available_at <= snapshot_asof`.

R2 — Financing units are canonical decimal-per-year:
5.18% -> 0.0518.

R3 — Financing value has one authoritative source:
derive the rate from the canonical observation rather than duplicate numeric state.

R4 — No naked liquidity floats:
volume/OI/spread must preserve point-in-time provenance or remain absent in Phase A.

R5 — Source agreement does not automatically create a synthetic averaged market price.

R6 — Synchronization is semantic-specific:
settlement↔settlement, quote↔quote, and futures↔spot need different policies.

R7 — Domain validation depends on semantic:
futures/spot prices must be positive; rates can be zero or negative.

R8 — Test helpers must be explicit:
a dedicated test support module should provide deterministic builders.

R9 — Combination contracts excluded from Phase A:
accept outright `type="single"` only.

R10 — Provider capability and provider health are separate.

R11 — Strategy boundary stays hard:
no direct `CurveSnapshot -> Pulse` integration in S4.

Governing principle:

`provider availability != data validity != estimator validity != trading authority`


---

# FILE: external_research/RESEARCH_EVIDENCE_NOTES.md

# External Research / Data Evidence Notes

## Commodity carry

Verified literature during the cycle included:

- Gorton, Hayashi & Rouwenhorst — commodity futures returns, basis and inventories / theory of storage.
- Koijen, Moskowitz, Pedersen & Vrugt — carry as an ex-ante characteristic across asset classes including commodities.

The literature supports researching carry. It does not automatically validate any specific ICARUS estimator or production strategy.

## Macro announcement behavior

The research cycle also checked literature and primary timing sources supporting:
- scheduled macro releases can cause concentrated futures/FX price discovery and volatility;
- surprise content matters;
- responses can be state-dependent;
- scheduled event knowledge is not the same thing as released outcome/surprise/directional alpha.

## Official timing lesson

FOMC statements are scheduled in Eastern Time and therefore map differently to UTC in winter versus summer.

Major BLS releases such as CPI and Employment Situation are commonly scheduled at 8:30 Eastern, so integer-hour UTC approximations are inadequate.

## Carry/data-source lesson

Point-in-time explicit GC contract metadata plus synchronized explicit-maturity prices can support real curve research.

A continuous front symbol cannot.

## Evidence doctrine

Primary exchange/official sources and reproducible research outrank secondary summaries.

When a source connector was unavailable or quota-limited, the cycle recorded the limitation instead of treating it as supporting or contradicting evidence.


---

# FILE: handoffs/CONTINUE_POINT.md

# Continue Point

The current loop should resume only after incoming loop handoffs are ingested and reconciled.

## Next sequence

1. Import each loop handoff under `docs/icarus/handoffs/inbox/`.
2. Preserve producer/source identity and pinned revision.
3. Deduplicate identical/derived claims.
4. Flag revision/config/evidence conflicts.
5. Merge compatible evidence into the canonical S3 registry.
6. Do not reset the attempt ledger.
7. Produce one dated convergence record.
8. Freeze the combined S3 state.
9. Re-evaluate S4 dependencies and blockers.
10. Resume Architecture Extraction Forge.

## Current highest-value architecture

Point-in-time futures curve research remains the most mature next S4 unit, unless incoming loops reveal a conflicting higher-priority dependency.

## Do not do

- do not merge the draft PR prematurely
- do not rewrite Pulse to add carry
- do not convert continuous GC into fake term structure
- do not count XGBoost5 as an independent ML vote
- do not count duplicate macro/event features independently
- do not reset failed research attempts


## Continuation work completed after the first package build

The integration branch was extended with:
- `docs/icarus/handoffs/inbox/README.md`
- `docs/icarus/handoffs/convergence/CONVERGENCE_TEMPLATE.md`
- an updated `ICARUS_LOOP_INDEX.md`

Verified branch head after this continuation:
`2f50a6bbc6b35eb13b2a8c458459c4ceee4944c2`

Verified compare against pinned main:
- ahead by 5 commits
- behind by 0
- 16 changed files


---

# FILE: handoffs/CONVERGENCE_TEMPLATE.md

# ICARUS Cross-Loop Convergence Record — TEMPLATE

## Control header

```
CONVERGENCE_ID=
CREATED_AT=
BASELINE_MAIN_REVISION=
INTEGRATION_BRANCH=
PIPELINE_POLICY_VERSION=icarus-control-v1
PIPELINE_SCHEMA=icarus-pipeline-v1
EXECUTION_AUTHORIZED=false
```

## Source handoffs consumed

| Handoff | Source loop | Producer | Pinned revision | Status |
|---|---|---|---|---|

## Claim reconciliation

| Canonical claim ID | Incoming claim | Source | Disposition | Evidence origin | Notes |
|---|---|---|---|---|---|

## Attempt-ledger delta

```
ATTEMPTS_BEFORE=
ATTEMPTS_ADDED=
ATTEMPTS_AFTER=
MULTIPLE_TESTING_STATUS=
```

## Required reconciliation sections

- duplicate suppression
- revision conflicts
- configuration conflicts
- evidence conflicts
- canonical S3 registry delta
- S4 architecture delta
- blockers after convergence
- final pipeline disposition
- smallest decisive resume action

No new execution authority is created by convergence alone.


---

# FILE: handoffs/INBOX_PROTOCOL.md

# Other Loop Intake Protocol

Destination for each incoming loop:

`docs/icarus/handoffs/inbox/YYYY-MM-DD_<loop-name>_<source>.md`

Required metadata:
- SOURCE_LOOP
- SOURCE_CHAT_OR_WORKSTREAM
- PRODUCER
- CAPTURE_DATE
- PINNED_REPO_REVISION
- POLICY_VERSION
- EXECUTION_AUTHORIZED=false

Required sections:
1. Purpose
2. What was actually done
3. Files/repo objects inspected
4. Verified findings
5. Hypotheses
6. Rejected/failed attempts
7. Open conflicts
8. Data/source limitations
9. Code changes actually made
10. Tests actually run
11. Exact next action
12. Artifact/file references

Reconciliation states:
COMPATIBLE
DUPLICATE
DERIVED_DUPLICATE
REVISION_CONFLICT
CONFIG_CONFLICT
EVIDENCE_CONFLICT
STALE
UNVERIFIED
BLOCKED

Never silently overwrite an earlier failed attempt or merge incompatible revisions.


---

# FILE: handoffs/inbox_README.md

# ICARUS Loop Handoff Inbox

This directory is the landing zone for the remaining ICARUS/AEGIS/DAEDALUS/NEXUS/HELIOS loop handoffs before convergence.

## One file per source loop

Use:

`YYYY-MM-DD_<loop-name>_<source>.md`

Never overwrite another loop's handoff. Never fold two source loops into one file before convergence.

## Required metadata

Every handoff begins with:

```
SOURCE_LOOP=
SOURCE_CHAT_OR_WORKSTREAM=
PRODUCER=
CAPTURE_DATE=
PINNED_REPO_REVISION=
POLICY_VERSION=
EXECUTION_AUTHORIZED=false
```

## Import discipline

Preserve the raw handoff first. Mark each claim during convergence as one of:

`COMPATIBLE, DUPLICATE, DERIVED_DUPLICATE, REVISION_CONFLICT, CONFIG_CONFLICT,
EVIDENCE_CONFLICT, STALE, UNVERIFIED, BLOCKED`.

Preserve failed/rejected attempts and never reset the global attempt ledger.


---

# FILE: providers/PROVIDER_CAPABILITY_MATRIX.md

# Provider Capability Matrix

| Provider | Observed capability | Limitation | Research role |
|---|---|---|---|
| Massive | explicit futures contract metadata, historical contract aggregates/settlements | requested live futures snapshot not entitled | explicit maturity reconstruction |
| FMP | historical U.S. Treasury curve | proxy only for gold financing | financing input candidate |
| Twelve Data | XAU/USD quote/history capability | preserve timestamp/spot convention | spot source |
| StackerScan | current metals spot observations | current != historical dataset | spot cross-check |
| U.S. Gold Bureau | connector exists | IP allowlist block during cycle | unavailable |
| Bybit | current BTCUSDT funding | adequate historical series not established | separate crypto research |
| Scite | core literature verified | monthly MCP quota later exhausted | literature verification |
| DataBlue | public discovery/search | not primary market truth | discovery |
| Runway | authenticated creative workspace | no quantitative evidentiary role | excluded from alpha evidence |
| Figma | authenticated design workspace | no quantitative evidentiary role | documentation/design |

Provider health and provider capability are separate concepts.


---

# FILE: repo_evidence/FILES_INSPECTED.md

# Repository Files Inspected During This Loop

The following repository areas materially informed the conclusions:

- icarus_engine/strategy/pulse.py
- icarus_engine/trainers/xgb_slot.py
- icarus_engine/trainers/run.py
- icarus_engine/trainers/logit.py
- icarus_engine/trainers/dataset.py
- icarus_engine/spec.py
- icarus_engine/research.py
- icarus_engine/research_service.py
- icarus_engine/correlations.py
- icarus_engine/events/calendar.py
- icarus_engine/events/candidate.py
- icarus_engine/events/__init__.py
- icarus_engine/advisory.py
- icarus_engine/contracts.py
- icarus_engine/assets.py
- icarus_engine/market_sources.py
- tests_engine/test_events.py
- tests_engine/test_fomc.py
- tests_engine/test_futures.py
- tests_engine/test_market_sources.py
- tests_engine/test_drop_candidates.py
- EVENTS_GROK.md
- history/events/macro.example.csv
- README.md
- HANDOFF_LOG.md
- ASTRA_HANDOFF.md
- GOAL.md
- SPEC.md
- instruction.txt

This package does not duplicate entire source files. It preserves the exact pinned revision and file list needed to recover them from GitHub.


---

# FILE: repo_exact/docs/superpowers/plans/2026-09-24-icarus-curve-research.md

# ICARUS Curve Research Plane — Implementation Plan

> Implementation method originally selected: Native/inline after subagent-driven was unavailable in chat.
> This file is the executable build contract. It does not claim implementation occurred.

**Goal:** Implement a deterministic, research-only, point-in-time GC futures-curve subsystem without strategy/runtime influence.

**Spec:** `docs/superpowers/specs/2026-09-24-icarus-curve-research-design.md`

## Global constraints
- `execution_authorized=false`.
- No Pulse/entry/exit/sizing/alert/broker mutation.
- No modification to existing NQ/ES/YM roll behavior.
- Explicit maturity contracts only.
- `available_at <= snapshot_asof` for every admissible observation.
- Contract metadata itself is point-in-time.
- Provider failure is explicit and fail-closed.
- No third-party Python dependency is required for Phase A.
- Deterministic tests do not use live internet.
- NaN/infinity are forbidden in canonical payloads.
- Provider agreement is quality evidence, not permission to average.
- Financing rates are normalized to decimal-per-year.
- Liquidity data without point-in-time provenance stays absent.
- Semantic synchronization policies are type-specific.
- Production integration remains out of scope.

## Review focus
1. historically dated but later-available records;
2. future contract-definition/listing leakage;
3. settlement/spot semantic skew;
4. provider disagreement and access failures;
5. strategy/runtime import isolation.

## File map
Create:
```
icarus_engine/curve_research/
    __init__.py
    errors.py
    models.py
    provenance.py
    contracts.py
    synchronize.py
    quality.py
    estimators.py
    experiment.py
```

Tests:
```
tests_engine/
    curve_test_support.py
    test_curve_models.py
    test_curve_provenance.py
    test_curve_contracts.py
    test_curve_synchronization.py
    test_curve_quality.py
    test_curve_estimators.py
    test_curve_experiment.py
    test_curve_isolation.py
    fixtures/curve_gc_2026_09_24.json
```

Do not modify initially:
`icarus_engine/runtime.py`,
`icarus_engine/contracts.py`,
`icarus_engine/strategy/pulse.py`,
`icarus_engine/emulator.py`.

---

## Task 1 — Immutable domain models and typed failures

### Produce
```python
PriceSemantic
SourceStatus
Observation
ContractDefinition
CurveLeg
FinancingPoint
CurveSnapshot
CurveResearchError
TemporalViolation
ContinuousContractError
ContractLifecycleViolation
InvalidCurveTopology
SynchronizationFailure
SourceDisagreement
UnsupportedContractType
SourceUnavailable
```

### RED tests
- Observation is frozen.
- nonfinite values rejected.
- `available_at < observed_at` rejected.
- positive price semantics reject zero/negative values.
- reference rates may be zero or negative.
- financing units must be `DECIMAL_PER_YEAR`.

### Corrected data model
`FinancingPoint` stores one authoritative `Observation`; `annual_rate`
is derived from `observation.value`.

Do not put naked volume/OI/spread floats into `CurveLeg` Phase A.

### Verify
`pytest tests_engine/test_curve_models.py -v`

---

## Task 2 — Canonical provenance and deterministic hashing

### Produce
```python
canonical_payload(value)
canonical_json(value)
canonical_digest(value)
```

Normalize dataclasses, enums, dates/times, tuples/lists, mapping order and finite floats.
Canonical JSON uses sorted keys, compact separators and `allow_nan=False`.

### RED tests
- mapping key order cannot change digest;
- date/tuple normalization deterministic;
- NaN/infinity rejected;
- one-byte semantic change changes digest.

### Verify
`pytest tests_engine/test_curve_provenance.py -v`

---

## Task 3 — Explicit contract validation

### Produce
```python
validate_contract(contract, *, root, asof)
ordered_contracts(contracts, *, root, asof)
```

### Required rules
Reject:
- `GC=F`, `GC1!` and continuous aliases;
- wrong root;
- non-`single` combo/spread contracts;
- inactive lifecycle;
- `definition_asof > snapshot_date`;
- `contract.available_at > snapshot_asof`;
- duplicate settlement maturity.

Return contracts sorted deterministically by settlement date then ticker.

### Verify
`pytest tests_engine/test_curve_contracts.py -v`

---

## Task 4 — Point-in-time snapshot construction

### Produce
`SyncPolicy` and `build_snapshot(...)`.

### Required behavior
- Build from explicit contracts + exact contract prices.
- Price records must be available by asof.
- Reject stale observations.
- Reject duplicate contract-price observations.
- Enforce accepted price semantics.
- Enforce minimum maturities.
- Synchronization policy is semantic-specific; do not use one universal skew.
- Spot and financing legs preserve their own admissibility rules.
- Financing observations must already be normalized to decimal-per-year.

### Critical RED test
A record with `observed_at < asof` but `available_at > asof` must fail.

### Verify
`pytest tests_engine/test_curve_synchronization.py -v`

---

## Task 5 — Source disagreement and curve quality

### Produce
```python
DisagreementState
SourceComparison
compare_source_values(...)
```

States:
`CONSISTENT, MINOR_DISLOCATION, MATERIAL_DISLOCATION`
plus semantic incomparability/staleness when needed.

### Rule
Initial implementation does **not** manufacture a blended consensus value.
The result reports disagreement only.

### RED tests
- material difference is surfaced;
- one source cannot claim consensus;
- semantically incomparable records fail comparison before numeric tolerance.

### Verify
`pytest tests_engine/test_curve_quality.py -v`

---

## Task 6 — Research-only curve estimators

### Produce
```python
raw_slope(snapshot, near=0, far=1)
annualized_log_slope(snapshot, near=0, far=1)
spot_basis(snapshot, leg=0)
annualized_log_basis(snapshot, leg=0)
financing_adjusted_log_basis(snapshot, leg=0, ...)
```

### Rules
- actual maturity distance drives annualization;
- spot is required for basis estimators;
- financing tenor mapping has an explicit maximum mismatch;
- financing-adjusted residual is **not** labeled convenience yield;
- estimator output carries no BUY/SELL semantics.

### Verify
`pytest tests_engine/test_curve_estimators.py -v`

---

## Task 7 — Deterministic GC fixture and test support

### Create
`tests_engine/curve_test_support.py` with:
```python
make_contract(...)
make_observation(...)
make_financing_point(...)
make_snapshot(...)
load_curve_fixture(...)
```

No production logic belongs in this file.

Create sanitized fixture:
`tests_engine/fixtures/curve_gc_2026_09_24.json`

The fixture may contain known contract metadata such as GCV6/GCX6/GCZ6 only when
source semantics and availability are explicit. Do not invent futures prices.

### RED tests
- identical frozen fixture -> identical digest;
- one revision/value change -> different digest.

### Verify
`pytest tests_engine/test_curve_provenance.py tests_engine/test_curve_synchronization.py -v`

---

## Task 8 — Research attempt envelope

### Produce
Immutable `CurveResearchReceipt` and `build_receipt(...)`.

Fields include:
```
cycle_id
execution_instance_id
claim_id
attempt_id
pinned_revision
source_set
snapshot_digest
estimator_id
data_sufficiency_status
estimator_validity_status
ablation_readiness_status
redundancy_status
multiple_testing_status
execution_authorized=false
```

Builder exposes no execution-authorization override.

### Verify
`pytest tests_engine/test_curve_experiment.py -v`

---

## Task 9 — Strategy/runtime isolation gate

Create `tests_engine/test_curve_isolation.py`.

### Required tests
- `runtime.py`, `emulator.py`, and `strategy/pulse.py` do not import
  `curve_research`;
- constructing a snapshot causes no engine/config/filesystem side effect;
- no broker/bridge/trading object is reachable from the curve package's public API.

### Verify
`pytest tests_engine/test_curve_isolation.py -v`

---

## Task 10 — Full verification

Run and read actual output:

```bash
pytest   tests_engine/test_curve_models.py   tests_engine/test_curve_provenance.py   tests_engine/test_curve_contracts.py   tests_engine/test_curve_synchronization.py   tests_engine/test_curve_quality.py   tests_engine/test_curve_estimators.py   tests_engine/test_curve_experiment.py   tests_engine/test_curve_isolation.py -v

pytest tests_engine/test_futures.py -v
pytest tests_engine/test_research.py -v
pytest tests_engine -q
python -m compileall -q icarus_engine
git diff --check
git grep -n "curve_research" --   icarus_engine/runtime.py   icarus_engine/emulator.py   icarus_engine/strategy
```

No completion claim is permitted without fresh command evidence.

## Post-implementation research gate
Implementation does not authorize carry.

Future experiment hierarchy:
```
M0 = null
M1 = own-price baseline
M2 = M1 + raw slope
M3 = M1 + annualized log slope
M4 = M1 + spot basis
M5 = current ICARUS
M6 = current ICARUS + preregistered curve family
```

Decision quantity: `Delta_OOS = M6 - M5`.

## Rollback
Because the subsystem is isolated, an eventual implementation commit must be revertable
without persistent strategy/broker migration.

## Definition of done
The infrastructure is complete only after fresh verification proves:
- immutable point-in-time objects;
- explicit-maturity/lifecycle/metadata availability enforcement;
- semantic synchronization;
- deterministic hashing/replay;
- no silent provider averaging;
- research-only estimators;
- fail-closed receipts;
- no Pulse/runtime dependency;
- existing futures/research/full engine suite green;
- compile and diff checks green;
- `execution_authorized=false`.

This definition does not claim profitability or production readiness.


---

# FILE: repo_exact/docs/superpowers/specs/2026-09-24-icarus-curve-research-design.md

# ICARUS S4 — Point-in-Time Curve Research Plane

**Specification status:** Review Candidate / approved for planning  
**Pipeline schema:** `icarus-pipeline-v1`  
**Policy:** `icarus-control-v1`  
**Stage:** `ARCHITECTURE_EXTRACTION_FORGE`  
**Production behavior changes:** None  
**Strategy integration:** Prohibited by this specification  
**Execution authorization:** `false`

## 1. Purpose
Build a research-only, point-in-time futures-curve subsystem capable of determining
what an explicit futures term structure actually looked like using only information
available at a historical decision timestamp.

Research scope includes commodity carry, basis, curve slope, roll yield,
financing-adjusted carry, term-structure deformation, inversion, maturity dispersion,
cross-maturity liquidity, and curve-state transitions.

## 2. Primary research question
What explicit futures contracts, prices, liquidity states, spot observations,
financing observations, and metadata were legitimately knowable at historical time `t`?

## 3. Core architecture
```
Observable Market State
    != Estimator
    != Predictive Relationship
    != Incremental Alpha
    != Executable Edge
```

No layer inherits authority automatically.

## 4. Non-goals
This subsystem does not rewrite Pulse, modify entries/exits/sizing, alter broker payloads,
replace NQ/ES/YM roll behavior, add carry votes, equate contango/backwardation with direction,
infer convenience yield without adequate data, treat continuous contracts as curves, use
BTC funding as commodity financing, add ML for novelty, or tune on final holdout data.

## 5. System decomposition
Nine independently testable components:
1. provider adapters;
2. source-health registry;
3. canonical observation;
4. contract metadata plane;
5. point-in-time synchronizer;
6. immutable CurveSnapshot;
7. source-quality/disagreement plane;
8. estimator registry;
9. experiment/ablation/provenance plane.

## 6. Provider adapters
Adapters translate provider records into canonical observations. Capabilities are explicit
and separate from current access status.

## 7. Source health
Supported states include:
`AVAILABLE, PARTIAL, NOT_ENTITLED, RATE_LIMITED, AUTH_FAILED,
NETWORK_RESTRICTED, STALE, SEMANTIC_MISMATCH, UNVERIFIED`.

Failure can lower data sufficiency; it may never silently change estimator semantics,
source priority, fallback logic, or confidence.

## 8. Canonical Observation
Each observation preserves:
```
source_id
source_record_id
source_revision
instrument_id
root
contract_ticker
observation_type
price_semantic
observed_at
published_at
available_at
received_at
value
units
currency
exchange
session_id
quality_flags
```

Fundamental causality constraint:
```
available_at <= decision_asof
```

## 9. Contract metadata
A qualified contract definition preserves root, ticker, first/last trade date,
settlement date, days-to-maturity, tick/multiplier, settlement method/type,
definition_asof, definition_available_at, and source revision.

Only outright `type="single"` contracts enter Phase A.

## 10. Contract point-in-time rule
A contract participates only when:
```
first_trade_date <= snapshot_date <= last_trade_date
definition_asof <= snapshot_date
definition_available_at <= snapshot_asof
```

## 11. Continuous-contract quarantine
`GC=F`, `GC1!`, generic front aliases, back-adjusted, ratio-adjusted, and stitched
continuous series are prohibited as substitutes for a maturity curve.

## 12. Price semantics
Typed semantics:
`TRADE, BID, ASK, MID, SETTLEMENT, OFFICIAL_CLOSE, SESSION_CLOSE, VWAP, SPOT, REFERENCE_RATE`.

Estimators declare accepted semantics. Settlement cannot silently stand in for an
executable quote, and vice versa.

## 13. Point-in-time synchronization
Synchronization is semantic-specific. Same date is not sufficient to imply the same
information set. Settlement↔settlement, quote↔quote, and futures↔spot comparisons
use separately configured tolerances and session policies.

## 14. CurveSnapshot
Immutable object containing:
- schema/root/asof/constructed_at;
- explicit contract legs and maturity metadata;
- point-in-time price observations;
- optional provenance-bearing liquidity observations;
- synchronized spot;
- normalized financing curve;
- policy version;
- quality summary;
- source disagreement;
- canonical digest.

No BUY/SELL field exists.

## 15. Curve validity
Fail closed on insufficient maturities, duplicate maturity, impossible chronology,
future listing knowledge, inactive contracts, missing semantics, stale records,
post-asof availability, incompatible sessions, unresolved timezone conversion,
excessive skew, missing revision where required, inconsistent units/currency,
unsupported combo contract, continuous aliases, or invalid settlement chronology.

## 16. Multi-provider consensus
Provider disagreement is classified:
`CONSISTENT, MINOR_DISLOCATION, MATERIAL_DISLOCATION,
SEMANTICALLY_INCOMPARABLE, STALE_SOURCE, UNKNOWN`.

Initial implementation does not automatically average provider values.

## 17. Financing plane
Financing observations are independent inputs. Canonical rate units are
`DECIMAL_PER_YEAR` (5.18% -> 0.0518).

Treasury rates may be a research proxy but are not assumed equal to dealer financing,
lease rates, storage, or convenience yield.

## 18. Estimator registry
No universal `carry_score`. Initial separate estimators:
- raw maturity slope;
- annualized log slope;
- spot basis;
- annualized log basis;
- financing-adjusted basis residual;
- optional level/slope/curvature/kink/inversion families.

A financing-adjusted residual is not automatically called convenience yield.

## 19. Estimator validity
Each estimator records ID, definition, interpretation, observables, semantics,
normalization, maturity rule, finite-sample concerns, confounds, parameter family,
and validation status.

## 20. Liquidity qualification
Existence is not liquidity. Any volume/OI/spread observation must preserve
point-in-time provenance. Phase A may omit liquidity fields rather than accept
unproven naked floats.

## 21. Curve quality report
Quality can summarize temporal completeness, semantic consistency, source consistency,
maturity coverage, liquidity coverage, spot alignment, financing alignment, and
revision integrity. Quality controls research admissibility, not direction.

## 22. Experiment hierarchy
```
M0 = null
M1 = simple own-price baseline
M2 = M1 + single curve estimator
M3 = M1 + alternative curve estimator
M4 = M1 + redundancy-controlled curve family
M5 = current ICARUS baseline
M6 = M5 + qualified curve family
```
Primary quantity: `Delta_OOS = M6 - M5`.

## 23. Chronological evaluation
Allowed: expanding/rolling OOS, walk-forward, untouched holdout.
Forbidden: random temporal splits, holdout tuning, post-holdout estimator selection,
or maturity choice based on future performance.

## 24. Falsification matrix
Temporal perturbation, maturity perturbation, estimator perturbation,
leave-provider-out, settlement/quote alternates, alternate spot/rate proxies,
regime slices, roll/expiry periods, and cross-market transfer after qualification.

## 25. Null controls
Time shuffle, block permutation, lag inversion, random maturity pairing,
synthetic flat curve, and own-price-only baseline.

## 26. Redundancy control
Every feature preserves raw-observable lineage, transform lineage, family ID, and
channel class:
`PRIMARY_OBSERVABLE, TRANSFORM, DERIVED_COMPOSITE, EXTERNAL_INDEPENDENT`.

Multiple transforms of one curve are not multiple independent votes.

## 27. Incremental information
Where feasible: train-only association, MI/HSIC, mRMR, partial predictive contribution,
family-out ablation, leave-estimator-out, time-respecting permutation, blocked bootstrap.

Held-out incremental value remains the primary gate.

## 28. Multiple-testing accounting
Every tested hypothesis/variant/parameter family increments the attempt ledger.
Failures/data-source changes/market changes/cycles do not reset effective trial count.
Until adequate correction exists: `MULTIPLE_TESTING_STATUS=UNCONTROLLED`.

## 29. Execution boundary
Predictive value does not establish tradeability. Separate evaluation must cover spread,
size, liquidity by maturity, impact, commissions, latency, partial fills, queue effects,
roll, expiry, delivery risk, sessions, order type, and signal publication delay.

## 30. Capacity
```
Expected Net Edge =
Gross Predictive Edge
- Spread
- Fees
- Slippage
- Impact
- Delay Cost
```

## 31. Regime integration
Curve state may serve risk, alpha, or execution planes only after independent
qualification for that use. Risk value does not imply directional alpha.

## 32. Cross-asset separation
Commodity carry, commodity basis, convenience-yield hypotheses, BTC funding,
CME BTC basis, Treasury term premium, and equity-index basis are separate mechanisms.

## 33. Deterministic replay
Preserve:
```
pipeline_policy_version
schema_version
experiment_id
attempt_id
git_revision
configuration_digest
source_query_digest
source_revision_set
curve_snapshot_digest
estimator_digest
split_definition
cost_model_digest
result_digest
```

## 34. Canonical hashing
Define field order, UTC timestamp normalization, numeric precision, missing representation,
string normalization, sorted contracts, and source ordering. Reject NaN/infinity.

## 35. Revision drift
Vendor revisions generate new lineage/digests. Old experiments remain associated with
their prior revisions; material changes trigger reevaluation rather than silent overwrite.

## 36. Source independence
Classify origins where knowable:
`ORIGINAL_EXCHANGE, PRIMARY_OFFICIAL, DIRECT_VENDOR, RETRANSMISSION,
DERIVED_VENDOR, UNKNOWN_LINEAGE`.

Provider count is not origin diversity.

## 37. Provider capability negotiation
Known unsupported/unenitled datasets fail explicitly. Do not repeatedly retry known
entitlement failures.

## 38. Offline fixture plane
Deterministic unit/regression tests use frozen sanitized fixtures, not live internet state.

## 39. Error taxonomy
Machine-readable errors include:
`TemporalViolation, SourceUnavailable, EntitlementFailure, SemanticMismatch,
ContractLifecycleViolation, InsufficientMaturities, StaleObservation,
SourceDisagreement, UnsupportedInstrument, InvalidCurveTopology,
RevisionConflict, SynchronizationFailure`.

## 40. Observability
Emit structured counts for attempted/valid/rejected snapshots, rejection reasons,
provider failures, disagreement rate, stale-record rate, future-leak rejections,
semantic mismatches, maturity counts, and liquidity-filter rate.

## 41. Data-quality drift
Track loss of maturities, contract-code changes, semantic/timestamp convention changes,
provider disagreement, settlement schedule changes, and missingness.

## 42. Security
External payloads are data, not instructions. They cannot mutate config, promotion rules,
source priority, execution state, or code.

## 43. Existing ICARUS boundary
Do not hijack `icarus_engine/contracts.py` or alter
`icarus_engine/strategy/pulse.py` under this specification.

## 44. Proposed module boundary
```
icarus_engine/curve_research/
    __init__.py
    errors.py
    models.py
    provenance.py
    contracts.py
    synchronize.py
    quality.py
    estimators.py
    experiment.py
```

Tests live under `tests_engine/test_curve_*.py` plus deterministic fixtures/support.

## 45. Minimum behavior-neutral seam
The smallest useful implementation:
1. frozen explicit contract records;
2. lifecycle validation;
3. frozen point-in-time price observations;
4. `available_at <= asof`;
5. continuous alias rejection;
6. deterministic CurveSnapshot;
7. research-only estimator(s);
8. provenance;
9. serialization/replay;
10. zero strategy/execution influence.

## 46. Critical regression tests
Future availability, future listing, continuous aliases, duplicate maturity,
mixed semantics, source disagreement, deterministic replay, mutation isolation,
rate-unit normalization, and contract-definition availability.

## 47. Adversarial tests
Out-of-order/duplicate records, timezone ambiguity, DST, malformed tickers,
negative/nonfinite values, stale spot/rates, maturity gaps, one-contract curves,
illiquid far maturities, exchange holidays, roll/expiry, provider outage/rate limit/
entitlement failure.

## 48. Performance
Correctness dominates speed. Later support caching, vectorized reconstruction,
query batching, incremental updates, and deterministic read-only parallelism.

## 49. Scalability
Architecture may later support SI/PL/PA/energy/agriculture/financial futures without
changing the core point-in-time contract. Market-specific rules live in product policies.

## 50. S3 promotion gate
Promotion requires material gates including:
`DATA_SUFFICIENCY_STATUS=SUFFICIENT`,
`ESTIMATOR_VALIDITY_STATUS=VALIDATED`,
ablation readiness, acceptable redundancy/multiple testing, temporal integrity,
provenance, OOS incremental value, cost stress, and closed conflicts.

## 51. Runtime integration gate
Even `EMPIRICALLY_SUPPORTED` is not production qualification. Later stages must
establish `IMPLEMENTATION_READY` and `VERIFIED_FOR_INTEGRATION`.

## 52. Kill switch
Any eventual runtime feature must be immediately disableable; disabled behavior must
reproduce baseline behavior exactly.

## 53. Shadow mode
First eventual integration, if separately approved:
```
compute=true
log=true
influence_strategy=false
```

## 54. False-discovery defense
Rejecting complexity, detecting leakage/redundancy/source instability/cost destruction,
or proving a simpler baseline equal/better are successful research outcomes.

## 55. Complexity budget
Every component must identify unique information, prevented failure mode, measurable
OOS value, and simpler alternative. Otherwise remove it.

## 56. Initial implementation acceptance
Acceptance requires deterministic explicit GC contract representation, maturity ordering,
point-in-time rejection, continuous-symbol rejection, immutable snapshots, source lineage,
canonical digest, at least one research-only estimator, explicit source failures,
zero runtime mutation, and passing tests for those properties.

No backtest-profit requirement belongs in implementation acceptance.

## 57. Architectural invariant
```
Uncertainty can reduce authority, but can never increase it.
```

## Final disposition
```
PIPELINE_DISPOSITION=ADVANCE
STAGE=ARCHITECTURE_EXTRACTION_FORGE
DESIGN_STATUS=REVIEW_CANDIDATE
PRODUCTION_MUTATION=NONE
TRADING_BEHAVIOR_CHANGED=false
EXECUTION_AUTHORIZED=false
NEXT_ACTION=IMPLEMENTATION_PLAN / CROSS-LOOP RECONCILIATION
```


---

# FILE: research/ATTEMPT_LEDGER.md

# S3 Attempt Ledger

Recorded attempt IDs include:

S3-TSMOM-001
S3-OFI-001
S3-OFI-COST-001
S3-CARRY-001
S3-HEDGE-001
S3-VRP-001
S3-VRP-PROXY-001
S3-VRP-COMDIR-001
S3-TOD-001
S3-FOMC-DRIFT-001
S3-XLAG-001
S3-FIXEDLEADER-001
S3-CORRVOTE-001
S3-REV-001
S3-REV-GENERIC-001
S3-BASISREV-001
S3-LP-001
S3-SPREADCAPTURE-001
S3-LP-QUEUE-001
S3-REGIME-001
S3-REGIME-LABEL-001
S3-REGIME-SMOOTH-001
S3-CORR-ALPHA-001
S3-CORR-INDEP-001
S3-DISP-001
S3-XGB5-LINEAGE-001
S3-MACRO-SCHEDULE-DIR-001
S3-MACRO-SURPRISE-001
S3-MACRO-REDUNDANCY-001
S3-CARRY-DATA-002
S3-CARRY-CONTINUOUS-001

A failure, source change, market change, parameter-family change, or new loop does not reset effective trial count.


---

# FILE: research/S3_EMPIRICAL_EDGE_REGISTRY.md

# S3 Empirical Edge Registry

| Claim / attempt | Family | State | Key result |
|---|---|---|---|
| EDGE-TSMOM-001 / S3-TSMOM-001 | trend/momentum | HYPOTHESIS | Medium-horizon TSMOM literature does not validate ICARUS short-horizon transforms. |
| EDGE-OFI-001 / S3-OFI-001 | order flow / queue | HYPOTHESIS; DATA_BLOCKED | True OFI/queue claims require quote/order-event data. |
| EDGE-CARRY-001 / S3-CARRY-001 | carry / term structure | HYPOTHESIS; GC PARTIAL | Explicit maturity reconstruction is feasible for GC; continuous/front series are insufficient. |
| S3-HEDGE-001 | hedging pressure | REJECTED simplification | Commercial hedging pressure alone cannot authorize direction. |
| EDGE-VRP-001 / S3-VRP-001 | variance risk premium | HYPOTHESIS; DATA_BLOCKED | ATR/realized vol alone is not VRP. |
| S3-VRP-PROXY-001 | VRP proxy | REJECTED | ATR/realized volatility cannot be relabeled as VRP. |
| EDGE-TOD-001 / S3-TOD-001 | session/intraday | HYPOTHESIS | Effects can exist but are horizon/market/regime dependent. |
| S3-FOMC-DRIFT-001 | macro drift | CONFLICTED / DECAYED | Historical drift evidence does not justify persistence assumptions. |
| EDGE-XLAG-001 / S3-XLAG-001 | cross-market lead/lag | HYPOTHESIS; DATA_BLOCKED | Requires synchronized point-in-time multi-market data. |
| S3-FIXEDLEADER-001 | lead/lag | REJECTED | Permanent fixed leaders are not established. |
| S3-CORRVOTE-001 | correlation | REJECTED | Contemporaneous correlation is not independent predictive evidence. |
| EDGE-REV-001 / S3-REV-001 | reversal | HYPOTHESIS | Generic mean-reversion fading is not an adequate mechanism. |
| S3-REV-GENERIC-001 | generic reversal | REJECTED | “Prices mean revert” is not enough. |
| EDGE-BASISREV-001 / S3-BASISREV-001 | basis reversal | OBSERVED / HYPOTHESIS | Interesting but still needs synchronized explicit maturities and independent replication. |
| EDGE-LP-001 / S3-LP-001 | liquidity provision | HYPOTHESIS; DATA_BLOCKED | Queue/adverse-selection/inventory state required. |
| S3-SPREADCAPTURE-001 | market making | REJECTED | Resting at bid/ask does not imply earned spread. |
| EDGE-REGIME-001 / S3-REGIME-001 | regime conditioning | HYPOTHESIS | Regime state may help risk/volatility without directional alpha. |
| EDGE-REGIME-RISK-001 | regime risk | HYPOTHESIS | Risk value is separate from directional value. |
| S3-REGIME-LABEL-001 | regime confluence | REJECTED | Related regime indicators do not become independent confirmation. |
| S3-REGIME-SMOOTH-001 | temporal integrity | REJECTED | Full-sample/smoothed contemporaneous regimes are invalid. |
| EDGE-CORR-001 | dependence | HYPOTHESIS | Descriptive association can be valid; predictive lead remains unproven. |
| S3-CORR-ALPHA-001 | correlation alpha | REJECTED | Correlation sign cannot directly authorize BUY/SELL. |
| S3-CORR-INDEP-001 | confluence independence | REJECTED absent OOS proof | Correlated confirmations cannot each receive full independent weight. |
| S3-DISP-001 | dispersion | NO_CHANGE_JUSTIFIED | Bounded pass did not justify standalone directional alpha. |
| S3-XGB5-LINEAGE-001 | composite lineage | VERIFIED_DERIVED_COMPOSITE | Pulse XGBoost5 is hand-built, not trained XGBoost. |
| EDGE-MACRO-001 | event/macro | HYPOTHESIS | Event-conditioned behavior plausible; current semantics require hardening. |
| S3-MACRO-SCHEDULE-DIR-001 | event direction | REJECTED | Scheduled event presence does not imply trade direction. |
| S3-MACRO-SURPRISE-001 | macro surprise | HYPOTHESIS | Requires point-in-time consensus, actual, and release availability. |
| S3-MACRO-REDUNDANCY-001 | feature lineage | VERIFIED | Current trainer path makes `any_macro` redundant with `fomc`. |
| S3-CARRY-DATA-002 | carry data | OBSERVED | Explicit GC maturity reconstruction is possible through connected sources. |
| S3-CARRY-CONTINUOUS-001 | carry identification | REJECTED | A continuous/front contract alone cannot identify term structure. |
| EDGE-BTC-FUNDING-001 | crypto funding | HYPOTHESIS | Current funding observable; adequate historical point-in-time series not established. |

## Global state

`MULTIPLE_TESTING_STATUS=UNCONTROLLED`

No edge in this registry is granted production execution authority.


---

# FILE: s4/IMPLEMENTATION_PLAN.md

# S4 Implementation Plan — Test First

## Task 1 — immutable domain models and typed failures

Create:
- errors.py
- models.py
- __init__.py
- test_curve_models.py

Test first:
- frozen dataclasses
- nonfinite rejection
- temporal ordering
- positive price semantics
- negative/zero reference-rate allowance
- financing-unit normalization

## Task 2 — canonical provenance

Create:
- provenance.py
- test_curve_provenance.py

Test:
- stable mapping ordering
- date/tuple normalization
- reject NaN/infinity
- one semantic mutation changes digest

## Task 3 — explicit contract validation

Create:
- contracts.py
- test_curve_contracts.py

Reject:
- continuous aliases
- wrong root
- non-single combo contracts
- inactive lifecycle
- future definition_asof
- future definition availability
- duplicate maturity

## Task 4 — point-in-time snapshot construction

Create:
- synchronize.py
- test_curve_synchronization.py

Critical test:
a record observed before asof but available after asof must fail.

Also:
- stale records
- duplicate price observations
- semantic-specific synchronization
- minimum maturity
- normalized financing

## Task 5 — source disagreement / quality

Create:
- quality.py
- test_curve_quality.py

No automatic blended consensus value.

## Task 6 — estimators

Create:
- estimators.py
- test_curve_estimators.py

Functions:
- raw_slope
- annualized_log_slope
- spot_basis
- annualized_log_basis
- financing_adjusted_log_basis

No BUY/SELL semantics.

## Task 7 — deterministic fixture and test support

Create:
- tests_engine/curve_test_support.py
- tests_engine/fixtures/curve_gc_2026_09_24.json

Test deterministic replay and revision sensitivity.

## Task 8 — research receipt

Create:
- experiment.py
- test_curve_experiment.py

Receipt always:
`execution_authorized=false`.

No builder override.

## Task 9 — isolation gate

Create:
- test_curve_isolation.py

Ensure runtime.py, emulator.py, and strategy/pulse.py do not import curve_research.

## Task 10 — full verification

Planned commands:

`pytest tests_engine/test_curve_models.py -v`
`pytest tests_engine/test_curve_provenance.py -v`
`pytest tests_engine/test_curve_contracts.py -v`
`pytest tests_engine/test_curve_synchronization.py -v`
`pytest tests_engine/test_curve_quality.py -v`
`pytest tests_engine/test_curve_estimators.py -v`
`pytest tests_engine/test_curve_experiment.py -v`
`pytest tests_engine/test_curve_isolation.py -v`
`pytest tests_engine/test_futures.py -v`
`pytest tests_engine/test_research.py -v`
`pytest tests_engine -q`
`python -m compileall -q icarus_engine`
`git diff --check`

These commands have NOT yet been run for an implemented curve subsystem because that subsystem has not been implemented.


---

# FILE: s4/PROPOSED_CODE_AND_TEST_INTERFACES.md

# Proposed Code and Test Interfaces

These are design interfaces, not committed production code.

```python
@dataclass(frozen=True)
class Observation:
    source_id: str
    source_record_id: str
    source_revision: str
    instrument_id: str
    observation_type: str
    price_semantic: PriceSemantic
    observed_at: int
    available_at: int
    value: float
    units: str
    currency: str
    contract_ticker: str | None = None
    quality_flags: tuple[str, ...] = ()
```

```python
@dataclass(frozen=True)
class ContractDefinition:
    root: str
    ticker: str
    first_trade_date: date
    last_trade_date: date
    settlement_date: date
    contract_type: str
    definition_asof: date
    available_at: int
    source_id: str
    source_revision: str
    tick_size: float | None = None
    multiplier: float | None = None
```

```python
@dataclass(frozen=True)
class FinancingPoint:
    tenor_days: int
    observation: Observation

    @property
    def annual_rate(self) -> float:
        if self.observation.units != "DECIMAL_PER_YEAR":
            raise ValueError("financing rate must be normalized")
        return self.observation.value
```

```python
def validate_contract(contract, *, root: str, asof: int):
    asof_date = datetime.fromtimestamp(asof, timezone.utc).date()

    reject_continuous_alias(contract.ticker)

    if contract.root != root:
        raise ContractLifecycleViolation(...)

    if contract.contract_type != "single":
        raise UnsupportedContractType(...)

    if contract.definition_asof > asof_date:
        raise TemporalViolation("contract definition is from the future")

    if contract.available_at > asof:
        raise TemporalViolation("contract definition was unavailable at asof")

    if not contract.first_trade_date <= asof_date <= contract.last_trade_date:
        raise ContractLifecycleViolation(...)

    return contract
```

Key regression case:

```python
def test_future_availability_is_rejected_even_when_observed_before_asof():
    # observed_at < asof, but available_at > asof
    # snapshot construction must raise TemporalViolation
    ...
```

Isolation expectation:

```python
assert "curve_research" not in runtime_py
assert "curve_research" not in emulator_py
assert "curve_research" not in pulse_py
```


---

# FILE: s4/S4_CURVE_RESEARCH_DESIGN.md

# S4 Point-in-Time Curve Research Plane — Condensed Complete Design

## Purpose

Build a research-only point-in-time futures-curve subsystem answering:

“What explicit contracts, prices, spot observations, financing observations, metadata, and source revisions were genuinely knowable at historical time t?”

## Architecture

Provider adapters
-> canonical observations
-> point-in-time contract metadata
-> semantic synchronizer
-> immutable CurveSnapshot
-> independent estimators
-> falsification / ablation
-> research evidence registry

No direct path to Pulse.

## Canonical observation fields

- source_id
- source_record_id
- source_revision
- instrument_id
- root
- contract_ticker
- observation_type
- price_semantic
- observed_at
- published_at when available
- available_at
- received_at when available
- value
- units
- currency
- exchange/session where available
- quality flags

Core constraint:
`available_at <= decision_asof`.

## Contract definition

Must preserve:
- root/ticker
- first trade date
- last trade date
- settlement date
- contract type
- definition_asof
- definition_available_at
- source/revision
- tick/multiplier where available

Only explicit outright single contracts in Phase A.

## Continuous-symbol quarantine

Reject as curve legs:
- GC=F
- GC1!
- generic front aliases
- stitched/back-adjusted/ratio-adjusted series

## Price semantics

Typed:
TRADE, BID, ASK, MID, SETTLEMENT, OFFICIAL_CLOSE, SESSION_CLOSE, VWAP, SPOT, REFERENCE_RATE.

Estimator declares accepted semantics.

## Synchronization

“Same calendar day” is insufficient.

Semantic-specific policies control:
- settlement-to-settlement
- quote-to-quote
- futures-to-spot
- rates-to-maturity mapping

## CurveSnapshot

Immutable research object carrying:
- root/asof/schema
- explicit maturity legs
- source lineage
- spot
- financing curve
- synchronization policy
- quality flags/report
- canonical digest

No direction field.

## Quality and provider disagreement

Classify consistency/dislocation/staleness/incomparability.

Do not automatically average providers.

## Financing

Normalize to decimal-per-year.

Treasury yields are a candidate proxy, not automatically:
- dealer financing
- lease rate
- storage cost
- convenience yield

## Initial estimators

- raw maturity slope
- annualized log slope
- spot basis
- annualized log basis
- financing-adjusted basis residual
- later level/slope/curvature/inversion families

No universal carry score.

## Research experiment hierarchy

M0 null
M1 simple own-price baseline
M2 M1 + single curve estimator
M3 M1 + alternative estimator
M4 M1 + redundancy-controlled curve family
M5 current ICARUS
M6 M5 + qualified curve family

Primary decision quantity:
`Delta_OOS = M6 - M5`.

## Chronological evaluation only

Allowed:
- expanding-window OOS
- rolling-window OOS
- walk-forward
- untouched final holdout

Forbidden:
- random temporal split
- final-holdout tuning
- estimator/maturity selection after viewing holdout performance

## Falsification

Use temporal perturbation, maturity perturbation, estimator perturbation, source removal, regime slices, roll/expiry windows, cross-market transfer after qualification, null controls, and simple baselines.

## Redundancy

Every candidate feature keeps:
- raw observable lineage
- transform lineage
- family ID
- channel class

Multiple transforms of one curve are one evidence family unless OOS independence is established.

## Multiple testing

Every variant/parameter/failure stays in the attempt ledger.

## Execution realism

Predictive information does not establish tradeability.

Later evaluation must include:
spread, commissions, slippage, impact, delay, liquidity by maturity, roll, expiry, delivery risk, order type, partial fills, and capacity.

## Deterministic replay

Preserve:
pipeline policy, schema, attempt, git revision, source query/revision set, curve digest, estimator digest, split definition, cost model, result digest.

## Initial module boundary

`icarus_engine/curve_research/`
with:
- errors.py
- models.py
- provenance.py
- contracts.py
- synchronize.py
- quality.py
- estimators.py
- experiment.py

## Initial acceptance

The infrastructure is acceptable only after tests prove:
- explicit maturity enforcement
- lifecycle and metadata availability
- post-asof rejection
- semantic synchronization
- deterministic hashing/replay
- no silent provider averaging
- research-only estimators
- fail-closed receipts
- runtime/Pulse isolation

This is infrastructure acceptance, not profitability validation.
