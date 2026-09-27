# Witness Policy Epochs and Durable Gossip — v3.4.0

SuperMesh-X v3.4 adds an additive witness-policy layer over the v3.3 RFC 9162 path. A policy epoch contains an Ed25519 witness-key set, threshold, explicit revocations, and descriptive metadata only. Policy metadata is forbidden from encoding execution authority.

Rotation follows a TUF-style dual-threshold transition: epoch `N+1` must be exactly one greater than epoch `N`, and the rotation statement must satisfy both the current-policy threshold and next-policy threshold. Duplicate public-key aliases are rejected so one cryptographic identity cannot satisfy multiple quorum slots. Revoked keys do not count. The durable policy root retains signed transition evidence so re-checksummed policy-history tampering fails cryptographic replay validation.

When `EpochWitnessRegistry` is supplied to `RFC9162WitnessedCheckpointLedger`, checkpoint signatures bind `policy_epoch` and `policy_digest`. Legacy v3.3 registries omit those fields and retain their original signature format.

`DurableGossipJournal` authenticates a receipt, durably appends a hash-chained JSONL envelope with fsync, and only then exposes it to the in-memory gossip view. Replay verifies the hash chain, signatures, compact consistency evidence, monotonic tree state, and non-regressing policy epochs. New appends must match the current policy epoch; historical epochs are accepted only during authenticated replay.

`cross_runtime_vectors.py` defines the `supermesh-json-v1` canonical JSON profile (sorted keys, compact separators, ASCII escaping, no NaN) and deterministic Ed25519 conformance vectors for ChatGPT/Codex/Claude adapters. It is deliberately not labeled RFC 8785/JCS.

Primary design references: The Update Framework root rotation workflow (sequential versioning, old+new threshold signatures, unique key counting, durable root persistence); C2SP transparency log checkpoints (consistent signed checkpoints, unknown-signature tolerance enabling key rotation/cosigning); RFC 9162 consistency proofs; transparency-dev witness persistence patterns.
