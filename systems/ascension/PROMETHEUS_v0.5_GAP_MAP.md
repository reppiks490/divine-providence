# PROMETHEUS v0.5 -> ASCENSION Adapter v0.4 Gap Map

Evidence class: **RUNTIME-STRUCTURAL / EXTERNALLY-VERIFIED-RECEIPT DESCRIPTOR**, not authenticated Transfer.

PROMETHEUS v0.5 records the fields required by the ASCENSION conformance profile:
`plugin_evidence_id`, `subject_sha256`, `predicate_type`, `envelope_ref`,
`envelope_sha256`, `verification_material_sha256`, `signer_identity`,
`attestation_format`; and verification receipt fields `attestation_id`,
`verifier_id`, `trusted_root_id`, `verification_policy_id`, `checks`,
`external_verification_ref`. It requires the receipt checks `signature`,
`subject_digest`, `signer_identity`, and `trusted_root`.

PROMETHEUS still does **not** implement or claim DSSE parsing,
X.509/Sigstore/Rekor verification, key management, trust-root rotation, or
ASCENSION authority. Its receipt records what an identified external verifier
reported under an identified external policy.

## Runtime handoff gaps now closed

Merged work on 2026-10-01 closes the earlier structural transport gaps:

- exact runtime `ResearchProvenanceManifest` payload is reconstructed from
  append-only `ResearchMemory`;
- exact canonical manifest bytes are emitted and bound to SHA-256;
- the exact stored `ExternalExecutionAttestation` descriptor is carried;
- the exact stored `AttestationVerificationReceipt` is carried;
- content-addressed IDs and attestation/receipt bindings are revalidated before
  export;
- strict handoff requires `PluginAttestationPolicy.REQUIRE_VERIFIED`;
- `prometheus-loop export-ascension-handoff` can export the same payload from
  an existing persisted research-memory file using exact provenance/evidence
  identifiers;
- the hub integration passes the runtime export untouched through ASCENSION
  Sibling Manifest Conformance Kit v0.1 and verifies
  `STRUCTURALLY_CONFORMANT`.

Verified implementation history:

- PR #8 merged runtime serializer at
  `c7146e8c3ed5b6865e80bbe1d37d5311f4c72402`;
- PR #9 merged the actual PROMETHEUS runtime-path -> ASCENSION driver at
  `0671943648278daeee3d4849a8ce6c6a75804eef`;
- PR #10 merged the operational handoff CLI at
  `e1f5f2c6bb93c47ff9c41f901273e7ec311e3785`;
- exact-head workflow runs 36875158294, 36878240351, and 36886560823 completed
  successfully, including PROMETHEUS tests, root hub tests, Linux/Windows
  causal subsystem gates, intelligence-fabric checks, and full twelve-system
  validation.

## Still missing for authenticated ASCENSION Transfer

The following material is **not** supplied or invented by PROMETHEUS and
remains required before Adapter v0.4 can move beyond structural readiness:

- raw signed attestation envelope bytes or an equivalent transferable
  cryptographic object, not only its reference and SHA-256 descriptor;
- raw verification-material bytes needed by the authorized verifier, not only
  their digest/reference;
- an ASCENSION-authorized trust policy for PROMETHEUS identities and roots;
- a valid prior Collision Detector report for the exact runtime artifact;
- v0.8 strict inclusion evidence for the exact artifact/manifest;
- v0.7 consistency-transition evidence plus independently valid witness
  observations;
- the exact governance-pinned Adapter v0.4 backend contract paired with that
  trust/transparency policy;
- successful cryptographic verification under those externally governed
  materials.

The deterministic hub integration uses internal contract fixtures for external
attestation records. Those fixtures verify interface behavior and fail-closed
binding; they are not evidence of real-world cryptographic authentication.

## Current gate state

- Structural conformance: **PASS**
- Exact runtime bytes: **PASS**
- Runtime provenance binding: **PASS**
- External-verifier receipt descriptor binding: **PASS**
- Adapter v0.4 readiness: **BLOCKED**
- Cryptographic authentication: **NOT ESTABLISHED**
- Transfer: **BLOCKED**
- Production/execution authority: **FALSE**

PROMETHEUS has therefore crossed ASCENSION's real runtime **structural**
handoff boundary, but it has not crossed the authenticated Transfer gate.
