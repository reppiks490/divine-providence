# PROMETHEUS v0.5 — External Attestation & Provenance Lineage

## Added

- `PluginAttestationPolicy` with `OPTIONAL` and `REQUIRE_VERIFIED` modes.
- `ExternalExecutionAttestation` bound to exact normalized plugin-evidence digest.
- `AttestationVerificationReceipt` with explicit verifier, trusted-root, policy, and mandatory verification checks.
- strict selected-plugin attestation coverage enforcement and explicit optional-mode coverage gaps.
- attestation/receipt identities in `ResearchProvenanceManifest`.
- `ProvenanceLineageReport` and read-only ancestry reconstruction from append-only `ResearchMemory`.
- detection of missing/wrong-type/tampered/duplicate-parent/cyclic provenance ancestry.
- lineage-report binding in `ResearchPromotionPacket` and packet evidence.
- deterministic strict-attested CLI fixture alongside the backward-compatible optional demo.

## Trust boundary

PROMETHEUS v0.5 does not implement or claim DSSE, X.509, Sigstore, Rekor, Fulcio, TSA, or other cryptographic verification. A receipt records what an identified external verifier reported under an identified trust policy. PROMETHEUS verifies the deterministic relationship among that receipt, the attestation reference, the exact plugin execution evidence, the current provenance manifest, and its local ancestry.

## Unchanged authority

DAEDALUS remains the validation/promotion authority, NEXUS remains the causal market-data/contract authority, and production authorization/execution remains outside PROMETHEUS.
