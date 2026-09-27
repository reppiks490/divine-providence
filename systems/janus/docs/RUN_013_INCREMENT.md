# JANUS ∞ Run 013 — Merkle Evidence DAG + Verification Contract Negotiation

Run 013 upgrades Run 012's selective causal evidence bundle from a whole-bundle commitment to per-object verifiability. `build_merkle_evidence_manifest()` constructs a deterministic binary SHA-256 Merkle tree over the existing content-addressed chunk digests and emits an inclusion proof for every evidence object. Odd tree levels duplicate the final node deterministically; this is part of the v1 format contract.

`verify_merkle_inclusion()` lets a receiver authenticate an individual evidence chunk against the root without possessing every sibling payload. `missing_evidence_chunks()` compares a receiver's local content-addressed store against the manifest and returns exactly the missing digests.

`verification_capabilities()` and `negotiate_verification_contract()` add a fail-closed compatibility gate over protocol, bundle format, Merkle format, certificate kind, and hash algorithm. No schema/version downgrade is inferred.

Authority boundaries are unchanged. These mechanisms establish transport integrity and replay compatibility only; they do not elevate evidence authority or semantic legitimacy.
