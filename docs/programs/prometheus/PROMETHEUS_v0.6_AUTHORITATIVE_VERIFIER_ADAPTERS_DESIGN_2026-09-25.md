# PROMETHEUS v0.6 — Authoritative Verifier Adapters Design

**Date:** 2026-09-25
**Status:** design checkpoint for review
**Baseline:** PROMETHEUS v0.5, commit `4746f11d493a1e6ed906da8e8d516e9b0963c276`
**Branch:** `work/prometheus-v0.6-authoritative-verifier-adapters`
**System role:** research-only verifier-boundary hardening; no production or promotion authority

## 1. Purpose

PROMETHEUS v0.5 can bind external plugin-execution attestations and verification receipts into research provenance, but the receipt itself is still supplied by the run input. That is a useful evidence contract, not an authoritative verifier boundary: a caller can construct a syntactically valid receipt that claims `signature`, `subject_digest`, `signer_identity`, and `trusted_root` all passed.

v0.6 closes that gap by separating **run-supplied verifier evidence** from **PROMETHEUS-issued normalized receipts**. A run may carry the structured result emitted by an external verifier, but it may not choose its own trusted verifier identity, trusted-root identifier, or verification-policy identifier. Those expectations come from an immutable `VerifierAuthorityRegistry` configured outside the run.

PROMETHEUS still does not own private keys, certificates, transparency-log roots, or cryptographic verification algorithms. The external verifier remains authoritative for cryptographic validation. PROMETHEUS is authoritative only for validating that a verifier result came through a configured adapter contract, matched the expected evidence and identity, and was normalized without unsafe bypasses or type confusion.

## 2. Goals

v0.6 must:

1. define immutable verifier-authority configuration outside per-run input;
2. normalize supported external verifier results into one typed observation contract;
3. bind a result to the exact external attestation and plugin-evidence digest;
4. require the expected artifact/subject digest and signer or verifier identity to have been checked;
5. preserve verifier implementation/version, policy identity, trust-domain/root identity, result digest, and source reference;
6. reject unknown verifier authorities, unsupported result formats, malformed claims, digest mismatch, identity mismatch, missing required checks, and unsafe bypass modes fail-closed;
7. issue `AttestationVerificationReceipt` objects from PROMETHEUS core only after authority-policy validation;
8. add an explicit strict policy that requires authoritative verifier evidence for every selected plugin while preserving v0.5 `OPTIONAL` and `REQUIRE_VERIFIED` compatibility semantics;
9. bind authoritative verifier result identities into provenance so replay can prove which verifier evidence supported the research candidate;
10. keep DAEDALUS as the only promotion authority and keep NEXUS market/replay authority unchanged.

## 3. Non-goals

v0.6 does **not**:

- implement DSSE, X.509, Rekor, RFC3161, Fulcio, Sigstore, SLSA, or other cryptographic verification primitives;
- fetch or rotate trust roots;
- manage signing keys, certificates, OIDC identities, secrets, or credentials;
- execute shell commands supplied by a run;
- permit a run to register or alter verifier authorities;
- infer trust from a `verifier_id` string alone;
- turn a verifier result into DAEDALUS acceptance or production authorization;
- claim a VSA/provenance statement is authentic merely because its JSON schema is valid;
- silently downgrade authoritative policy when verifier evidence is missing or malformed.

## 4. External verification model

The v0.6 boundary follows four externally established principles:

1. the verification applies to an immutable subject/artifact digest;
2. the verifier/predicate/result type is explicit;
3. expected identity and trust policy are checked in addition to signature validity;
4. a verification result is useful only when the consumer knows which verifier and policy it trusts.

This mirrors the verification model described by in-toto, SLSA, and Sigstore: envelope authentication is not enough by itself; consumers also bind the expected subject digest and expected identity/policy.

PROMETHEUS records these facts but does not independently prove the external verifier actually performed the cryptography. The configured verifier adapter and the host channel delivering its result are part of the trusted computing boundary for v0.6.

## 5. Threat model

v0.6 protects against these PROMETHEUS-side failures:

- a run fabricating its own trusted-root or policy identifier;
- a result for one attestation being replayed against another;
- a result for another plugin-evidence digest being substituted;
- a valid verifier result from an unapproved verifier being accepted;
- an approved verifier operating under an unexpected policy or trust domain being accepted;
- a result that skipped artifact-digest checking or identity checking being treated as authoritative;
- verifier-format or predicate-type confusion;
- raw-result mutation after normalization;
- an authoritative strict run proceeding with partial verifier coverage.

