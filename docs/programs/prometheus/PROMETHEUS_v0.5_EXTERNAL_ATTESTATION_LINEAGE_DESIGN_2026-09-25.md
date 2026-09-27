# PROMETHEUS v0.5 — External Attestation & Provenance Lineage Design

**Date:** 2026-09-25  
**Status:** design prepared for user review  
**Scope:** research-only external host/plugin attestation binding and deterministic cross-run provenance-chain verification

## 1. Purpose

PROMETHEUS v0.5 strengthens the v0.4 provenance boundary without turning PROMETHEUS into a certificate authority, signature service, package verifier, broker, or production promotion engine.

The release has two tightly related goals:

1. let a plugin execution evidence artifact be bound to an externally verifiable attestation envelope and an explicit verification receipt produced by a verifier outside PROMETHEUS; and
2. let a `READY_FOR_DAEDALUS_REVIEW` packet prove that its current provenance manifest has a complete, untampered local ancestry through every declared parent manifest.

PROMETHEUS remains responsible only for binding, deterministic structural verification, lineage reconstruction, evidence persistence, and fail-closed policy enforcement. Cryptographic signature verification remains external unless a future authoritative verifier adapter is deliberately added.

## 2. Design basis

The design follows the high-signal patterns from the in-toto Attestation Framework, DSSE, SLSA Provenance, and Sigstore verification model:

- an attestation is bound to immutable subject identity by digest;
- the predicate/type is explicit and authenticated as part of the statement/envelope model;
- verification must be evaluated against an expected artifact and expected signer/trust policy rather than treating a syntactically valid bundle as sufficient;
- signer/verifier/trusted-root identity must remain explicit;
- verification material should be referenceable and digest-bound so another verifier can reproduce the check;
- PROMETHEUS must not claim a cryptographic property it did not itself verify.

These are design patterns, not a claim that v0.5 implements the in-toto, DSSE, SLSA, or Sigstore protocols themselves.

## 3. Alternatives considered

### A. Native cryptographic verification inside PROMETHEUS

PROMETHEUS would parse DSSE/Sigstore bundles, manage roots, verify signatures, transparency proofs, and identity constraints itself.

**Rejected for v0.5.** This would duplicate a security-sensitive trust stack, add non-standard-library dependencies, and blur the authority boundary between PROMETHEUS research orchestration and external attestation infrastructure.

### B. External verification receipt + deterministic PROMETHEUS binding

An external verifier performs cryptographic/policy verification. PROMETHEUS stores a content-addressed reference to the external envelope plus a content-addressed verification receipt, validates that both bind to the exact `PluginExecutionEvidence` subject, and can require those receipts under an explicit attestation policy.

**Chosen.** It improves verifiability while keeping trust roots and cryptographic authority outside PROMETHEUS.

### C. Opaque attestation URLs only

PROMETHEUS stores only a URL or result reference.

**Rejected.** A locator alone does not bind the referenced material to a plugin execution, signer expectation, verifier policy, or immutable digest.

## 4. Hard authority boundaries

- PROMETHEUS remains research-only.
- `production_authorized` remains structurally false.
- DAEDALUS alone owns protected validation and later promotion/acceptance.
- NEXUS remains authoritative for causal market identity and sibling contract identity.
- PROMETHEUS does not sign host/plugin executions.
- PROMETHEUS does not manage public keys, certificate roots, Rekor/transparency roots, or revocation state.
- A stored verification receipt is evidence that an identified external verifier reported a result under an identified policy/trust root; it is not proof that PROMETHEUS independently re-ran the cryptography.
- No raw private keys, bearer tokens, cookies, credentials, certificates containing secrets, or plugin response bodies are stored.
- No runtime import or write dependency on sibling source repositories is added.

## 5. External attestation contract

Add immutable `ExternalExecutionAttestation` with:

- `plugin_evidence_id`
- `subject_sha256`
- `predicate_type`
- `envelope_ref`
- `envelope_sha256`
- `verification_material_sha256`
- `signer_identity`
- `attestation_format`

Rules:

- `plugin_evidence_id` must use the `plugin-evidence:` namespace.
- `subject_sha256` must be exactly the digest suffix of `plugin_evidence_id`.
- every SHA-256 field must be exactly 64 lowercase hexadecimal characters.
- `predicate_type`, `envelope_ref`, `signer_identity`, and `attestation_format` must be non-empty.
- `predicate_type` is an opaque type identity; v0.5 does not interpret predicate semantics beyond exact matching.
- the attestation exposes deterministic `artifact_id` prefix `external-attestation:`.
- the contract stores references and digests, not raw envelope or verification-material bodies.

