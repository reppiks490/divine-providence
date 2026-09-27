# v3.3.0 — RFC 9162 Witness Durability + Gossip

- Preserved the v3.2 legacy witness/Merkle surface byte-for-byte at the API/behavior boundary.
- Added an additive RFC 9162 SHA-256 Merkle root and compact consistency-proof implementation.
- Added `RFC9162WitnessedCheckpointLedger` with quorum Ed25519 checkpoint signatures and compact proof digest binding.
- Added atomic public witness-state snapshots and `checkpoint_and_persist()` rollback-on-storage-failure behavior.
- Added `GossipReceiptStore` for partition recovery, rollback/same-size equivocation detection, and optional authenticated receipt admission.
- Witness/gossip evidence remains non-authoritative for external writes, process execution, brokerage, or capability grants.
- No Gmail, Finances, broker, calendar, messaging, or live-trading path is introduced.