v0.6 does not protect against compromise of the configured external verifier, its trust roots, or the host boundary that supplies authenticated verifier output. Those remain explicitly outside PROMETHEUS.

## 6. Core contracts

### 6.1 `VerifierAuthority`

Immutable configuration established when the `ResearchLoop` is created, not supplied by a `LoopRunInput`.

Minimum fields:

- `authority_id` — `verifier-authority:` content identifier;
- `verifier_kind` — e.g. `SIGSTORE_RESULT_V0_1`, `SLSA_VSA_V1`, `GENERIC_HOST_ATTESTED`;
- `expected_verifier_id`;
- `trusted_root_id`;
- `verification_policy_id`;
- `allowed_predicate_types`;
- `allowed_signer_identities` or explicit wildcard policy;
- `require_subject_digest_check=True`;
- `require_identity_check=True`;
- `allow_unsafe_bypass=False`;
- optional `minimum_verified_levels` for SLSA/VSA-style results.

`authority_id` is content-addressed so policy mutation produces a new identity.

### 6.2 `VerifierAuthorityRegistry`

An immutable registry keyed by `authority_id` and also queryable by verifier kind/id. It is injected into `ResearchLoop` construction.

Rules:

- duplicate authority ids fail;
- conflicting verifier-kind/id routes fail;
- per-run input cannot add or replace entries;
- unknown authorities fail under authoritative policy;
- the registry contains expectation identifiers, not secret key material.

### 6.3 `ExternalVerifierResult`

A content-addressed representation of an externally produced verification result after transport but before PROMETHEUS authority evaluation.

Minimum fields:

- `authority_id` — selects a preconfigured authority, never defines one;
- `result_format`;
- `result_media_type`;
- `verifier_id`;
- `verifier_version`;
- `subject_sha256`;
- `predicate_type`;
- `signer_identity` or verifier identity as applicable;
- `trusted_root_id`;
- `verification_policy_id`;
- `checks` as normalized booleans;
- `verified_levels` where applicable;
- `unsafe_bypass_flags`;
- `raw_result_ref`;
- `raw_result_sha256`.

The raw result bytes are not stored in the core contract. The digest/reference allow replay and incident investigation without duplicating external verifier data stores.

### 6.4 `AuthoritativeVerifierObservation`

Produced only by a v0.6 verifier adapter after matching the external result to a configured `VerifierAuthority`.

It records:

- authority identity;
- external result identity;
- exact attestation identity;
- expected subject/plugin-evidence digest;
- normalized verifier/signer identity;
- policy/trust-root identities;
- required checks and their outcomes;
- verified levels;
- adapter type/version;
- failure reasons, if any.

Its `authoritative` property is true only if every configured expectation passes and no unsafe bypass is present.

### 6.5 `AttestationVerificationReceipt` v0.6 extension

The existing receipt remains the artifact consumed by provenance and orchestration, but v0.6 adds optional source fields:

- `verifier_authority_id`;
- `external_verifier_result_id`;
- `verifier_observation_id`.

Legacy v0.5 receipts remain reconstructable. A new property `authoritatively_verified` requires:

- existing `verified == True`;
- all three source identifiers present and correctly namespaced;
- the referenced observation to have passed authority evaluation before the receipt was issued.

Receipts used under the new strict policy are created by PROMETHEUS from the observation; callers cannot inject an authoritative receipt directly.

## 7. Supported adapter slices

v0.6 provides two concrete **normalizers**, not cryptographic implementations.

### 7.1 Sigstore verification-result adapter

Accepts a machine-readable Sigstore verification result already produced by an external Sigstore verifier and extracts:

- verification-result media type/version;
- statement subject digest;
- predicate type;
- verified certificate/key identity;
- verifier/trust-policy identifiers supplied by the trusted host adapter;
- timestamp/tlog evidence presence as claims when required by authority policy;
- raw result digest/reference.

It rejects authoritative normalization if the result lacks an expected artifact digest or expected identity. A merely valid bundle/signature result is not enough.

### 7.2 SLSA Verification Summary Attestation adapter

Accepts a host-verified SLSA VSA result and extracts:

- subject digest;
- VSA predicate type;
- verifier identity;
- resource URI where configured;
- PASS/FAIL result;
- verified levels;
- trust-policy identity;
- raw result digest/reference.

