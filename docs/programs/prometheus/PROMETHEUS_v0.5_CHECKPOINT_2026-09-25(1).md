# PROMETHEUS v0.5 Verified Checkpoint — 2026-09-25

- Branch: `work/prometheus-v0.5-attestation-lineage`
- HEAD: `4746f11d493a1e6ed906da8e8d516e9b0963c276`
- Verified baseline: v0.4 `22c2aae066a4e74fcc331e60285ceeed10b86d1e`
- Full tests: **119 passed** on the clean post-commit release gate
- Compile: passed
- OPTIONAL deterministic demo: passed
- REQUIRE_VERIFIED deterministic attested fixture demo: passed
- Demo memory/manifest/lineage/promotion binding inspection: passed
- Production-authority negative scan: passed
- Broker/credential-term scan across production Python: passed
- Runtime sibling-import scan: passed
- Tracked-bytecode scan: passed
- `git diff --check`: passed
- Working tree at gate: clean

## v0.5 additions

1. Immutable `ExternalExecutionAttestation` bound to exact normalized `PluginExecutionEvidence` digest.
2. Immutable `AttestationVerificationReceipt` identifying external verifier, trust-root identity, policy identity, and mandatory check outcomes.
3. Explicit `OPTIONAL` and `REQUIRE_VERIFIED` plugin-attestation policies included in deterministic loop identity.
4. Fail-closed validation of half-supplied or cross-bound attestation/receipt evidence.
5. Strict-mode degradation and DAEDALUS handoff suppression for missing, partial, or unverified selected-plugin coverage.
6. `ResearchProvenanceManifest` now binds attestation/receipt identities plus policy.
7. Deterministic `ProvenanceLineageReport` verifies local ancestry from append-only memory.
8. Missing parents, wrong artifact types, content-ID substitution, duplicate parent IDs, and cycles fail lineage verification.
9. `ResearchPromotionPacket` requires both the exact current provenance manifest and its complete lineage report in evidence.
10. `production_authorized=True` remains structurally rejected; DAEDALUS acceptance is not represented by PROMETHEUS.

## Trust-boundary note

PROMETHEUS v0.5 does **not** implement DSSE parsing, X.509 validation, Sigstore/Rekor/Fulcio/TSA verification, key management, or trust-root rotation. A verification receipt records what an identified external verifier reported. PROMETHEUS validates deterministic binding of that receipt to the exact plugin execution evidence and research lineage; it does not claim to have repeated the cryptography itself.

## Review note

The final whole-branch review was a self-review because no independent subagent-reviewer tool was available in this execution context. No Critical or Important findings remained after review; one unused test import was removed before the final release commit. The full release suite and gates were rerun after commit.
