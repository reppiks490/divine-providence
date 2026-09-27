# SuperMesh-X v3.0 Signed Runtime Evidence Design

Goal: authenticate v2.9 runtime evidence without allowing signatures to confer execution authority.

Design: introduce a provider-neutral Ed25519 signer/verifier boundary over canonical evidence envelopes. A trust store maps key IDs to public keys and lifecycle state, rejects unknown/revoked keys, and permits explicit rotation. Signed journal admission verifies signature, run identity, monotonic fence, and replay identity before appending to the existing evidence chain. Concrete-adapter conformance is represented by launch/resource/mount/DNS/process/reconciliation evidence bindings; no VM/container launch is claimed.

Security invariants: private keys never enter evidence receipts; signature verification precedes journal admission; signatures authenticate claims but never grant capabilities; stale fences/replays/tampering/reordered evidence fail closed; v2.9 APIs remain compatible. Ed25519 follows RFC 8032; attestation shape follows in-toto/SLSA principles of signed statements bound to subjects/builders rather than copying those specifications wholesale.

Testing: RED-first tests cover tamper, wrong/unknown/revoked key, rotation, replay, stale fence, authority non-escalation, and signed journal chain verification. Full regression, compile, smoke, package validation, cache cleanup, ZIP integrity, and fresh-extraction verification are release gates.
