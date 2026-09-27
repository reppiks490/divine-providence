# Replayable Market Event Analysis

1. Capture the earliest verifiable public event timestamp plus publication and retrieval timestamps.
2. Canonicalize text/entity identifiers and cluster syndicated copies within a bounded time window.
3. Preserve independent source families and the earliest record in an append-only hash chain.
4. Resolve relevant assets from the market-mover registry and current topic/exposure mapping.
5. Capture pre-event and post-event market observations with explicit observation times.
6. Build an observed shock graph using standardized move magnitudes, lags, and channels.
7. Check competing macro, company, policy, geopolitical, and market-structure events.
8. Compute conservative association confidence and decay it as evidence becomes stale or conflicting.
9. Build a point-in-time replay bundle that excludes anything unavailable at the requested cutoff.
10. Store the event-family id, ledger hashes, evidence lineage, market snapshot ids, and bundle hash for later audit or backtest replay.

Never infer an unqualified causal relationship from timestamp proximity alone.
