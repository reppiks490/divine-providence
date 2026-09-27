# PROMETHEUS v0.5 External Attestation & Provenance Lineage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind optional/required externally verified plugin execution attestations into PROMETHEUS provenance and require complete deterministic provenance ancestry before DAEDALUS review readiness.

**Architecture:** Add a focused attestation contract module, extend the v0.4 provenance manifest with attestation policy/evidence identities, add a read-only lineage verifier over append-only `ResearchMemory`, and integrate both gates into orchestration/promotion without adding cryptography or sibling authority. External verification remains an asserted, content-addressed receipt from an identified verifier; PROMETHEUS validates binding and policy only.

**Tech Stack:** Python 3.11+, standard library production code, dataclasses/enums, pytest, append-only JSONL research memory.

**Spec:** `docs/superpowers/specs/2026-09-25-prometheus-v0.5-external-attestation-lineage-design.md`

## Global Constraints

- PROMETHEUS remains research-only; `production_authorized=True` must remain structurally rejected.
- DAEDALUS remains authoritative for protected validation/promotion; NEXUS remains authoritative for causal market identity and sibling contract identity.
- No DSSE/Sigstore/X.509/Rekor/TSA cryptographic verification is implemented in PROMETHEUS v0.5.
- No raw private keys, tokens, cookies, secrets, raw plugin bodies, or raw attestation bundles are persisted.
- No runtime import/write dependency on sibling repositories is added.
- Default attestation policy is `OPTIONAL`; `REQUIRE_VERIFIED` must fail/degrade closed when selected plugin coverage is incomplete or unverified.
- Provenance ancestry is reconstructed from persisted manifests and must reject missing, wrong-type, content-ID-mismatched, duplicate-parent, or cyclic lineage.

## Review Focus

1. A syntactically valid receipt whose `attestation_id` points at another plugin execution must be rejected rather than counted as coverage.
2. OPTIONAL mode with a supplied invalid attestation/receipt pair must fail closed; OPTIONAL relaxes absence, not correctness.
3. A parent record whose stored payload was changed while its outer memory checksum was recomputed must still fail lineage because the manifest content ID no longer matches its reference.
4. A multi-parent DAG must verify each ancestor exactly once, report deterministic roots/edges, and not mistake convergence for a cycle.
5. A strict run with one selected plugin verified and another missing must degrade and emit no provenance/promotion packet.

---

### Task 1: External attestation and verification receipt contracts

**Files:**
- Create: `src/prometheus_loop/attestation.py`
- Create: `tests/test_attestation.py`

**Interfaces:**
- Produces: `PluginAttestationPolicy`, `ExternalExecutionAttestation`, `AttestationVerificationReceipt`, `validate_external_attestation_binding(plugin_evidence_id, attestation, receipt) -> None`.
- Consumed by: Tasks 2 and 4.

- [ ] **Step 1: Write failing contract tests** covering SHA-256 shape, subject digest equality, deterministic IDs, canonical duplicate-free receipt checks, mandatory-check derivation, mismatched receipt/attestation binding, and OPTIONAL-invalid-pair rejection semantics.
- [ ] **Step 2: Run `pytest -q tests/test_attestation.py`** and confirm failure because the new API does not exist.
- [ ] **Step 3: Implement the minimal immutable contracts and binding validator** with prefixes `external-attestation:` and `attestation-verification:` and exact required check names `signature`, `subject_digest`, `signer_identity`, `trusted_root`.
- [ ] **Step 4: Run `pytest -q tests/test_attestation.py`** and require all Task 1 tests to pass.
- [ ] **Step 5: Commit** as `feat: add external execution attestation contracts`.

### Task 2: Extend provenance manifest and deterministic lineage verifier

**Files:**
- Modify: `src/prometheus_loop/contracts.py`
- Modify: `src/prometheus_loop/provenance.py`
- Modify: `src/prometheus_loop/memory/store.py`
- Create: `src/prometheus_loop/lineage.py`
- Modify: `tests/test_provenance.py`
- Create: `tests/test_lineage.py`

**Interfaces:**
- Consumes: Task 1 `PluginAttestationPolicy` and attestation/receipt artifact IDs.
- Produces: extended `ResearchProvenanceManifest`, `ProvenanceLineageReport`, `ResearchMemory.reconstruct_provenance_manifest(id)`, `verify_provenance_lineage(memory, tip_manifest_id) -> ProvenanceLineageReport`.
- Consumed by: Tasks 3 and 4.

