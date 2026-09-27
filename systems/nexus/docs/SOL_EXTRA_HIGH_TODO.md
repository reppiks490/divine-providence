# SOL -> Sol Extra High: Explicit Continuation Queue

Prepared by **SOL** for **Sol Extra High** on 2026-09-23.

## Goal

Make NEXUS the authoritative, source-agnostic, causal market-data substrate for the Icarus stack while preserving sibling ownership boundaries. Do not restart or redesign from scratch; continue from tag `nexus-v0.3-sol-handoff`.

## P0.1 — Recover and prove the authoritative corpus

**Goal:** reconcile every accessible CSV/archive against the current 238-usable-stream checkpoint and AION's prior 626-usable-stream/~12.59M-row checkpoint.

**Do:** locate every archive/repo batch; catalog ZIP-native first; preserve archive/member paths; fingerprint raw and logical content; merge by content identity, never filename alone; run `compare_declared_checkpoint` after every recovered batch.

**Acceptance:** one content-addressed manifest; no unexplained loss relative to recovered checkpoints; `coverage_claim_allowed=false` until entry and row gaps are zero; every source remains traceable to archive/member/hash.

## P0.2 — Finish reviewed representation semantics

**Goal:** turn the generated `artifacts/representation_review_queue.v3.json` into evidence-backed immutable registry entries.

**Do:** start with 92 P0 candidates; obtain vendor/source evidence for representation type, timestamp semantics, timezone/session, and volume semantics; version every reviewed record; never infer BAR_OPEN/BAR_CLOSE from cadence alone.

**Acceptance:** strict-model streams have active reviewed policies; event-driven views have no fictional fixed interval; unknown semantics remain blocked; every activation points to evidence hash.

## P0.3 — Prove 12M+ row columnar parity

**Goal:** validate the existing streaming Parquet path in a `pyarrow` environment on the recovered corpus.

**Do:** write partitioned Parquet in streaming batches; replay back to canonical events; test multiple worker counts and partition sizes; record throughput/memory.

**Acceptance:** event counts, source sequences, visibility order, state frame hashes and derivation hashes match canonical replay exactly across worker counts; benchmark artifact saved.

## P0.4 — Deploy same-instant sibling integration

**Goal:** preserve one atomic NEXUS replay instant across AION, ARGUS, ATHENA and DAEDALUS service boundaries.

**Do:** use `ReplayBus.instants()` + `SiblingInstantRouter.package_instant()`; persist derivation + source-health context to AION; enforce ARGUS `CANDLE_PROXY`; route provenance/health/quality to ATHENA; route research-only candidate to DAEDALUS.

**Acceptance:** identical `decision_ns`/`frame_hash` across sibling packets; contract-drift sentinel clean or reviewed; AION as-of/hash-chain recovery passes; no sibling receives `production_authorized=true` from NEXUS.

## P0.5 — Make contract drift a CI gate

**Goal:** prevent silent adapter staleness when sibling boundary code changes.

**Do:** capture `ContractDriftSnapshot` in CI, compare to reviewed baseline, rerun exact sibling contract validation on semantic drift, update baseline only with reviewed adapter changes.

**Acceptance:** nonsemantic formatting churn is reported but not treated as semantic drift; AST-semantic drift fails the compatibility gate until validation passes.

## P1 — Next capability work

1. Authenticated live adapters with observed receipt times, reconnect epochs, sequence gaps, watermark/backpressure telemetry and idempotent restart.
2. Futures canonical identity/roll policy with contract month, continuous-series lineage, venue/session metadata and no execution ambiguity.
3. Distributed deterministic replay benchmark and restart-from-checkpoint parity.
4. CI certification of every promoted transform through prefix invariance.
5. Source-class SLO calibration from real live evidence; do not invent universal thresholds.
6. Durable AION write-through for research-run manifests, health planes and derivation genealogy.
7. Full-corpus representation-family consensus/ablation, then hand statistical usefulness questions to DAEDALUS.

## Required first commands

```bash
git status --short
git log -5 --oneline
git tag --list 'nexus-v0.3-sol-handoff'
PYTHONPATH=src pytest -q
python -m compileall -q src tests
```

Expected NEXUS baseline at SOL freeze: **117/117 tests passing**.

Then rerun `scripts/validate_sibling_contracts.py` and `scripts/snapshot_sibling_contracts.py` against the sibling roots available in the receiving environment.

— **SOL**
