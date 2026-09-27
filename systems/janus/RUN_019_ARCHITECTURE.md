# JANUS ∞ Run 019 — Portable Trust-Lineage Evidence

Run 019 makes the authorization lineage itself a proof-carrying artifact. A sender can export the minimal policy/key/delegation/rotation closure used by one authorization decision. Every trust object is canonicalized and SHA-256 content-addressed; a deterministic bundle digest commits to the closure. A separate binary Merkle manifest supports selective missing-object discovery and per-object inclusion proofs.

A receiver verifies the bundle before mutation, imports only the supported trust-object kinds, reruns temporal authorization against the original signed evidence root, and requires exact reproduction of the sender's authorization-decision digest. This does not grant JANUS semantic authority over sibling systems: exported policies remain subsystem/evidence-class scoped, direct delegation remains non-transitive, and quorum is still counted by policy principal.

Current limitation: selective trust-object transport primitives exist (Merkle manifest + missing-chunk discovery), but resumable trust-sync sessions and atomic staging/rollback are not yet implemented.
