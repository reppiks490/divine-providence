# NEXUS ADAPTIVE MARKET FABRIC — BLUEPRINT v0.3

> Canonical status: `VALIDATION_STATUS.md`. Canonical takeover instructions: `SOL_EXTRA_HIGH_HANDOFF_V3.md`.

## 1. Mission

NEXUS is the market-data substrate beneath the Icarus intelligence stack. It turns imperfect, overlapping, transformed and differently timed historical/live market sources into a **causal, deterministic, provenance-preserving market fabric** and exposes derived state without taking over sibling authority.

Design principle: **preserve first, review semantics second, align causally third, adapt fourth, predict nowhere by default**.

CSV is the primary historical corpus, not the architectural limit. The same contracts now support CSV, iterable sources, deterministic NPY partitions, appendable SQLite storage and optional streaming Parquet; authenticated live transports are the next frontier.

## 2. Non-negotiable invariants

1. Never infer authoritative identity/clock semantics solely from a filename.
2. Never silently sort away, deduplicate, aggregate or forward-fill raw truth for modeling convenience.
3. Preserve repeated timestamps, revisions and source-local sequence.
4. Event time, availability time, receipt/ingestion time and decision time are distinct.
5. A derived value at decision `t` may use only information available by `t`.
6. Event-driven representations never receive fictional fixed-time boundaries.
7. Candle-derived products never become true trade/depth evidence.
8. Duplicate inputs may share compute but never lose lineage.
9. Multiple representations of one symbol never gain extra cross-asset voting weight by file count alone.
10. Quality/OOD/confidence are telemetry, not predictive probabilities.
11. DAEDALUS owns statistical validation/promotion; ATHENA owns supervision; AION owns memory; ARGUS owns microstructure truth; Icarus owns execution.
12. NEXUS never places an order and never emits `production_authorized=true`.

## 3. Layered architecture

### A — Forensic corpus and archive catalog
- recursive and ZIP-native profiling;
- raw SHA-256 and logical identity;
- original archive/member path;
- schema/header position fingerprinting;
- AppleDouble/resource-fork quarantine;
- timestamp/cadence/quality diagnostics;
- exact and near-duplicate evidence without deleting lineage.

### B — Raw identity + reviewed representation registry
Raw identity remains immutable. A separate reviewed, versioned registry binds evidence-backed canonical instrument, venue, representation class, timestamp semantics, interval (only where legitimate), availability delay, timezone, roll policy and execution suitability. Activation is explicit; old review versions remain replayable.

### C — Causal time kernel / clock lattice
- nanosecond/fractional timestamp preservation;
- reviewed open-stamped, close-stamped and event-completion policies;
- event / availability / ingestion separation;
- native multi-resolution visibility lattice;
- strict refusal to invent unavailable timestamps.

### D — Atomic replay fabric
`ReplayBus` merges streams deterministically. `ReplayInstant` binds every same-visibility batch to exactly one post-batch `StatePacket` and frame hash. This is the canonical boundary for sibling routing.

### E — Integrity, quality and operational health
Two separate planes are preserved:
- **data quality/integrity:** schema, OHLC geometry, cadence confidence, missing/stale state, clock uncertainty, admission policy;
- **operational source health:** receive-lag evidence, sequence gaps, reconnect epochs, revisions, nonmonotone receipts/sequences, impossible timing evidence and explicit per-source SLOs.

Neither plane imputes market truth. ATHENA may consume these ingredients but owns supervisory interpretation.

### F — Representation -> symbol -> cross-asset fusion
Equivalent/redundant source views are first reconciled within representation/symbol boundaries. Hierarchical fusion prevents duplicate downloads or many representations from giving one underlying symbol multiple cross-asset votes.

### G — Adaptive synthetic ticker factory
Implemented builders include equal weight, inverse volatility, adaptive PCA, shrinkage PCA, robust PCA and cluster-balanced factors with concentration caps. An ensemble exposes method disagreement, turnover/loading stability and coverage rather than pretending one factor method is universally correct.

### H — Dynamic topology / drift / OOD
- rolling correlation and ridge partial correlation;
- communities, centrality, network entropy, edge survival;
- descriptive lead/lag candidate persistence;
- EWMA/CUSUM change telemetry;
- trailing Mahalanobis OOD and kernel-window shift.

More complex nonlinear/causal-network methods remain DAEDALUS research candidates until validated.

### I — Ablation / fragility
Synthetic products support single-sensor and arbitrary grouped ablation (sector, cluster, asset class, representation family) to expose dependence and hidden concentration.

### J — Persistence and restartability
- hash-chained SQLite Market Fabric Ledger;
- deterministic mmap-friendly NPY columnar partitions;
- appendable SQLite BarEvent store;
- optional streaming per-stream Parquet partitions with content-addressed manifest;
- replay checkpoints and full fabric checkpoint manifests.

### K — Reproducibility / promotion engineering
- immutable factor specifications + dependency DAG;
- tamper-evident derivation records;
- deeply immutable factor genealogy snapshots;
- immutable `ResearchRunManifest` binding corpus hash, reviewed registry hash, code, params, inputs, outputs and derivations;
- causal-transform registry requiring a passing prefix-invariance certificate before the exact transform version is marked engineering-promotable.

Engineering promotability is not DAEDALUS statistical promotion and never grants production authority.

### L — Sibling-safe atomic routing
For one `ReplayInstant`, NEXUS can package:
- **AION:** bar/context observations, derivation genealogy and source-health context;
- **ARGUS:** `CANDLE_PROXY` context only, with `microstructure_truth=false`;
- **ATHENA:** provenance + factor/topology/quality/OOD/source-health ingredients; no WorldState ownership;
- **DAEDALUS:** `RESEARCH_CANDIDATE_ONLY` payloads; no protected-evidence bypass;
- **Icarus:** no direct order path.

## 4. Accuracy doctrine

“Accuracy” is not one thing:
- **data accuracy:** correct identity, values, timestamp semantics, schema and lineage;
- **causal accuracy:** no future information in historical state;
- **operational accuracy:** measured source timing/health rather than guessed timing;
- **statistical accuracy:** out-of-sample/calibrated evidence, owned by DAEDALUS/ATHENA protocols;
- **execution accuracy:** fills/queue/slippage using real microstructure, owned by ARGUS/Icarus.

NEXUS primarily guarantees the first three and provides reproducible inputs for the latter two.

## 5. Current scaling frontier

Current runtime validates CSV/ZIP, NPY and SQLite paths. A streaming partitioned Parquet implementation exists, but `pyarrow` is not installed here, so Arrow runtime parity remains a P0 validation item. The authoritative historical corpus is also incomplete in this environment: 238 usable streams / 1,970,753 rows are materialized versus AION's prior 626-stream / ~12.59M-row checkpoint.

## 6. Target end-state

`raw/live source -> forensic identity -> reviewed representation/clock -> causal native event fabric -> source health + integrity gate -> representation/symbol fusion -> adaptive factors/topology/OOD -> derivation/genealogy/run hashes -> atomic sibling-safe packets`

The target is a market-data operating system that is deterministic, causally auditable, adaptable across source types, and explicit about uncertainty—without fabricating evidence or stealing downstream authority.