## 6. External verification receipt contract

Add immutable `AttestationVerificationReceipt` with:

- `attestation_id`
- `verifier_id`
- `trusted_root_id`
- `verification_policy_id`
- `checks`
- `external_verification_ref`

`checks` is a duplicate-free canonical tuple of `(name, passed)` pairs.

Required check names are:

- `signature`
- `subject_digest`
- `signer_identity`
- `trusted_root`

A receipt exposes `verified` as a derived property that is true only when all four required checks exist and pass. Additional checks such as transparency inclusion or trusted timestamp verification may be recorded but are not mandatory unless the named `verification_policy_id` requires them outside PROMETHEUS.

Rules:

- `attestation_id` must use `external-attestation:`.
- verifier/root/policy identities and external verification reference must be non-empty.
- duplicate check names fail closed.
- missing mandatory checks make `verified` false.
- any mandatory false check makes `verified` false.
- the receipt exposes deterministic `artifact_id` prefix `attestation-verification:`.
- PROMETHEUS never silently upgrades an unverified receipt to verified.

## 7. Attestation policy

Add `PluginAttestationPolicy` with two explicit modes:

- `OPTIONAL`: external attestation is recorded and validated when supplied, but absence does not block PROMETHEUS research completion or DAEDALUS review readiness.
- `REQUIRE_VERIFIED`: every selected plugin execution must have exactly one `ExternalExecutionAttestation` and exactly one verified `AttestationVerificationReceipt` bound to it; otherwise the run is degraded and cannot emit `READY_FOR_DAEDALUS_REVIEW`.

The policy mode is part of the deterministic loop-run identity.

Default for v0.5 is `OPTIONAL` for backward compatibility. This default is not presented as equivalent to external verification. A strict caller must opt into `REQUIRE_VERIFIED` until the host integration can provide real external receipts by default.

## 8. Host input and normalization

Extend `HostPluginResult` with optional:

- `external_attestation`
- `attestation_verification`

Validation occurs only after `PluginExecutionEvidence` has been normalized, because the exact evidence artifact ID is the attestation subject.

For each selected plugin:

1. normalize `PluginExecutionEvidence` exactly as in v0.4;
2. if no attestation/receipt is supplied:
   - accept under `OPTIONAL`;
   - mark the attestation coverage gap explicitly;
   - degrade under `REQUIRE_VERIFIED`;
3. if only one of attestation/receipt is supplied, fail closed;
4. require the attestation subject to equal the plugin evidence artifact ID/digest;
5. require the receipt to reference that attestation artifact ID;
6. require a verified receipt under `REQUIRE_VERIFIED`;
7. persist supplied attestation artifacts and receipts before any promotion packet is built.

One selected plugin may not claim multiple attestations or receipts in v0.5. Multi-signature/multi-attestation policy is deliberately deferred.

## 9. Provenance manifest extension

Extend `ResearchProvenanceManifest` with:

- `external_attestation_ids`
- `attestation_verification_ids`
- `plugin_attestation_policy`

The attestation and receipt collections are canonical and duplicate-free.

When policy is `REQUIRE_VERIFIED`, their cardinality must equal selected plugin descriptor/evidence/contribution cardinality. Under `OPTIONAL`, cardinality may be zero through the selected-plugin count, but every stored receipt must correspond to exactly one stored attestation and each stored attestation to one selected plugin execution.

The v0.5 manifest remains content-addressed with `research-provenance:` and therefore changes identity when attestation evidence or policy changes.

## 10. Cross-run provenance lineage verification

Add immutable `ProvenanceLineageReport` with:

- `tip_manifest_id`
- `verified_manifest_ids`
- `root_manifest_ids`
- `edge_ids`
- `complete`
- `failure_reasons`

The verifier walks the `parent_manifest_ids` DAG from the tip using `ResearchMemory`.

For every visited manifest it must:

1. confirm a record exists;
2. confirm the record type is `ResearchProvenanceManifest`;
3. reconstruct the manifest from its stored payload;
4. recompute its `artifact_id` and require it to equal the referenced ID;
5. reject duplicate parent IDs;
6. detect cycles;
7. continue until every root is reached.

