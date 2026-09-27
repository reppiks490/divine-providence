# ASCENSION Evaluator Fabric v0.8

**Lifecycle:** CANDIDATE. **Read-only. No sibling adoption is claimed.**

This version adds strict RFC 9162-style Merkle inclusion verification on top of the known-good v0.7 compact-consistency and signed-witness primitives. It binds a declared `leaf_index` and `tree_size` to proof orientation, validates exact proof geometry before hashing, enforces uint64/index and 32-byte hash domains, preserves CT domain separation, and composes strict inclusion with the v0.7 transition/witness gate.

Primary interfaces:
- `merkle_leaf_hash(data)`
- `expected_inclusion_path_length(leaf_index, tree_size)`
- `verify_strict_inclusion(leaf_hash, leaf_index, tree_size, root_hash, inclusion_path)`
- `verify_transparency_evidence(...)`

Rollback: Evaluator Fabric v0.7 remains unchanged. Adapter v0.3 is intentionally not modified in this package.
