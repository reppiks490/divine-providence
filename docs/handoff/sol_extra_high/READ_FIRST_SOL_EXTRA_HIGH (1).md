# SOL EXTRA HIGH — NEXUS TAKEOVER HANDOFF

Prepared and signed by: **SOL**
Date: 2026-09-23

## Primary goal

Take NEXUS v0.2 from a tested advanced CSV-first market fabric into the **authoritative market-data substrate for the complete Icarus intelligence stack**. Preserve the existing architecture and invariants. Do not restart the project and do not collapse NEXUS into ARGUS, ATHENA, AION, or DAEDALUS.

## Start here

1. Run `git status`, inspect the final tagged checkpoint, and read:
   - `docs/BLUEPRINT.md`
   - `docs/CAPABILITY_CROSS_REFERENCE_V2.md`
   - `docs/VALIDATION_STATUS.md`
   - this file
2. Run `PYTHONPATH=src pytest -q -o addopts=''` and confirm **80 passed** or better.
3. Re-run `scripts/validate_sibling_contracts.py` against the available sibling roots.
4. Do not make predictive/trading claims from the engineering smoke artifacts.

## What SOL completed in v0.2

### Corpus and identity
- ZIP-native and extracted corpus profiling.
- SHA-256 raw identity + logical digest identity.
- AppleDouble quarantine.
- filename claim parsing separated from download copy ordinal.
- observed cadence inference without trusting filename claims.
- duplicate header position detection.
- numeric/OHLC geometry integrity telemetry.
- exact/logical duplicate controls.
- reviewed identity registry and corpus reconciliation.

### Time and causality
- nanosecond/fractional timestamp preservation.
- event time / availability time / ingestion time separation.
- strict unknown-availability refusal paths.
- reviewed clock policies for open-stamped, close-stamped, and event-completion representations.
- multi-resolution clock lattice that emits native visibility boundaries and never manufactures a common regular clock.
- deterministic same-time replay and vector replay.
- backward-as-of causal alignment.
- generic prefix-invariance audit for future leakage.

### Persistence and reproducibility
- hash-chained SQLite Market Fabric Ledger.
- deterministic NPY columnar partition store with mmap reads and content verification.
- optional Parquet frontier when `pyarrow` is available.
- replay checkpoints and full fabric checkpoint manifests.
- factor specification registry + DAG validation.
- tamper-evident derivation records covering input hashes, spec, params, code version, and decision time.

### Modeling substrate
- causal completed-bar/context features.
- equal / inverse-vol / adaptive PCA / shrinkage PCA / robust PCA / cluster-balanced factors.
- component concentration caps.
- ensemble disagreement, turnover, and loading-direction stability.
- hierarchical representation -> symbol -> cross-asset fusion to eliminate representation-count voting bias.
- robust per-symbol representation consensus, disagreement, directional agreement, quality weighting and coverage.
- hard integrity-gated factor universe with duplicate and per-symbol representation controls.
- rolling correlation and ridge partial-correlation topology.
- topology communities, entropy, centrality, edge survival.
- descriptive lead/lag candidate scan + persistence diagnostics.
- EWMA/CUSUM change detection.
- trailing Mahalanobis novelty/OOD + kernel-window shift sensor.
- sensor ablation/fragility diagnostics.

### Sibling contracts
- AION SourceSpec/Observation validation passes.
- ARGUS CSV export remains `CANDLE_PROXY` only.
- ATHENA provenance construction passes without NEXUS constructing WorldState.
- DAEDALUS candidate bridge stays `RESEARCH_CANDIDATE_ONLY`, `production_authorized=false`.

## P0 unfinished — do these first

### P0.1 Recover and reconcile the authoritative corpus
**Goal:** replace the current incomplete 238-usable materialization with one versioned manifest covering every accessible real CSV member expected from the multi-level-csv/GitHub corpus.

Known anchors:
- current materialization: 238 usable / 1,970,753 rows.
- AION prior checkpoint: 626 usable / ~12,588,290 rows across nine ZIPs.
- owner expectation: roughly 800+ files; do not claim that count until verified.

Acceptance criteria:
- every archive/member has archive hash, member raw hash, logical hash, original path, schema fingerprint, header positions, symbol/venue claims, observed cadence, representation hypothesis and quality assessment;
- exact byte/logical duplicate sets are explicit;
- a reconciliation report shows no unexplained loss relative to every recovered prior checkpoint;
- current `coverage_claim_allowed` remains false until evidence proves otherwise.

