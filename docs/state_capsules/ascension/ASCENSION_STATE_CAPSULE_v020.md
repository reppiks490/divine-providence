# ASCENSION ∞ STATE CAPSULE v020

## Authority / checkpoint
- Cycle: `ascension-cycle-020`
- New capability: **Manifest Trust → Collision Adapter v0.4.0 — CANDIDATE**.
- Evaluator Fabric v0.8 remains **CANDIDATE**.
- Evaluator Fabric v0.7 remains **CANDIDATE**.
- Collision Detector v0.3 remains **CANDIDATE**.
- Context Distillation Engine v0.3 remains **SHADOW**.
- Rollback baseline remains Collision Detector v0.2.1, SHA-256 `e71d28d701b9693ce78173c8d0fa603d3ae7fd5ca1bbfdab4dc659d17b0ec9cc`.
- Adapter v0.3 rollback artifact SHA-256 `cfb6b26965531bcdf7def4ae635a47d25190982d47ce0be7a1e6b0fb2016708a`.
- Evaluator Fabric v0.8 dependency artifact SHA-256 `d8f4a0dedf27def0f1bde05bc52faa6dd637068c95594b3c6090642b08573cae`.
- No sibling adoption is claimed.

## Completed work
Adapter v0.4 now:
1. replaces the active v0.6 side-directed inclusion path with Evaluator Fabric v0.8 strict RFC 9162 index-bound inclusion;
2. keeps Evaluator Fabric v0.7 as the compact consistency + signed-witness transition layer;
3. keeps Collision Detector v0.3 as the collision backend;
4. requires an explicit backend contract and separates trust, inclusion, transition, composite transparency, collision, and inclusion-schema identities;
5. pins the transparency/witness policy digest;
6. pins build-time SHA-256 identities for the embedded trust, inclusion, transition, and collision source modules;
7. validates those dependency source bytes at runtime before manifest acceptance;
8. rejects v0.6 inclusion downgrade, old side-directed inclusion evidence, transition/collision substitution, inclusion-schema substitution, SHA-1 downgrade, and policy substitution;
9. binds the manifest's RFC 9162 domain-separated Merkle leaf hash into provenance;
10. records deterministic digests for attestations, prior collision report, raw transparency evidence, trust result, strict-inclusion result, transition result, backend contract, dependency source identities, policy, manifest, artifact, and final evidence packet;
11. preserves the complete sibling manifest rather than projecting away unknown sibling fields;
12. preserves fail-closed ASCENSION analysis with `safe_for_siblings=true` on rejection;
13. remains read-only and performs no sibling writes.

## TDD / debugging evidence
- Valid RED: `ModuleNotFoundError: manifest_trust_collision_adapter_v0_4` before implementation.
- Dependency-source pin RED: missing `backend_artifact_sha256` and missing `validate_runtime_dependency_integrity()` before implementation.
- An earlier invalid RED attempt failed due unittest path parsing; it was explicitly discarded and not counted as evidence.
- GREEN after dependency pinning: 28/28 focused tests.

## Exact final ZIP verification
Artifact: `ASCENSION_Manifest_Trust_Collision_Adapter_v0.4.zip`
SHA-256: `0145bf2ecb3ecd606c9d70b26b671ce397bba17f35dc56da4c691997bbd8e224`
Size: 48392 bytes

Clean extraction of the exact frozen ZIP:
- Combined unit/regression suite: **105/105 PASS**, 0 failures, 0 errors.
- Evaluator v0.7 property matrix: **2,016/2,016 valid transitions PASS**; **1,000/1,000 mutated consistency proofs rejected**.
- Evaluator v0.8 property matrix: **8,256/8,256 valid inclusion proofs PASS**; **1,500/1,500 mutated nodes rejected**; **1,000/1,000 geometry attacks rejected**; **1,000/1,000 binding attacks rejected**.
- Historical comparison retained: v0.6 accepted **42/42** false index relabels in the 7-leaf comparison; v0.8 rejected **42/42**.
- Adapter v0.4 adversarial campaign: **3,226/3,226** rejected/detected.
  - backend substitutions 500/500
  - pinned policy substitutions 500/500
  - strict inclusion node mutations 500/500
  - false index relabels 500/500
  - witness mutations 400/400
  - malformed inputs fail closed + safe_for_siblings 300/300
  - dependency-digest contract substitutions 500/500
  - required provenance deletions 26/26
- Deliberate post-freeze dependency source-file tampering: **4/4 detected** (trust, inclusion, transition, collision).
- Python compilation of shipped core modules: PASS.
- Packaged `__pycache__` / `.pyc` entries: 0.

