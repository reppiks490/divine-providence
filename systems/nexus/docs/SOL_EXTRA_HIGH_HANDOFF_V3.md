# SOL -> SOL EXTRA HIGH — NEXUS v0.3 TAKEOVER

Prepared and signed by: **SOL**
Receiving model: **Sol Extra High**
Date: 2026-09-23

## Clear takeover goal

Turn NEXUS from a tested CSV-first adaptive market fabric into the **authoritative, source-agnostic market-data substrate for the Icarus intelligence stack**, without absorbing the authority of ARGUS, ATHENA, AION, DAEDALUS, or Icarus execution.

The target pipeline is:

`raw sources -> forensic manifest -> reviewed identity/clock policy -> causal native event fabric -> integrity/source-health gate -> representation-family consensus -> symbol plane -> adaptive factors/topology/OOD -> derivation/run hashes -> same-instant sibling packets`

Every stage must remain deterministic, replayable, leakage-resistant, and explicit about uncertainty.

## Takeover procedure — do this before changing code

1. Run `git status --short` and verify the checkpoint/tag `nexus-v0.3-sol-handoff`.
2. Read, in order:
   - `docs/BLUEPRINT.md`
   - `docs/CAPABILITY_CROSS_REFERENCE_V3.md`
   - `docs/VALIDATION_STATUS.md`
   - this file
   - `docs/current-state.md`
   - `docs/next-task.md`
3. Run `PYTHONPATH=src pytest -q -o addopts=''` and require **117 passed or better** before modifying architecture.
4. Run `python -m compileall -q src tests`.
5. Re-run `scripts/validate_sibling_contracts.py` against the sibling roots available in the environment.
6. Do not make trading-edge or profitability claims from engineering smoke tests.

## What SOL completed

### Corpus forensics and identity
- ZIP-native and extracted profiling.
- raw SHA-256 and logical-content hashes.
- AppleDouble/resource-fork quarantine.
- filename claim parsing separated from duplicate-download ordinal.
- observed cadence inference independent of filename claims.
- schema/header-position and OHLC geometry integrity checks.
- exact and near-duplicate lineage preservation.
- reviewed representation/identity registries.
- deterministic representation-review queue requiring source/timestamp/timezone evidence; current catalog: **92 P0 / 146 P2** candidates.
- hash-first corpus reconciliation.

### Causality and clocks
- nanosecond/fractional timestamp preservation.
- event time / availability time / ingestion time separation.
- strict refusal path for unknown availability.
- reviewed open-stamped, close-stamped, and event-completion policies.
- native multi-resolution clock lattice; no fictional common cadence.
- deterministic same-time atomic replay and vector replay.
- backward-as-of alignment.
- prefix-invariance leakage audit.
- causal transform certification gate.

### Data quality and operational health
- static manifest quality scoring and hard factor-admission gate.
- dynamic source-health tracker: observable receive lag, sequence gaps, reconnect epochs, revisions, nonmonotone sequences, out-of-order receipts, clock uncertainty, impossible-time evidence, unknown availability.
- reviewed per-source SLO policies; unconfigured streams remain `unknown_slo` rather than inheriting guessed thresholds.
- deterministic fleet-level `SourceHealthPlane` with hash.
- source-health plane is now bound to the same decision instant as replay state and carried through the atomic sibling bundle.

### Representation/symbol/factor fabric
- representation consensus and disagreement.
- hierarchical representation -> symbol -> cross-asset fusion to stop representation-count voting bias.
- equal-weight, inverse-vol, PCA, shrinkage PCA, robust PCA, cluster-balanced factors.
- component concentration caps.
- factor ensemble disagreement/turnover/loading-stability diagnostics.
- single-sensor and group/cluster ablation.
- rolling topology, ridge partial correlation, communities, centrality, entropy, edge survival, lead/lag persistence.
- EWMA/CUSUM change detection.
- trailing Mahalanobis novelty and kernel shift telemetry.

### Reproducibility and persistence
- hash-chained Market Fabric Ledger.
- deterministic NPY partitions with verification.
- appendable SQLite event store/source path.
- optional streaming partitioned Parquet implementation when Arrow is present.
- replay/fabric checkpoints.
- immutable factor registry / DAG checks.
- tamper-evident `DerivationRecord` over inputs/spec/params/code/decision time.
- immutable research-run manifests and factor genealogy snapshots.

### Same-instant sibling routing
The canonical `SiblingInstantRouter` packages one causal replay instant for all siblings.

- **AION:** SourceSpec/Observation plus derivation genealogy; validation includes durable EventStore append, as-of recovery, and hash-chain verification.
- **ARGUS:** CSV-derived information remains `CANDLE_PROXY`; no fabricated trade/depth truth.
- **ATHENA:** receives provenance, factor/topology/OOD/quality/source-health ingredients; NEXUS does not construct supervisory WorldState or decide abstention.
- **DAEDALUS:** receives `RESEARCH_CANDIDATE_ONLY` payloads; NEXUS never authorizes production.
- **Icarus:** no broker/order authority exists in NEXUS.
- **Contract drift:** raw + AST-normalized sibling boundary fingerprints distinguish formatting churn from semantic contract drift before integration.

