# JANUS ∞ Run 021 — Crash-Safe Synchronization Ledger, Signed Receipt Chain, Concurrency Guard

Run 021 extends Run 020 without changing JANUS ownership boundaries.

## Added
- Durable `sync_session_chunks` inventory for causal/trust evidence with missing/acquired/verified states and restart-safe idempotent updates.
- Receiver-state optimistic concurrency guard captured when a deterministic session begins; stale staging promotion fails closed.
- Ed25519 joint-receipt signing with domain `JANUS_JOINT_RECEIPT_V1` and independent signature verification.
- `joint_receipts` append-only receipt ledger; each new receipt commits to the previous receipt digest.
- Forward-compatible migration for Run 020 databases adding the receiver-state digest.

## Invariants
- Chunk checkpointing is control-plane state and does not alter project truth.
- A stale session cannot overwrite project-domain changes accepted after session creation.
- Receipt signatures authenticate receipt origin/integrity; they do not grant sibling-system semantic authority.
- NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus authority remains governed by the explicit temporal authorization machinery.
