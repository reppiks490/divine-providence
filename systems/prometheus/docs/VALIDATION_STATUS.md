# Validation Status — PROMETHEUS v0.5 (unified)

Verified on branch `work/prometheus-v0.5-unified` on 2026-09-26 after merging the two independently verified v0.5 lineages. How the conflicts were resolved is recorded in `docs/changes/2026-09-26-prometheus-v0.5-unified-merge.md`.

## Baselines and merged commits

Common ancestor: v0.3 `a00db63da838c91b0b100d48a717a36cbaedcde4`.

**Lineage A — v0.4 lineage + diagnosis → v0.5 experiment routing** (tip `444d978`)

- verified v0.4 head: `2659350553f23f2314b27a80bb04604d5747418e`
- bounded v0.5 implementation: `e30223b` — stale-aware deterministic experiment routing
- review hardening: `d4f2aa0` — preserve universal replay guardrails across route-specific probes
- lineage-reuse hardening: `aba745b` — bind experiment identity to route/preflight lineage

**Lineage B — v0.4 provenance attestation → v0.5 external attestation + provenance lineage** (tip `4746f11`)

- verified v0.4 baseline: `22c2aae066a4e74fcc331e60285ceeed10b86d1e`
- v0.5 design: `a0b14cf`; plan: `3328c68`
- `e0031cf` — external execution attestation contracts
- `9940ca1` — provenance ancestry verification
- `c27497a` — plugin attestation policy enforcement
- `1e54421` — lineage-bound DAEDALUS review packet

The merge commit is not embedded by full hash here because a commit cannot contain its own final hash without changing that hash.

## Fresh gate results (unified tree)

Run from the repository root with `PYTHONPATH=src`, using the local analysis venv (CPython 3.10.11):

- `python -m compileall -q src` -> **passed**
- `python -m compileall -q src tests` -> **passed**
- `python -m pytest -q -p no:cacheprovider` -> **156 passed**
  - 150 = the exact union of both branch tips' test node IDs (A: 77, B: 119, shared: 46). Every ID from both tips is present and passing, and none was renamed.
  - 6 = the new merge-specific tests in `tests/test_unified_promotion_gate.py`.
- Branch tips re-run in this session from detached worktrees: A **77 passed**, B **119 passed**.
- `python -m prometheus_loop.cli demo` -> **passed** with:
  - status `RESEARCH_COMPLETE`;
  - route `RUN_REPLAY` / `MEDIUM` / `AMBIGUITY_REDUCTION_PROBE`;
  - result `PROMETHEUS_ENGINEERING_PASS`;
  - policy `OPTIONAL`, coverage gaps `deep-research` and `exa`;
  - provenance manifest, lineage report and promotion packet present;
  - `production_authorized=false`.
- `python -m prometheus_loop.cli demo-strict-attested` -> **passed** with:
  - status `RESEARCH_COMPLETE`;
  - the same route;
  - policy `REQUIRE_VERIFIED`, 2 attestations, 2 receipts, no coverage gaps;
  - provenance manifest, lineage report and promotion packet present;
  - `cryptographic_verification_performed_by_prometheus=false` and `production_authorized=false`.
- Both demos are byte-identical across two fresh-memory runs. Inspecting each demo's memory shows the packet's `lineage_manifest_id` resolves to a `ResearchLineageManifest` with a clean final `StaleEvidenceReport`, and its provenance IDs resolve to a `ResearchProvenanceManifest` and a complete `ProvenanceLineageReport`.
- production-authority literal scan across `src` -> **passed**
- AST-based sibling-repository runtime-import scan -> **passed**
- broker/order/credential token scan across `src` -> **passed**
- tracked Python bytecode scan -> **passed**
- `git diff --cached --check` of the merge result:
  - against the lineage B parent -> **passed**;
  - against the lineage A parent -> flags only 3 lines. These are pre-existing Markdown hard line breaks (two trailing spaces) in B's `docs/superpowers/specs/2026-09-25-prometheus-v0.4-provenance-attestation-design.md` (lines 3–4) and `...v0.5-external-attestation-lineage-design.md` (line 3), inherited verbatim from B and deliberately not rewritten. No merge-authored line has whitespace errors.

`pyproject.toml` declares `requires-python >=3.11`, but the available interpreter was 3.10.11. The suite and demos pass on it. A 3.11+ run was not performed in this merge cycle.

## Unified promotion gate

A `READY_FOR_DAEDALUS_REVIEW` packet now requires **both** bindings:

- **stale-aware research lineage (A):** a concrete `ResearchLineageManifest` and a clean `StaleEvidenceReport` bound to that exact manifest. Stale lineage suppresses the packet.
- **provenance attestation lineage (B):** a `ResearchProvenanceManifest` that exactly matches the live run, including attestation, receipt and policy bindings, plus a complete `ProvenanceLineageReport` whose tip is that manifest.

Neither binding substitutes for the other. The packet carries `lineage_manifest_id`, `provenance_manifest_id` and `provenance_lineage_report_id`. Its evidence includes the lineage manifest, the staleness report, the provenance manifest, the lineage report, and any attestations and receipts. `production_authorized=True` remains structurally rejected. The attestation policy is part of the deterministic loop identity.

## Experiment-routing evidence (lineage A)

