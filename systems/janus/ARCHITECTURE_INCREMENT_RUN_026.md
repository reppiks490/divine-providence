# JANUS ∞ Run 026 — Storage-Fault Matrix + Corrupt-Stage Quarantine

Run 026 hardens the promotion boundary against damaged staging databases and injected storage-write failure. Before authoritative backup, JANUS performs SQLite `PRAGMA integrity_check`. Deliberately corrupted or truncated stage files are rejected, copied to a forensic quarantine artifact, and represented by content-addressed `janus-storage-quarantine-v1` evidence. Injected ENOSPC-like failure aborts a prepared promotion without producing a joint receipt or changing authoritative project truth.

Ownership remains unchanged: JANUS owns project-twin temporal truth/conflict/proof synchronization. Quarantine is evidence about JANUS staging state, not an Infrastructure persistence authority.

Acceptance invariants:
- corrupt/truncated staging state is never promoted;
- authoritative receiver digest remains unchanged on storage fault;
- no joint receipt is invented for failed storage promotion;
- quarantined bytes are retained with SHA-256 where readable;
- authoritative SQLite remains integrity-check clean;
- prepared ENOSPC-like failure resolves aborted and remains recoverable.
