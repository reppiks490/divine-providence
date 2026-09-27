# Signed Runtime Evidence — v3.0.0

SuperMesh-X authenticates canonical runtime evidence envelopes with Ed25519. A verifier trust store owns public-key identity, rotation and revocation state; unknown or revoked keys fail closed. Verification occurs before journal mutation. Signed statements bind run identity and fencing token, and replay identities are based on canonical statement digests.

A signature authenticates evidence only. It cannot grant capabilities or external-write authority. Signed claims are intersected with the pre-existing allowed-capability set before admission. Private keys and raw secret references are excluded from receipts.

The envelope is intentionally provider-neutral. Its security model follows RFC 8032 for Ed25519 and the in-toto/SLSA principle that verifiable provenance is bound to an identified signer/builder and subject. It is not represented as SLSA certification.
