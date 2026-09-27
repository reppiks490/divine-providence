# Research Notes — Cycle 021

- Exact first-party Deep Research was checked but not exposed/callable in this runtime.
- Exa research was actually invoked against official in-toto, SLSA, and Sigstore-style attestation/provenance patterns.
- High-signal design patterns retained: bind subject identity by digest; make predicate/schema identity explicit; preserve signer/trusted-root/policy identities; separate envelope authentication from predicate semantics; compare against expected artifact/identity rather than trusting syntactic validity; do not turn a verification receipt into a claim that this component re-ran the cryptography.
- File Library search discovered a PROMETHEUS v0.5 verified checkpoint and design that expose an external attestation + verification receipt contract. This materially improves the conformance target but does not constitute the missing signed runtime manifest.
