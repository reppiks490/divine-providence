# NEXUS → ChatGPT Work Handoff

**Package signature:** SOL
**Receiving model:** Sol Extra High
**Project:** NEXUS Adaptive Market Fabric

## Primary package
Open the persistent Library file:

`/NEXUS/NEXUS_ADAPTIVE_MARKET_FABRIC_v0.3_SOL_FOR_SOL_EXTRA_HIGH.zip`

Then read, in this order:
1. `READ_FIRST_SOL_EXTRA_HIGH.md` inside the ZIP
2. `docs/SOL_EXTRA_HIGH_HANDOFF.md`
3. `docs/SOL_EXTRA_HIGH_TODO.md`
4. `docs/current-state.md`
5. `docs/next-task.md`
6. `docs/progress.md`

## Required receive procedure
Use a baton-pass / foresight-style receive:
- verify the working tree and latest tagged/committed state before modifying anything;
- rerun the NEXUS test suite and compile checks from the packaged copy;
- verify sibling-boundary tests against AION, ARGUS, ATHENA, and DAEDALUS where those packages are available;
- compare the repo state to the handoff claims and correct any drift before building further;
- preserve all source lineage and never collapse distinct market representations solely because their symbols/timestamps resemble each other.

## Current architectural ownership
NEXUS owns the market-data operating fabric: forensic ingestion, stream identity, causal/availability-aware synchronization, deterministic replay, adaptive synthetic factors/tickers, topology/lead-lag telemetry, quality/health state, representation review, and versioned sibling export contracts.

NEXUS does **not** take over:
- ARGUS: true microstructure / order-flow / execution-physics authority
- ATHENA: supervisory world-state, risk, confidence, abstention and routing authority
- AION: durable evidence memory and historical atlas
- DAEDALUS: scientific research validation / promotion authority
- ICARUS: production execution authority

## Known corpus facts to preserve and re-verify
The currently accessible `Full csv candles only.zip` was profiled as 476 CSV-named physical entries: 238 usable market files plus 238 macOS AppleDouble/resource-fork sidecars. The usable set was measured at 1,970,753 parsed rows. A prior AION/PARALLAX checkpoint referenced a larger corpus (626 usable entries / ~12.59M rows), so corpus reconciliation remains a high-priority unresolved item until all archive batches are accessible.

## Immediate continuation goal
Push NEXUS from a strong research/data fabric into a production-grade cross-market substrate without violating sibling ownership. Prioritize:
1. Reconcile the authoritative full CSV corpus and ingest missing archive batches.
2. Finish representation-specific clock policy review for time, tick, volume, Renko/range/event-like streams.
3. Scale storage/replay toward partitioned Arrow/Parquet and streaming sources while preserving nanosecond/availability semantics.
4. Extend robust factor/topology methods and dynamic source-quality/missingness telemetry.
5. Maintain strict leakage audits, derivation genealogy, sensor/cluster ablation, and hard admission gates.
6. Expand exact contract-drift tests against AION/ARGUS/ATHENA/DAEDALUS.
7. Do not add broker/order authority to NEXUS.

## First command-equivalent goal for Sol Extra High
"Receive and audit the SOL NEXUS v0.3 handoff. Verify the package before changing it. Continue from the existing architecture; do not restart or duplicate sibling capabilities. Resolve the highest-value unfinished item from `SOL_EXTRA_HIGH_TODO.md`, update tests/docs/baton state, and leave the tree in a verified checkpoint."

— SOL