PROMETHEUS does not verify the VSA envelope signature. The host/external verifier must attest that envelope authentication succeeded; the configured authority policy determines whether that external result is acceptable.

## 8. No shell execution in v0.6

PROMETHEUS will not spawn `cosign`, `slsa-verifier`, `sigstore`, or arbitrary verifier commands in this slice.

Reasoning:

- command execution introduces path, binary-substitution, environment, timeout, output-bounding, and secret-leakage concerns;
- it would blur the boundary between research orchestration and verifier runtime ownership;
- real verifier services/CLIs can still feed their machine-readable output through the adapters;
- execution integration can be a later host/infrastructure slice with its own threat model.

This keeps v0.6 focused on the trust and normalization contract.

## 9. Policy modes

`PluginAttestationPolicy` becomes:

- `OPTIONAL` — v0.5 compatibility; missing attestation/receipt is recorded as a coverage gap but does not by itself degrade the run;
- `REQUIRE_VERIFIED` — v0.5 compatibility; every selected plugin requires an external attestation plus a verification receipt whose legacy required checks pass;
- `REQUIRE_AUTHORITATIVE` — new v0.6 mode; every selected plugin requires external attestation + configured verifier authority + external verifier result + authoritative observation + PROMETHEUS-issued receipt with `authoritatively_verified=True`.

No mode is silently upgraded or downgraded. The selected policy is bound into provenance.

## 10. Orchestration changes

`PluginExecutionInput` gains optional verifier-result evidence while preserving v0.5 fields for compatibility.

Under `REQUIRE_AUTHORITATIVE`:

1. caller supplies plugin execution evidence and external attestation;
2. caller supplies an `ExternalVerifierResult`, not an authoritative receipt;
3. `ResearchLoop` resolves `authority_id` only through its constructor-injected registry;
4. the format adapter normalizes and validates the result;
5. the authority policy checks expected verifier, root/policy id, predicate, subject digest, identity, required checks, verified levels, and unsafe bypass flags;
6. PROMETHEUS persists the external result and authoritative observation;
7. PROMETHEUS issues and persists the receipt;
8. any failure marks strict attestation failure and the run degrades; no provenance manifest or DAEDALUS review packet is emitted.

A caller-provided receipt under `REQUIRE_AUTHORITATIVE` is rejected to prevent receipt injection.

## 11. Provenance and lineage

`ResearchProvenanceManifest` gains:

- `verifier_authority_ids`;
- `external_verifier_result_ids`;
- `verifier_observation_ids`.

Rules:

- identifier namespaces are validated;
- result/observation/receipt cardinality cannot exceed selected-plugin cardinality;
- under `REQUIRE_AUTHORITATIVE`, authority/result/observation/attestation/receipt coverage must all equal selected-plugin cardinality;
- provenance lineage reconstruction includes these fields in the content ID automatically;
- old v0.5 manifests reconstruct with empty verifier-authority/result/observation tuples.

The existing complete-lineage requirement for `READY_FOR_DAEDALUS_REVIEW` remains unchanged and therefore automatically protects the new v0.6 evidence through the manifest hash.

## 12. Memory and replay

`ResearchMemory` remains append-only.

v0.6 adds reconstruction helpers only where deterministic validation requires them. It must reject:

- content-id mismatch;
- wrong artifact type;
- malformed authority/result/observation payloads;
- conflicting duplicate artifact ids.

A replay of a v0.6 run must be able to identify the exact authority policy and exact external verifier result digest used at the original decision instant. It does not need the external verifier's private trust material.

## 13. Fail-closed rules

`REQUIRE_AUTHORITATIVE` degrades and suppresses promotion when any selected plugin has:

- no external attestation;
- no external verifier result;
- unknown authority;
- result format not supported by the selected authority;
- subject/plugin-evidence digest mismatch;
- attestation/result mismatch;
- verifier identity mismatch;
- signer identity outside configured policy;
- trust-root or verification-policy id mismatch;
- missing required predicate type;
- required verification check false or absent;
- required SLSA verified level absent;
- any unsafe bypass flag;
- raw-result digest malformed;
- duplicate authority/result/observation attribution creating false coverage.

Malformed structural inputs raise `ValueError`; ordinary verifier-policy failure degrades research and records explicit failure reasons rather than crashing the entire loop.

## 14. Compatibility

v0.6 must preserve all v0.5 behavior unless `REQUIRE_AUTHORITATIVE` is selected.

Specifically:

