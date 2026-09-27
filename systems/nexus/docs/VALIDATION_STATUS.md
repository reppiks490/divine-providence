# NEXUS v0.3 Validation Status

Checkpoint date: 2026-09-23
Build owner/signature: **SOL**
Receiving model: **Sol Extra High**

## Test status

- NEXUS: **117/117 passed**
- AION: **11/11 passed**
- ARGUS: **4/4 passed**
- ATHENA: **3/3 passed**
- DAEDALUS: **45/45 collected tests passed file-by-file** (the monolithic command exceeds this environment's 120-second window) on a fresh full rerun
- `python -m compileall -q src tests`: **passed**
- exact same-instant sibling contract validation: **passed** for all four siblings
- sibling contract drift sentinel: **passed**; final snapshot matches the sealed AST/raw baseline with zero semantic drift
- AION durable integration: bar + derivation + source-health context validates and preserves hash-chain/as-of semantics
- real NQ/ES/VIX/DXY/VXN engineering smoke: **passed**
- prior five-market factor prefix audit: **9,460 comparisons / 0 violations**

## v0.3 additions validated

- canonical `ReplayInstant` binds a same-time batch to its exact post-batch state/frame hash;
- atomic sibling routing can bind source-health and derivation genealogy to that same decision instant;
- source health/SLO telemetry covers observable receive lag, gaps, reconnects, revisions, nonmonotone sequence/receipt, clock uncertainty and impossible timing evidence;
- fleet source-health planes are deterministically hashed and leave unconfigured SLOs explicitly unknown;
- reviewed representation registry is immutable/versioned and refuses fictional fixed cadence for event-driven representations;
- causal-transform registry requires prefix-invariance certification before engineering promotion;
- single-sensor and arbitrary group/sector/representation-family ablation pass;
- factor genealogy nodes are deeply immutable and run manifests are tamper-evident;
- appendable SQLite event store/source round-trips deterministically;
- streaming partitioned Parquet implementation compiles and is isolated behind optional Arrow dependency.

## Real accessible corpus checkpoint

The currently materialized archive is **not** the full expected corpus.

- physical `.csv` members: **476**
- AppleDouble/resource-fork sidecars: **238**
- usable market CSV members: **238**
- usable rows: **1,970,753**
- distinct byte/logical market contents: **231**
- exact duplicate usable entries: **7**
- fractional-time streams: **12**
- cadence-ambiguous streams: **64**
- filename/observed-cadence mismatches: **47**
- default integrity gate admitted: **174 / 238**
- default integrity gate withheld: **64 / 238**
- one-stream-per-symbol anti-duplication universe: **19 symbols selected**

AION's prior audit records **626 usable entries / ~12,588,290 rows** across nine ZIPs. Current materialization remains short by **388 usable entries / 10,617,537 rows** relative to that checkpoint. Full-corpus coverage MUST NOT be claimed until reconciled.

## Important runtime boundary

`pyarrow` is not installed in this environment. The streaming Parquet implementation compiles but is **not runtime-validated here**. NPY and SQLite paths are test-validated. Sol Extra High should validate Parquet replay parity, deterministic manifests and bounded-memory behavior in an Arrow-capable environment before calling that backend production-ready.

These checks prove engineering properties, not predictive edge, profitability, execution quality or live calibration.