`complete` is true only when every declared ancestor is present, type-correct, content-ID correct, and acyclic.

`edge_ids` are deterministic `parent_id -> child_id` strings sorted lexically. `verified_manifest_ids`, `root_manifest_ids`, and `failure_reasons` are canonical tuples.

The report exposes deterministic `artifact_id` prefix `provenance-lineage:`.

## 11. Promotion gate

Every promotion-eligible v0.5 run builds and persists a lineage report before the DAEDALUS review packet.

`ResearchPromotionPacket` gains:

- `provenance_lineage_report_id`

The packet requires both the current provenance manifest ID and lineage report ID in `evidence_ids`.

The promotion builder fails closed when:

- the current manifest does not match the live run inputs, as in v0.4;
- lineage verification is incomplete;
- the lineage report tip does not equal the current manifest;
- strict attestation policy is active and attestation coverage is incomplete/unverified;
- a receipt/attestation ID supplied to the manifest does not match the current normalized plugin evidence; or
- `production_authorized=True` is attempted.

A rejected hypothesis, reused negative, failed/degraded run, or non-engineering-pass candidate emits no packet.

## 12. Memory semantics

`ResearchMemory` remains append-only.

v0.5 adds reconstruction helpers only for the new provenance/attestation contracts needed by lineage validation. It does not become a general object-relational store and does not rewrite historical records.

The lineage verifier treats missing historical parent records as incomplete evidence, not as permission to infer a root.

## 13. Failure model

Fail closed on:

1. malformed SHA-256 digests;
2. attestation subject mismatch;
3. receipt-to-attestation mismatch;
4. duplicate or missing mandatory receipt checks;
5. strict-policy missing attestation or receipt;
6. strict-policy unverified receipt;
7. manifest attestation cardinality or mapping drift;
8. missing parent manifest;
9. parent record with wrong artifact type;
10. parent content-ID mismatch;
11. provenance cycle;
12. lineage report tip mismatch;
13. incomplete lineage presented to promotion;
14. any attempt to set production authorization true.

## 14. Non-goals for v0.5

- implementing DSSE parsing;
- validating X.509 chains;
- calling Sigstore/Rekor/Fulcio/TSA services;
- managing trusted-root rotation or revocation;
- signing PROMETHEUS artifacts;
- storing raw attestation bundles;
- automatic network retrieval of `envelope_ref`;
- multi-signature threshold policy;
- DAEDALUS acceptance;
- production authorization or execution.

These remain candidate future adapters behind explicit trust boundaries.

## 15. Verification plan

TDD must cover:

- SHA-256 shape and subject digest binding;
- deterministic/canonical external attestation IDs;
- receipt mandatory checks and `verified` derivation;
- one-to-one plugin evidence → attestation → receipt binding;
- OPTIONAL versus REQUIRE_VERIFIED behavior;
- strict-policy degradation and promotion suppression;
- provenance-manifest attestation identity binding;
- lineage root verification;
- multi-generation lineage verification;
- missing parent rejection;
- wrong-type parent rejection;
- stored manifest content-ID mismatch rejection;
- cycle detection;
- lineage report determinism;
- promotion packet lineage binding;
- existing v0.4 stale-manifest checks;
- existing production-authority negative test.

Final gates remain:

- `python -m compileall -q src tests`
- full `pytest`
- deterministic CLI/demo including an OPTIONAL run and a strict verified-fixture run
- production-authority literal scan
- broker/credential scan
- runtime sibling-import scan
- tracked-bytecode scan
- `git diff --check`

## 16. Acceptance criteria

v0.5 is successful when:

1. externally produced host/plugin attestations can be represented without storing raw sensitive bodies;
2. a verification receipt is explicitly tied to the attestation, verifier, trust root, policy, and exact plugin-evidence subject;
3. strict mode prevents a DAEDALUS review packet when any selected plugin lacks verified external attestation evidence;
4. optional mode remains backward-compatible while making missing attestation coverage explicit;
5. every review-ready current manifest has a complete deterministic local ancestry report;
6. parent manifests cannot be missing, substituted, type-confused, or content-ID altered without detection;
7. no cryptographic verification or external trust claim is fabricated by PROMETHEUS;
8. DAEDALUS, NEXUS, sibling, and production authority boundaries remain unchanged; and
9. all verification gates pass from a clean checkout.
