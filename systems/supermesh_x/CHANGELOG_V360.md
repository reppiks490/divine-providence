# SuperMesh-X v3.6.0

## Signed replay compaction and rollback-resistant snapshot anchoring
- Added immutable witness-signed gossip compaction snapshots containing the verified journal prefix boundary, SHA-256 prefix hash, terminal hash-chain digest, latest authenticated receipt per log, and witness-policy binding.
- Added a compact append-only signed anchor journal. Each anchor advances exactly one snapshot epoch, chains to the prior anchor digest, and binds the snapshot digest plus journal prefix state.
- Added `DurableGossipJournal.load_compacted()` to reconstruct authenticated state from the signed snapshot and replay only entries after the captured byte offset. The original journal is never truncated, so legacy `load()` remains valid and forensic history is preserved.
- Added optional `minimum_snapshot_epoch` and `expected_anchor_digest` trust floors. These allow a caller to pin state outside the local snapshot/anchor pair and detect rollback even if all local compaction files are restored to an older previously valid state.
- Snapshot paths are create-only. A new compaction cannot overwrite the sole good snapshot. Snapshot publication precedes anchor commitment; an anchor-write failure leaves the prior anchor authoritative and at most an orphan immutable snapshot.
- Added fail-closed checks for snapshot tamper, anchor-chain tamper/rollback, journal-prefix mutation/truncation, stale snapshot selection, insufficient witness quorum, and in-memory/disk journal divergence.
- Added an exclusive per-anchor compaction lock plus compare-before-publish validation of the previous anchor digest/epoch. Concurrent writers cannot silently overwrite one another; a stale lock after a process crash deliberately blocks future compaction until an operator verifies and removes it.

## Compatibility and authority
- Existing v3.5 strict load and torn-tail recovery semantics are unchanged.
- v3.1 remains the protected stable baseline; v3.6 is an additive candidate only.
- Compaction signatures authenticate public evidence state only. They do not grant execution, external-write, brokerage, credential, or routing authority.


Stale when: a later release changes compaction concurrency, snapshot/anchor schemas, or the rollback trust-floor contract.
