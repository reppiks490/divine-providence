# Build Report v3.5.0

Scope: crash-tail quarantine/recovery for the v3.4 durable gossip journal.

Design invariant: automatic recovery is permitted only when the final bytes cannot form a JSON record. A syntactically complete record that fails digest, chain, signature, policy, rollback, or equivocation verification is never auto-truncated.

Durability ordering: quarantine tail -> fsync quarantine -> write verified prefix temp -> fsync temp -> atomic replace -> directory fsync -> strict replay.

Research basis: SQLite WAL crash/checkpoint ordering, TUF rollback/freeze protections, and transparency checkpoint/witness persistence patterns. External research remained read-only and received no private or proprietary payload.