## Versioned interfaces
- `build_backend_contract(trust_policy)`
- `validate_runtime_dependency_integrity()`
- `hash_evidence(value)`
- `normalize_trusted_manifest(...)`
- `validate_trust_result(trust_result)`
- `validate_normalized_manifest(normalized_manifest, backend_contract)`
- `analyze_trusted_ecosystem(items, dependency_graph, policy=None)`

## Dependency source pins inside v0.4
- trust / Evaluator Fabric v0.4: `b189d3c21516ee62ee15da764f9bbedd0c036d180a4cb316d81c2426717d238e`
- inclusion / Evaluator Fabric v0.8: `8c40d16061bbc436cf78d3029f6b4d04b507dad8779e3dba74fd6ce51746de4b`
- transition / Evaluator Fabric v0.7: `eb8b4ad9990f8b57530aa88415827a762c6b1ff136996a33fe158ea8a72c33b6`
- collision / Collision Detector v0.3: `fda90e02b3774219d0b52640e58f35510f5834c1065a2729cb563f1b303f5abb`

## Hard-gate status
- Evidence: **PARTIAL** — strong local/synthetic and exact-package evidence; authoritative real sibling evidence missing.
- Reproduction: **PASS_LOCAL** — exact final ZIP clean-extraction verification passed.
- Boundary: **PASS_LOCAL** — read-only; no sibling writes.
- Non-Interference: **PASS_LOCAL** — malformed/trust failures fail closed for analysis and preserve sibling continuity.
- Rollback: **PASS_LOCAL** — Adapter v0.3 and Collision v0.2.1 retained.
- Observability: **PASS_LOCAL** — manifest leaf hash, policy, contract, upstream evidence, subresults, dependency source identities, collision output, evidence-packet digests.
- Contract: **PASS_LOCAL** — explicit v0.4 layered backend and evidence-schema contract.
- Transfer: **BLOCKED** — no authoritative signed real sibling runtime manifest located.
- Regression: **PASS_LOCAL** — v0.3/v0.4, Collision v0.3, Evaluator v0.6/v0.7/v0.8 suites green.

Lifecycle remains **CANDIDATE**, not VERIFIED or ADOPTED_EXTERNALLY.
`READY_TO_COMMIT = NO` for ecosystem promotion.

## Research / tools actually used
- Exact first-party Deep Research checked at cycle start: **not exposed/callable; actually invoked = NO**.
- Superpowers skills actually invoked: using-superpowers, brainstorming, test-driven-development, systematic-debugging, verification-before-completion.
- Baton Pass skill actually invoked for continuity guidance.
- Exa Search plugin actually invoked for official/primary software-supply-chain verification patterns.
- Standard web search used for official TUF/Sigstore validation.
- File Library searched for authoritative signed sibling manifests.
- Container/Python used for TDD, regression, properties, adversarial tests, packaging, hashing, clean extraction, compilation, and deliberate file-tamper tests.
- Codex Coordinator / Akinator were exposed but not invoked because no live repository was mutated.
- No repository commit ID exists for this isolated package.

## Blockers / risks / assumptions
- No authoritative signed sibling runtime manifest has yet crossed the Transfer gate.
- Initial trust-root and witness-key authority remains externally governed.
- A valid signature/proof establishes configured cryptographic properties, not semantic truth.
- Distinct witness identities do not prove organizational independence.
- Runtime dependency integrity assumes file-backed Python modules; compiled/zipimport deployment requires a different measurement mechanism.
- If an attacker replaces both the adapter package and the external authoritative package hash/checkpoint before verification, internal dependency pins alone do not restore trust.
- `build_backend_contract()` remains meaningful only when governance pins the result before untrusted policy mutation.
- v0.8 is SHA-256-specific.

## Next action
1. Search first for an authoritative signed sibling runtime manifest.
2. If found, preserve its exact source bytes and route it unchanged through Adapter v0.4, then evaluate all nine promotion gates.
3. If still absent, do **not** spend the next cycle merely adding another verifier layer. Build a non-authoritative, read-only **Sibling Manifest Conformance Kit v0.1**: versioned schemas + conformance validator + authority handoff checklist that tells a sibling owner exactly what must be emitted/signed for real Transfer, without generating or claiming authority on its behalf.
4. Preserve v0.4, v0.3, Evaluator v0.8/v0.7, and Collision v0.2.1 as rollback checkpoints.

## Exact resume instructions
Load this capsule; verify the v0.4 ZIP hash above; do not restart earlier detector/evaluator work; search for real signed sibling evidence; if absent, begin the read-only Sibling Manifest Conformance Kit. Do not mark any capability VERIFIED or ADOPTED_EXTERNALLY until an authoritative real sibling manifest passes Evidence, Reproduction, Boundary, Non-Interference, Rollback, Observability, Contract, Transfer, and Regression gates.
