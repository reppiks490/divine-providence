# NEXT MODEL HANDOFF — NEXUS Adaptive Market Fabric

## Goal
Continue NEXUS as the CSV-first causal market-data substrate for the Icarus stack. Do not restart it and do not merge it into an existing sibling.

## Done
- Built and tested v0.1 implementation across catalog, identity, timing, replay, causal alignment, features, synthetic tickers, factor ensemble, topology, novelty, change detection, ablation, hash ledger and sibling adapters.
- Profiled the actual materialized ZIP: 476 physical `.csv` entries, 238 usable, 238 AppleDouble sidecars, 1,970,753 rows, 7 exact-byte duplicate entries, 12 fractional-time streams, 64 cadence-ambiguous streams.
- Proved catalog determinism by identical output SHA across two full runs.
- Ran actual NQ/ES/VIX/DXY/VXN multi-asset smoke.
- Cross-read and locally tested ARGUS, ATHENA, AION and DAEDALUS handoffs.

## Verification
- NEXUS: `22 passed`
- ARGUS: `4 passed`
- ATHENA: `3 passed`
- AION: `11 passed`
- DAEDALUS: `45 passed`
- Python compileall: passed
- real-corpus catalog determinism: passed

## Priority next tasks

### P0 — authoritative corpus reconciliation
Locate the full GitHub/Work corpus expected to exceed 800 real CSV files. Reconcile archive/member hashes with AION's prior 626-usable checkpoint and the 238-stream materialized ZIP. Do not claim full coverage until resolved.

### P0 — persistent Market Fabric Ledger v2
The current SQLite hash chain proves append-only frame identity. Extend to partitioned Arrow/Parquet event storage, checkpoint manifests and deterministic frame hashes while keeping AION as evidence-memory owner.

### P0 — representation-aware clock policies
Build explicit policies for:
- conventional time bars
- variable-cadence charts (Renko/range/etc.)
- tick/volume-labeled exports
- macro revisions/releases
- authenticated event feeds

Do not flatten all representations onto one fictional regular clock. Repeated timestamp alignment must require reviewed sequence/availability semantics.

### P1 — scalable corpus engine
Replace whole-file timestamp lists with chunked/streaming statistics and parallel profiling. Benchmark at >10M rows. Require deterministic hashes across worker counts.

### P1 — factor system v2
Add robust PCA, shrinkage dynamic factor baseline, rolling factor stability/turnover, cluster-aware weighting, component caps and explicit uncertainty. Compare all complex methods against equal/inverse-vol baselines before retaining them.

### P1 — topology v2
Add partial-correlation network, edge survival, community detection and rolling lead/lag stability. Treat transfer entropy/Granger methods as DAEDALUS research candidates, not causal truth.

### P1 — missingness and quality state
Make source age/gaps/clock uncertainty dynamic time series. Add missingness-pattern telemetry for ATHENA while preventing missingness from silently becoming imputed market truth.

### P1 — integration tests against real sibling contracts
- instantiate/validate NEXUS AION dictionaries with AION `SourceSpec`/`Observation`
- validate ARGUS exports can only be `CANDLE_PROXY` for CSVs
- package ATHENA input provenance without constructing ATHENA `WorldState`
- feed NEXUS derived features into DAEDALUS research protocol without bypassing promotion gates

### P2 — live adapter frontier
Add Parquet/Arrow, SQLite, WebSocket/Kafka, broker/exchange and macro-source adapters. Route authenticated depth/trade semantics through ARGUS contracts rather than inventing a parallel microstructure truth layer.

## Risks / unresolved
- Filename representation/timeframe claims remain untrusted by design.
- Historical CSV first-known availability is generally not proved; AION export correctly refuses to invent it without an explicit availability input.
- Current real smoke is small and engineering-only.
- No production authorization exists.

## Environment
Python >=3.11 with NumPy, pandas and pytest. In the current offline runtime, use `PYTHONPATH=src pytest -q`; editable pip install attempted network access for build isolation and failed for that environmental reason only.

## Next agent
Run a foresight/receive check against this handoff, current git status and `VALIDATION_STATUS.md`, then start with authoritative corpus reconciliation and representation-aware clock policies.
