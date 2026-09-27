# JANUS ∞ Run 014 — Signed Proof Roots + Incremental Evidence Synchronization

Run 014 extends Run 013 without changing subsystem authority boundaries.

## Built

- Ed25519 signing key generation for reference/testing deployments.
- Domain-separated `janus-signed-proof-root-v1` envelopes over Merkle roots.
- Explicit receiver trust-store verification. A valid signature authenticates the root's signer; it does **not** make the signed facts semantically authoritative.
- Incremental evidence synchronization that combines already-held chunks with fetched missing chunks, validates every content hash and Merkle inclusion path before mutation, imports only a complete verified closure, reruns the causal engine, and emits a deterministic synchronization receipt.
- Schemas for signed roots and synchronization receipts.

## Invariants

1. Signature verification and project authority adjudication remain separate.
2. Unknown signing authorities fail closed.
3. Evidence mutation happens only after complete chunk-set, content-hash, and Merkle-path verification.
4. A sync succeeds only if the receiver reproduces the sender's minimal causal-certificate digest.
5. NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus ownership boundaries are unchanged.

## Dependency note

Run 014 adds `cryptography>=41` for Ed25519. This is the first non-standard-library runtime dependency in the reference package and should be pinned/managed by the live repository if adopted.