## Real corpus facts that must remain explicit

Current accessible archive:
- 476 physical `.csv` members.
- 238 AppleDouble/resource-fork sidecars.
- 238 usable market CSV members.
- 1,970,753 usable rows.
- 231 distinct byte/logical market contents.
- 7 exact duplicate usable entries.
- 12 fractional-time streams.
- 47 filename-vs-observed-cadence mismatches.
- 64 cadence/quality-ambiguous streams withheld by the default factor gate.
- 174 / 238 admitted by default integrity policy.

AION's prior audit records **626 usable entries / ~12,588,290 rows across nine ZIPs**. Therefore the currently materialized corpus is short by **388 usable entries / 10,617,537 rows** relative to that checkpoint. The owner also expects roughly 800+ files. Never claim full-corpus coverage until it is proved by manifests and hashes.

## P0 — unfinished work Sol Extra High should do first

### P0.1 Recover the authoritative corpus
**Goal:** produce one content-addressed manifest covering every accessible source archive/member and reconcile it against both the current 238-stream checkpoint and AION's 626-stream checkpoint.

Required output per member: archive hash, member raw hash, logical hash, original path, schema/header positions, symbol/venue claim, observed cadence, representation hypothesis/review state, integrity result, row count, timestamp range, duplicate set membership.

Acceptance: zero unexplained loss relative to every recovered checkpoint; `coverage_claim_allowed=false` until proven complete.

### P0.2 Populate the reviewed representation registry
**Goal:** convert hypotheses to evidence-backed clock/identity policies for every recovered stream.

Families to review: fixed time bars, seconds/minutes/hours/daily/weekly, Renko/range/price-event, tick/volume/event-completion, Heikin-Ashi/derived candles, scheduled/revised macro observations, authenticated live feeds.

Acceptance: unknown semantics remain blocked from strict modeling; event-driven views never receive fabricated minute boundaries; registry revisions are immutable/versioned.

### P0.3 Prove production-scale Arrow/Parquet replay parity
**Goal:** run the existing streaming partitioned Parquet path with `pyarrow` available against the recovered 12M+ corpus.

Acceptance: streaming writes; stable partition identity/time buckets; content-addressed manifests; deterministic output across worker counts; Parquet -> events -> replay state/frame hashes equal canonical replay; benchmark recorded.

### P0.4 Deploy exact same-instant sibling integration
**Goal:** move from local class-level validation to deployed/service integration while retaining the canonical atomic bundle.

Acceptance: AION durably persists frame/derivation lineage; ARGUS accepts proxy context only; ATHENA consumes health/quality/topology/OOD/factors but retains supervisory authority; DAEDALUS validates candidates; NEXUS never sets production authorization true.

## P1 — high-value next capabilities

- authenticated live source adapters (WebSocket/Kafka/Redpanda/database/Parquet) with receive-time evidence and source-health telemetry;
- futures contract/roll identity and venue/session metadata;
- distributed catalog/replay worker-count parity test;
- automatic CI prefix-invariance certification for every registered/promoted transform;
- calibrated source-class integrity/SLO policies from observed live behavior;
- durable write-through of source-health and derivation/run manifests into AION;
- representation-family consensus calibrated on the full corpus;
- topology shrinkage/community persistence research candidates handed to DAEDALUS, not silently promoted in NEXUS;
- live service backpressure, watermark, restart/recovery, and exactly-once/idempotency tests.

## Known verification caveat at freeze

Fresh freeze verification:
- NEXUS: **117/117 passed**.
- AION: **11/11 passed** after using its repo on `PYTHONPATH`.
- ARGUS: **4/4 passed**.
- ATHENA: **3/3 passed**.
- compileall: passed.
- exact sibling validation: passed all four, including AION durable EventStore genealogy and source-health same-instant binding.
- final contract-drift comparison: zero raw drift and zero semantic AST drift versus the sealed sibling boundary baseline.
- DAEDALUS: **45/45 passed** on a fresh full rerun.

## Architectural prohibitions

Do not:
- round away or sort away repeated/fractional timestamps;
- delete duplicate sources from provenance because compute can be shared;
- trust filename timeframe as truth;
- call OHLCV proxies order flow/L2;
- invent historical availability/receipt times;
- forward-fill missingness into market truth without an explicit derived-imputation contract;
- let multiple representations or duplicate downloads silently overweight a symbol;
- use full-data normalization, centered windows, or future-aware transforms in historical evaluation;
- let NEXUS take ATHENA supervisory authority, AION memory authority, ARGUS microstructure truth authority, DAEDALUS statistical promotion authority, or Icarus execution authority.

## Definition of takeover success

Sol Extra High succeeds when NEXUS can ingest the **authoritative recovered corpus and live sources**, replay them causally and deterministically at native clocks, gate them by reviewed integrity/source health, fuse representations without voting bias, emit adaptive state/factors/topology/OOD with exact genealogy, and route the identical market instant into all sibling systems—with no future leakage, fabricated microstructure, hidden source collapse, or production order authority.

— **SOL**