### P0.2 Build the reviewed representation registry
**Goal:** convert non-authoritative representation hypotheses into reviewed clock/identity policies without guessing.

Create reviewed families at minimum for:
- conventional fixed time bars;
- second/minute/hour/day/week exports;
- Renko/range/price-event transforms where proven;
- tick/volume-like/event-completion streams where proven;
- derived candles such as Heikin-Ashi where proven;
- macro scheduled/revised observations;
- authenticated real-time feeds.

Acceptance criteria:
- no stream receives a fixed cadence merely because of filename syntax;
- event-driven representations never get fictional minute boundaries;
- unknown semantics stay blocked from strict availability-aware modeling;
- registry changes are versioned/immutable.

### P0.3 Promote persistence to production-scale Arrow/Parquet
**Goal:** retain NEXUS deterministic hashes while scaling beyond 10M rows.

Acceptance criteria:
- partition by stable stream identity and sensible time buckets;
- streaming writes, no whole-corpus materialization;
- content-addressed partition manifest;
- deterministic manifest/hash across worker counts;
- replay parity test: Parquet -> events -> state hashes equal canonical source replay;
- benchmark current 12M+ checkpoint when recovered.

### P0.4 End-to-end sibling replay integration
**Goal:** replay the same NEXUS market instant into all sibling contracts without violating ownership.

Acceptance criteria:
- AION persists NEXUS frame/derivation hashes;
- ARGUS receives only proxy context for CSV-derived information;
- ATHENA receives quality/topology/OOD/factor ingredients but owns interpretation and abstention;
- DAEDALUS receives candidates and runs validation without bypassing protected evidence/promotion;
- no code path sets `production_authorized=true` inside NEXUS.

## P1 high-value build work

1. Add cluster/sector/representation-family ablation, not just single-sensor ablation.
2. Add topology shrinkage selection and community persistence; nonlinear/Granger/transfer-entropy work stays a DAEDALUS research candidate.
3. Add live source health: receive lag, gap runs, reconnect epochs, revision counts, clock uncertainty and source SLOs.
4. Add source adapters for SQLite/Parquet/Kafka or Redpanda/WebSocket; hand authenticated depth/trades to ARGUS evidence contracts.
5. Add automatic prefix-invariance/leakage audits to CI for every registered factor/transform.
6. Add factor genealogy export to AION and immutable run manifests for every research run.
7. Add representation-family consensus before symbol fusion when the full corpus contains several equivalent copies/transforms.
8. Add deterministic distributed catalog/replay benchmark with worker-count parity.

## Do not do

- Do not sort away repeated timestamps to make a model convenient.
- Do not delete duplicate files from lineage simply because compute can be shared.
- Do not treat filename timeframe as authoritative.
- Do not call candle proxies L2/order flow.
- Do not infer historical availability timestamps that the source cannot prove.
- Do not forward-fill missing state into market truth without an explicit derived/imputation contract.
- Do not let multiple representations of the same symbol silently overweight that symbol.
- Do not run full-data normalization or centered rolling transforms before historical evaluation.
- Do not merge ATHENA supervisory authority, AION memory authority, ARGUS microstructure authority, or DAEDALUS validation authority into NEXUS.
- Do not authorize orders from NEXUS.

## Verification baseline handed to Sol Extra High

- NEXUS: **80/80 passed**
- AION: **11/11 passed**
- ARGUS: **4/4 passed**
- ATHENA: **3/3 passed**
- DAEDALUS: **45/45 passed**
- compileall: passed
- sibling schema validation: passed all four
- real 5-market factor prefix audit: **9,460 comparisons / 0 violations**

## Definition of success for the next takeover

NEXUS should be able to point at the authoritative corpus or live adapter set and produce, reproducibly:

`raw sources -> forensic manifest -> reviewed clock/identity -> causal native event fabric -> quality/integrity gate -> representation consensus -> symbol state -> adaptive factors/topology/OOD -> derivation hashes -> sibling-safe packets`

with no hidden future data, no silent source collapse, no representation-count bias, no fabricated microstructure, and no production order authority.

— **SOL**
