# JANUS ∞ Run 017 — Constrained Temporal Delegation + Key Rotation Lineage

Adds direct, scope-bound authority delegation and same-authority key rotation lineage to the bitemporal authorization gate. Delegation is deliberately non-transitive: only a delegate directly named by a policy principal for the exact subsystem/evidence class can satisfy that principal. Quorum counts satisfied policy principals, not raw signer keys, preventing delegated identities from multiplying quorum weight. Key rotations are same-authority only and are surfaced in authorization decision lineage.

Ownership invariant: cryptographic delegation never broadens NEXUS/AION/ARGUS/ATHENA/DAEDALUS/Icarus scope; subsystem + evidence_class remain mandatory boundaries.
