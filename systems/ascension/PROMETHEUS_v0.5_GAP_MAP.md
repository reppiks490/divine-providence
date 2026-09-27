# PROMETHEUS v0.5 -> ASCENSION Adapter v0.4 Gap Map

Evidence class: **DECLARED_CONTRACT / VERIFIED CHECKPOINT DESCRIPTION**, not signed runtime manifest.

PROMETHEUS v0.5 already declares or records concepts that align strongly with the conformance profile: `plugin_evidence_id`, `subject_sha256`, `predicate_type`, `envelope_ref`, `envelope_sha256`, `verification_material_sha256`, `signer_identity`, `attestation_format`; and verification receipt fields `attestation_id`, `verifier_id`, `trusted_root_id`, `verification_policy_id`, `checks`, `external_verification_ref`. It also requires the core receipt checks `signature`, `subject_digest`, `signer_identity`, and `trusted_root`.

The recovered checkpoint explicitly states that PROMETHEUS does **not** itself implement DSSE parsing, X.509/Sigstore/Rekor verification, key management, or trust-root rotation. Its receipt records what an identified external verifier reported.

### Still not located as authoritative runtime Transfer material

- exact runtime `ResearchProvenanceManifest` body intended for ASCENSION handoff;
- exact artifact bytes bound to that manifest;
- raw signed attestation envelope and verification material bodies;
- an ASCENSION Adapter v0.4 trust policy authorized for PROMETHEUS;
- v0.8 strict inclusion proof for the exact manifest;
- v0.7 compact consistency proof and signed witness observations;
- governance-pinned v0.4 backend contract paired with that policy.

Therefore PROMETHEUS v0.5 is a useful real sibling-owned **contract target**, but it has not crossed ASCENSION's authenticated Transfer gate.