- actionable shared-evidence disagreement outranks intentional role specialization;
- route selection is deterministic under disagreement/diagnosis input reordering;
- routing uses qualitative priority bands rather than a scalar experiment score;
- every replay-eligible route retains the non-negotiable `leakage`, `missingness`, and `reproducibility` guardrails;
- `IRREDUCIBLE_AMBIGUITY` can trigger a bounded information-gain replay without changing the diagnosis label;
- availability mismatch and source-health problems are not replay-eligible until evidence is fresh;
- preflight `ResearchLineageManifest` and `StaleEvidenceReport` are created before replay;
- stale bound sibling/plugin fingerprints veto adversarial replay itself;
- stale replay deferral produces `DeferredExperiment`, not `RejectedHypothesis`;
- healthy `INTENTIONAL_SPECIALIZATION` can produce `ABSTAIN_SPECIALIZATION` with no experiment/replay;
- the live loop chooses the routed disagreement instead of blindly using the first sorted case;
- negative-result reuse remains intact for replay-eligible exact repeats;
- negative-result reuse does not cross changed sibling/plugin contract fingerprints because experiment identity is bound to the immutable route context;
- final lineage includes preflight lineage, preflight staleness, route decision, and downstream experiment/result artifacts; in the unified build it also includes attestation and receipt IDs;
- stale/deferred/abstained routes emit no DAEDALUS review packet;
- normal fresh replay still reaches only `PROMETHEUS_ENGINEERING_PASS` before DAEDALUS review; and
- CLI output exposes route artifact ID, action, priority band, and reason code.

## External attestation + provenance-lineage evidence (lineage B)

- attestation subject digest must equal the digest suffix of the exact `plugin-evidence:` artifact;
- SHA-256 fields are restricted to lowercase 64-hex digests;
- verification receipts canonicalize duplicate-free checks and derive `verified` only when `signature`, `subject_digest`, `signer_identity`, and `trusted_root` all exist and pass;
- half-supplied attestation/receipt pairs fail closed even in OPTIONAL mode;
- `REQUIRE_VERIFIED` degrades runs with missing, partial, or unverified selected-plugin coverage and suppresses provenance/promotion output;
- complete strict fixture coverage persists both attestation and receipt artifacts before handoff;
- attestation policy participates in deterministic loop identity;
- provenance manifests bind policy plus canonical attestation and receipt IDs;
- lineage verification supports roots, multi-generation ancestry, and convergent multi-parent DAGs;
- lineage fails closed on missing parents, wrong artifact types, content-ID substitution even when the outer memory checksum is recomputed, duplicate parent IDs, and cycles;
- review-ready packets require a complete lineage report whose tip is the exact current manifest and whose evidence contains both manifest and lineage-report IDs;
- stale/tampered plugin, observation, source-contract, parent, external-attestation, receipt, and policy bindings remain rejected;
- `production_authorized=True` remains structurally rejected.

## Evidence semantics

`ExternalExecutionAttestation` and `AttestationVerificationReceipt` are application-level evidence references. PROMETHEUS does not parse or validate DSSE, certificates, transparency-log proofs, timestamps, revocation, or cryptographic signatures. `verified=True` means the identified external verifier reported the recorded mandatory checks as passing under the identified policy and root. It does not mean PROMETHEUS repeated that cryptography itself.

`ProvenanceLineageReport` (`prometheus_loop.provenance_lineage`) verifies the integrity of locally persisted identity and ancestry. `ResearchLineageManifest`/`StaleEvidenceReport` (`prometheus_loop.lineage`) record participating artifacts and detect contract-fingerprint staleness. Neither turns PROMETHEUS into DAEDALUS or confers production authority. Disagreement diagnoses are conservative research labels, not proof of causation.

## Host research capability record

- **Lineage A build cycle:** Native Deep Research was not exposed. Exa and Firecrawl developer search succeeded. Tavily research returned HTTP/status `432` (plan usage limit exceeded) and was recorded as capability-degraded.
- **Unified merge cycle:** No external research surfaces were used. This cycle only reconciled code, tests, and docs and re-ran the local gates.

The deterministic local demos intentionally use fixture plugin execution records, fixture attestations, and fixture receipts.

## What remains unverified / intentionally absent

- live Deep Research execution;
- PROMETHEUS-side cryptographic verification of plugin execution attestations (receipts are recorded and bound, not re-verified);
- private/public key management or signing;
- X.509 chain/revocation validation;
- Sigstore/Rekor/Fulcio/TSA network integration;
- automatic retrieval of external attestation bodies;
- multi-signature threshold policy;
- direct AION evidence-write contract binding;
- direct DAEDALUS review-ingress contract binding;
- live NEXUS service ingestion;
- direct current ARGUS/ATHENA service integrations;
- live sibling service writes;
- DAEDALUS protected-holdout evaluation or acceptance;
- broker connectivity or production execution;
- predictive edge, profitability, or production readiness;
- proof that qualitative route priority corresponds to real-world economic value; and
- proof that disagreement diagnoses are the true causal explanation rather than conservative research labels.

**Stale when:** code/tests change, routing policy, disagreement taxonomy, adversarial check vocabulary, lineage identity, contract/plugin fingerprint semantics, attestation/policy schemas, provenance identifiers or loop identity inputs, external verifier/trusted-root semantics, host plugin behavior, sibling contracts, DAEDALUS review-ingress authority, or ecosystem authority boundaries change.
