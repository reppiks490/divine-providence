# RFC 9162 Witness + Gossip Compatibility Path — v3.3.0

## Compatibility rule
`WitnessedCheckpointLedger`, `_root`, `consistency_proof`, and `verify_consistency_proof` are the v3.2 legacy witness surface and remain unchanged. Their odd-leaf behavior is intentionally not relabeled as RFC 9162.

v3.3 adds an independent `RFC9162WitnessedCheckpointLedger` plus `rfc9162_root`, `rfc9162_consistency_proof`, and `verify_rfc9162_consistency_proof`. The new root follows RFC 9162 §2.1.1 domain separation (`0x00` leaves, `0x01` internal nodes) and split-at-largest-power-of-two tree construction. Compact consistency paths follow §2.1.4 and do not embed old/new leaves.

## Witness state
`checkpoint_and_persist()` returns only after an atomic snapshot write succeeds. A persistence exception restores the prior in-memory checkpoint and fails closed. Snapshots serialize public checkpoint/cosignature state only, include a SHA-256 corruption checksum, and are revalidated against the supplied witness registry on load. Private witness keys are never serialized.

The checksum is corruption detection, not a replacement for witness signatures. Authenticity comes from the stored Ed25519 cosignatures and registry verification.

## Gossip
`GossipReceiptStore` detects same-size conflicting roots and rollback observations. Stores can merge monotonic receipts after a partition. When constructed with a `WitnessRegistry`, the store additionally verifies quorum signatures, signed statement fields, RFC 9162 consistency evidence, and the signed consistency digest before admitting a receipt. Without a registry it is a conflict detector only and grants no trust or authority.

## Authority boundary
Witness and gossip signatures authenticate evidence. They never grant tool, shell, messaging, brokerage, deployment, or external-write authority.

## Protocol sources
- RFC 9162 §§2.1.1 and 2.1.4: Merkle Tree Hash and compact consistency proofs.
- C2SP tlog-witness: witness keeps the latest verified checkpoint, verifies consistency from the old size, persists the new checkpoint before success, and must not cosign invalid evolution.
- transparency-dev/witness: witnesses counter-sign only append-only checkpoint evolution.

## Known limits
This package is a local reference/control-plane implementation, not a drop-in C2SP HTTP server. It does not claim wire-format, note-signature, base64-line, or public witness-network interoperability. Gossip transport is caller-supplied. Multi-process locking/distributed serialization must be provided by an execution adapter.