- v0.5 `OPTIONAL` tests remain valid;
- v0.5 `REQUIRE_VERIFIED` tests remain valid;
- legacy receipts without v0.6 source ids remain `verified` but never `authoritatively_verified`;
- v0.5 provenance manifests reconstruct with empty v0.6 collections;
- existing sibling authority boundaries remain unchanged.

## 15. Testing strategy

TDD coverage must include at least:

### Contracts

- deterministic content IDs and canonical ordering;
- invalid namespaces and duplicate authority entries;
- legacy receipt remains verified but not authoritative;
- authoritative receipt requires correctly namespaced source ids;
- malformed raw result digest rejected.

### Registry

- unknown authority rejection;
- duplicate/conflicting route rejection;
- run cannot mutate authority policy.

### Sigstore normalizer

- accepts expected subject + identity + predicate under approved authority;
- rejects missing subject digest;
- rejects missing verified identity;
- rejects signer/verifier mismatch;
- rejects unsafe bypass flags;
- rejects trust-root/policy mismatch.

### SLSA VSA normalizer

- accepts PASS result with expected verifier/subject/resource/level;
- rejects failed/unevaluated result;
- rejects wrong verifier;
- rejects wrong resource where constrained;
- rejects insufficient verified level;
- rejects host claim that envelope authentication was skipped.

### Orchestration

- authoritative complete coverage can reach research-complete state;
- missing/failed authority evidence degrades;
- injected caller receipt is rejected under authoritative mode;
- `OPTIONAL` and `REQUIRE_VERIFIED` compatibility stays green;
- coverage reporting distinguishes missing attestation, missing verifier result, and verifier-policy failure.

### Provenance/promotion

- authoritative manifests bind authority/result/observation ids;
- tampering changes/rejects content id;
- complete lineage still required;
- degraded authoritative run emits no `READY_FOR_DAEDALUS_REVIEW` packet;
- production authorization remains impossible.

## 16. Release gates

v0.6 is checkpointable only when all of these pass from a clean committed tree:

1. full pytest suite;
2. compileall;
3. deterministic `OPTIONAL` demo;
4. deterministic `REQUIRE_VERIFIED` demo;
5. deterministic `REQUIRE_AUTHORITATIVE` demo using static verifier-result fixtures;
6. memory scan proving authority/result/observation/receipt/manifest linkage;
7. negative tests for unknown authority, unsafe bypass, subject mismatch, identity mismatch, and insufficient SLSA level;
8. production-authority source scan;
9. broker/credential scan;
10. runtime sibling-import scan;
11. tracked-bytecode scan;
12. `git diff --check`;
13. source archive extracted and full tests rerun from the packaged snapshot.

## 17. Frozen authority boundaries

- **External verifier / host adapter:** cryptographic verification, trust roots, keys, certificates, transparency logs, timestamps, verifier runtime integrity.
- **PROMETHEUS v0.6:** immutable verifier expectation registry, result normalization, evidence matching, policy evaluation, receipt issuance, research provenance.
- **NEXUS:** causal market/replay and source identity authority.
- **DAEDALUS:** protected validation and promotion authority.
- **Icarus:** production decision and execution authority.

No v0.6 code path may set or imply `production_authorized=True` or `DAEDALUS_ACCEPTED`.

## 18. Preferred implementation shape

Create a focused `prometheus_loop/verifiers/` package:

- `contracts.py` — authority, external result, normalized observation;
- `registry.py` — immutable authority registry;
- `sigstore.py` — Sigstore verification-result normalizer;
- `slsa.py` — SLSA VSA normalizer;
- `issue.py` — authority evaluation and receipt issuance.

Modify only the existing attestation, provenance, memory, orchestration, CLI/demo, and promotion-facing tests needed to bind the new evidence. Do not refactor unrelated research logic.

## 19. References used for the design

Primary external references reviewed during design:

- Sigstore verification guidance: `https://github.com/sigstore/sigstore-go/blob/main/docs/verification.md`
- Sigstore bundle format: `https://docs.sigstore.dev/about/bundle/`
- in-toto Attestation Framework: `https://github.com/in-toto/attestation`
- SLSA Build provenance verification: `https://slsa.dev/spec/v1.2-rc1/verifying-artifacts`
- SLSA Verification Summary Attestation model: `https://slsa.dev/spec/v1.2/verification_summary`

The implementation may copy concepts and interoperability constraints from these specifications, but it must not claim conformance to an external standard unless the implemented slice is actually verified against that standard.
