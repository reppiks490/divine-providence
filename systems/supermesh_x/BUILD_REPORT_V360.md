# Build Report v3.6.0

Scope: additive signed replay compaction for the durable public gossip journal.

## Design
The physical journal remains append-only and untouched. Compaction is a replay optimization and integrity checkpoint, not destructive log pruning. A versioned immutable snapshot authenticates a fully verified journal prefix; a small witness-signed anchor chain designates the newest accepted snapshot. `load_compacted()` verifies the snapshot, verifies the complete anchor chain, checks the exact on-disk journal prefix hash/length, reconstructs the latest authenticated receipt per log, then replays only the suffix.

## Rollback model
- Local rollback of only the snapshot is rejected because the latest signed anchor chooses the accepted snapshot epoch/digest.
- Anchor entries are monotonic, hash-chained, witness-signed, and require strictly advancing journal sequence.
- Optional external pins (`minimum_snapshot_epoch`, `expected_anchor_digest`) detect rollback of the whole local snapshot+anchor state when the pin is retained in an independent trusted location.
- No purely local file format can detect restoration of every local trusted file to an older internally consistent image without an independently retained trust floor; the API exposes that boundary explicitly instead of claiming otherwise.

## Crash / publication ordering
1. Strictly replay and authenticate the current full journal.
2. Build and quorum-sign the snapshot and anchor statements in memory.
3. Create the snapshot with exclusive-create semantics, fsync it, then fsync its parent directory where supported.
4. Hold an exclusive fail-closed compaction lock for the anchor path while selecting and publishing the next epoch.
5. Immediately before publishing the anchor update, compare the current anchor head with the statement's `previous_anchor_digest` and expected next epoch; refuse a stale commit if another writer changed it.
6. Atomically replace the tiny anchor journal with old bytes plus the new signed entry, fsync the replacement, then fsync the parent directory where supported.
7. The gossip journal itself is never truncated or rewritten.

If anchor persistence fails after snapshot publication, the prior anchor remains authoritative and the new snapshot is merely orphaned. A process crash can leave a stale `.compaction.lock`; this is intentionally fail-closed and requires operator verification before removal rather than guessing that no competing writer exists.

## Research basis
Public read-only research was used for design validation only. High-signal sources included The Update Framework rollback/freeze and signed snapshot concepts, the C2SP transparency-log witness protocol, and crash-consistency guidance around fsync/atomic replacement. No private account data, credentials, repository payload, or proprietary state was sent to public search providers.

## Test-first evidence
- RED: 5/5 new v3.6 behavioral tests failed because `DurableGossipJournal.compact` did not exist.
- GREEN: 5/5 new v3.6 behavioral tests passed after the minimum implementation.
- Focused trust/recovery regression immediately after implementation: 45 passed.
- Packaging contract was also introduced RED first: it failed on the prior 3.5.0 manifest before v3.6 metadata/docs were added.
- Independent author review found a concurrent-writer race at anchor publication. Two additional RED tests failed first (exclusive-lock contention and stale-head compare-before-publish).
- GREEN after the concurrency hardening: 7/7 v3.6 behavioral tests passed; focused trust/recovery regression: 47 passed.

## Final source-tree verification
- Full regression: 338 passed.
- Python compileall with external bytecode cache: PASS.
- Executable smoke: PASS; `package_version=3.6.0` and `gossip_signed_compaction=true`.
- Package validator: PASS.
- The extracted source is not a Git checkout, so release identity is the versioned package SHA-256 plus the cycle state capsule rather than an invented commit ID.

ZIP integrity, final artifact SHA-256, and fresh-extraction verification are recorded in the versioned cycle state capsule because those values exist only after this source tree is packaged.


Stale when: the compaction storage protocol, witness-policy model, or durable-file publication semantics change.
