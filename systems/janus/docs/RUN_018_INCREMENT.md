# JANUS ∞ Run 018 — Revocable Delegation + Complete Rotation Proof Chains

Run 018 extends Run 017 without changing sibling-system authority ownership.

## Built
- `revoke_authority_delegation(...)` with knowledge-time-aware revocation filtering.
- Rotation DAG cycle rejection before mutation.
- Complete predecessor-chain reconstruction for accepted successor signing keys.
- Authorization decision digests continue to bind delegation and complete rotation lineage.

## Invariants
- Delegation remains direct and non-transitive by default.
- Delegation remains scoped by subsystem and evidence class.
- Cross-authority rotation remains forbidden.
- Rotation lineage must be finite and acyclic.
- Revocation learned later does not rewrite an earlier knowledge-time decision.

## Verification
71/71 tests pass; Python compilation passes.