- [ ] **Step 1: Write failing provenance tests** for canonical attestation IDs, policy-bound manifest identity, strict cardinality, optional mapping bounds, and namespace/type checks.
- [ ] **Step 2: Run focused provenance tests** and confirm RED.
- [ ] **Step 3: Implement manifest extension and builder parameters**: `external_attestation_ids`, `attestation_verification_ids`, `plugin_attestation_policy`.
- [ ] **Step 4: Run focused provenance tests** and require GREEN.
- [ ] **Step 5: Write failing lineage tests** for root, multi-generation, convergent multi-parent DAG, missing parent, wrong artifact type, reconstructed content-ID mismatch, duplicate parent, cycle detection, deterministic edge/root/verified tuples.
- [ ] **Step 6: Run `pytest -q tests/test_lineage.py`** and confirm RED.
- [ ] **Step 7: Implement read-only reconstruction and DAG verification** without mutating historical memory.
- [ ] **Step 8: Run `pytest -q tests/test_lineage.py tests/test_provenance.py tests/test_memory.py`** and require GREEN.
- [ ] **Step 9: Commit** as `feat: verify provenance ancestry`.

### Task 3: Host normalization and attestation policy enforcement

**Files:**
- Modify: `src/prometheus_loop/orchestration/loop.py`
- Modify: `tests/test_loop.py`
- Modify: `tests/test_nexus_adapter.py`

**Interfaces:**
- Consumes: Task 1 attestation contracts/policy and Task 2 extended manifest/lineage APIs.
- Produces: `HostPluginResult.external_attestation`, `HostPluginResult.attestation_verification`, `RunInput.plugin_attestation_policy`, `NexusRunInput.plugin_attestation_policy`, result IDs/coverage state persisted before promotion.
- Consumed by: Task 4 promotion path.

- [ ] **Step 1: Write failing loop tests** for OPTIONAL absence success with explicit zero coverage, OPTIONAL supplied-invalid pair failure, strict missing-pair degradation, strict unverified-receipt degradation, strict partial-coverage degradation, strict complete verified fixture success, persisted attestation/receipt records, and policy influence on loop ID.
- [ ] **Step 2: Run focused loop/NEXUS tests** and confirm RED.
- [ ] **Step 3: Implement normalization after `PluginExecutionEvidence` creation**, one-to-one evidence→attestation→receipt validation, strict degradation, persistence, manifest population, and policy propagation through `run_nexus`.
- [ ] **Step 4: Run `pytest -q tests/test_loop.py tests/test_nexus_adapter.py tests/test_attestation.py`** and require GREEN.
- [ ] **Step 5: Commit** as `feat: enforce plugin attestation policy`.

### Task 4: Lineage-bound DAEDALUS review packet

**Files:**
- Modify: `src/prometheus_loop/contracts.py`
- Modify: `src/prometheus_loop/policy/promotion.py`
- Modify: `src/prometheus_loop/orchestration/loop.py`
- Modify: `tests/test_promotion_packet.py`
- Modify: `tests/test_loop.py`

**Interfaces:**
- Consumes: Task 2 `ProvenanceLineageReport`; Task 3 current manifest/attestation state.
- Produces: `ResearchPromotionPacket.provenance_lineage_report_id`; promotion builder requires complete report whose tip equals current manifest and includes manifest/report IDs in evidence.

- [ ] **Step 1: Write failing promotion tests** for lineage report requirement, tip mismatch, incomplete lineage, missing evidence binding, strict-attestation mismatch, and preserved production-authority rejection.
- [ ] **Step 2: Run focused promotion tests** and confirm RED.
- [ ] **Step 3: Implement lineage-bound promotion contract and builder checks**; eligible runs persist lineage report before packet construction.
- [ ] **Step 4: Run `pytest -q tests/test_promotion_packet.py tests/test_loop.py tests/test_lineage.py`** and require GREEN.
- [ ] **Step 5: Commit** as `feat: bind promotion to verified provenance lineage`.

### Task 5: Deterministic demos, documentation, and release gates

**Files:**
- Modify: `src/prometheus_loop/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `README.md`
- Modify: `docs/VALIDATION_STATUS.md`
- Create: `docs/changes/2026-09-25-prometheus-v0.5-attestation-lineage.md`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: deterministic OPTIONAL demo and strict verified-fixture demo evidence; updated v0.5 validation documentation.

- [ ] **Step 1: Write failing CLI tests** proving OPTIONAL demo remains valid and a strict verified-fixture run exposes attestation/lineage IDs without claiming cryptographic verification.
- [ ] **Step 2: Run CLI tests** and confirm RED.
- [ ] **Step 3: Implement minimal CLI/demo additions and documentation** with explicit trust-boundary language.
- [ ] **Step 4: Run full test suite and release gates**: `python -m compileall -q src tests`; `pytest -q`; both deterministic demos with memory inspection; production-authority literal scan; broker/credential scan; sibling runtime-import scan; tracked-bytecode scan; `git diff --check`.
- [ ] **Step 5: Commit** as `docs: finalize prometheus v0.5 attestation lineage` only after every gate is green.
