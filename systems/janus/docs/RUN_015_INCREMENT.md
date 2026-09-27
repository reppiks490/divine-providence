# JANUS ∞ Run 015 — Temporal Trust Ledger + Threshold Authorization

Run 015 makes root authentication bitemporal and subsystem-scoped. Signing keys now have valid-time, knowledge-time, optional expiration, and revocation. Authorization policies bind a subsystem/evidence-class pair to an explicit authority set and quorum threshold. `verify_authorized_merkle_root_at()` requires both cryptographic validity and a policy-valid quorum at `(valid_at, known_at)`.

Key invariants: signer identity never implies semantic authority; a key learned after `known_at` cannot authorize earlier knowledge; revocation affects later knowledge without rewriting earlier justified belief; policies are scoped so NEXUS authority does not silently authorize AION/ARGUS/ATHENA/DAEDALUS domains.
