# Icarus/JANUS State Capsule — Run 020

Authoritative offline checkpoint: JANUS ∞ Run 020.
Resume from this package, not the older Run 002 prompt baseline.

Completed: deterministic sync-session checkpointing; isolated staging-twin synchronization; portable trust-lineage import/replay; causal Merkle verification/import/replay; exact authorization and causal-certificate reproduction; atomic promotion on success; failed-session recording without project-domain promotion; joint proof receipt binding trust+causal evidence and temporal scope.

Verification: inherited Run 019 74/74 tests passed. Run 020 RED 3/74 additions failed before APIs existed. Final 77/77 passed. Python compileall passed. No live-repo reconciliation performed.

Interfaces: `begin_sync_session`, `sync_session`, `atomic_joint_sync`, existing trust-lineage and causal-evidence APIs. Dependency remains `cryptography>=41` plus Python stdlib/sqlite.

Ownership: JANUS owns project-twin temporal truth/conflict/proof synchronization only. NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus authority remains explicit and policy-scoped. Infrastructure persistence, VECTOR intelligence, and ASCENSION evaluation are not absorbed.

Risks: staging promotion uses SQLite backup semantics and has not been stress-tested under concurrent writers/process crashes; sync sessions track transaction identity/status but do not yet persist per-chunk fetch inventory; joint receipts are content-digested but not yet independently signed/receipt-chained; live repo parity remains unproven.

Next: Run 021 — crash-safe chunk inventory + receipt signing/chaining + concurrency/lock tests. Add per-session acquired/missing chunk ledger, restart recovery, idempotent resume, signed joint receipt, prior-receipt hash chain, and concurrent promotion guard.

Resume instruction: unpack Run 020; run `PYTHONPATH=src pytest -q` and `python -m compileall -q src tests`; require 77/77 before mutation; then implement Run 021 RED→GREEN without weakening authority boundaries.
