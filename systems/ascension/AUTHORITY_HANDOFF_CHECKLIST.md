# Authority Handoff Checklist — ASCENSION Sibling Manifest Conformance v0.1

This checklist is for a sibling system owner or explicitly authorized verifier. It is not permission for ASCENSION to create evidence on the sibling's behalf.

## 1. Collision-facing manifest
Provide the exact runtime manifest with `system_id`, `owned_domains`, `mutation_rights`, `interfaces`, `requires`, `forbids`, `shared_state`, and `coordination_contracts`. Preserve additional sibling-owned fields; do not project them away.

## 2. Runtime artifact binding
Provide the exact artifact bytes (or a transfer mechanism that yields those bytes), a stable reference, and their SHA-256. The bytes must reproduce the declared digest.

## 3. Sibling attestation descriptor
Provide the sibling-owned subject binding, predicate/type, signer identity, envelope reference and SHA-256, verification-material SHA-256, attestation format, and immutable attestation ID.

## 4. External verification receipt
Name the verifier, trusted-root identity, policy identity, receipt reference, and result for all mandatory checks: `signature`, `subject_digest`, `signer_identity`, `trusted_root`. A stored receipt is evidence from the named verifier; ASCENSION does not silently upgrade it.

## 5. Adapter v0.4 evidence package
Provide the full bound prior Collision report, trust policy, actual signed attestation set, v0.8 strict inclusion evidence, v0.7 compact consistency + witness evidence, and the governance-pinned Adapter v0.4 backend contract.

## 6. Nonclaims
Structural conformance does not mean authentication, semantic truth, witness independence, ecosystem adoption, or successful Transfer. Those require the downstream verification chain and the remaining ASCENSION promotion gates.
