# V39 Journaled Governance Transaction Contract

The governance composite protocol now has a durable append-only state machine: PREPARED, GOVERNANCE_WRITTEN, ADMISSION_WRITTEN, COMMITTED. Phase transitions are sequential only. Every record binds epoch, epoch hash, phase, predecessor record hash and canonical record hash. HEAD binds the latest phase record. Durable writes fsync the record, atomically rename it, fsync HEAD, atomically rename HEAD, then fsync the directory.

The journal is evidence/persistence safety state only. It exposes no execute, mutate, promote, rollback, lease, routing, sibling semantic, or production authority. V39 does not yet replace the V38 composite coordinator with this journal; that integration and exhaustive failpoints remain the next checkpoint.
