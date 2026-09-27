# Signed Gossip Replay Compaction

SuperMesh-X v3.6 adds an additive replay checkpoint for `DurableGossipJournal`. It is deliberately non-destructive: the canonical JSONL journal stays append-only so legacy `load()` continues to work and the complete forensic history remains available.

## Artifacts

A **snapshot** is an immutable, create-only JSON document signed by the active witness quorum. Its signed statement binds:
- `snapshot_epoch`;
- the compacted `journal_sequence` and terminal `journal_last_digest`;
- exact `journal_prefix_bytes` and SHA-256 of that prefix;
- the latest authenticated gossip receipt for every observed log; and
- witness `policy_epoch` / `policy_digest` when an epoch registry is used.

An **anchor journal** is a small signed chain with one entry per accepted snapshot. Each entry increments the snapshot epoch exactly once, references the previous anchor digest, and binds the selected snapshot digest and the same journal-prefix boundary. Journal sequence must strictly advance between anchors. Compaction holds an exclusive per-anchor lock and rechecks the anchor head immediately before replacement so a second writer cannot publish from a stale head.

## Loading

`DurableGossipJournal.load_compacted(journal, snapshot, anchors, registry, ...)` performs these gates before exposing state:
1. verify snapshot structure, digest, witness signatures, and historical policy threshold;
2. verify every anchor entry, signature, monotonic epoch, sequence advancement, and anchor hash chain;
3. require the supplied snapshot to match the latest anchored snapshot;
4. enforce optional external rollback pins;
5. hash the exact current journal prefix and require it to match the signed snapshot;
6. authenticate the snapshot's latest receipt per log;
7. replay only the bytes after the signed prefix boundary, starting from the signed terminal sequence/digest.

## Threat boundary

The local anchor journal detects stale-snapshot selection and tampering while the latest local anchor state is retained. If an attacker can restore **all** local trusted files to an older previously valid image, cryptographic signatures alone cannot reveal that fact. Use `minimum_snapshot_epoch` or `expected_anchor_digest` with a trust floor retained outside that rollback domain (for example a separately governed state capsule or external witness store).

This compaction layer authenticates evidence only. It never grants execution, network-write, credential, messaging, brokerage, order, or production authority.

## Operational rules

- Never reuse a snapshot path; snapshots are create-only and versioned.
- Do not delete older good snapshots solely because a newer file exists; the anchor commit determines acceptance.
- Treat an orphan snapshot after an anchor-write failure as uncommitted.
- A stale `.compaction.lock` is a fail-closed recovery condition. Verify that no compactor is active and inspect the anchor/snapshot state before operator removal; never auto-delete the lock based only on age.
- Keep strict `load()` available for full forensic replay and independent audit.
- Apply torn-tail recovery to the base journal only through the existing narrow `recover()` path; do not auto-repair authenticated corruption.


Stale when: snapshot/anchor schemas, witness threshold rules, lock semantics, or durable replacement primitives change.
