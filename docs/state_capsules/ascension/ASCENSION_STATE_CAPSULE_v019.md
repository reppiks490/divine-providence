# ASCENSION ∞ STATE CAPSULE v019

## Authority / checkpoint
- Cycle: `ascension-cycle-019`
- New capability: **Evaluator Fabric v0.8.0 — CANDIDATE**
- Manifest Trust -> Collision Adapter v0.3 remains **CANDIDATE**, unchanged.
- Evaluator Fabric v0.7 remains **CANDIDATE** rollback dependency, SHA-256 `f010e9986eb366d7b65179e722934acb4fa0d30768da3d575eebaa467e889ca7`.
- Evaluator Fabric v0.6 remains rollback/comparison baseline, SHA-256 `ed5c6ec83d08630a903bd26f73166360c0193d7f6dcb28c36729dac6e018acd9`.
- Collision Detector v0.3 remains **CANDIDATE**.
- Collision Detector v0.2.1 remains rollback baseline, SHA-256 `e71d28d701b9693ce78173c8d0fa603d3ae7fd5ca1bbfdab4dc659d17b0ec9cc`.
- Context Distillation Engine v0.3 remains **SHADOW**.

## Completed work
Evaluator Fabric v0.8 adds strict RFC 9162-style Merkle inclusion verification without changing v0.7 or Adapter v0.3:
1. `merkle_leaf_hash(data)` applies explicit `0x00` leaf domain separation.
2. Internal nodes use `SHA-256(0x01 || left || right)`.
3. `expected_inclusion_path_length(leaf_index, tree_size)` derives exact proof geometry from RFC structural coordinates.
4. `verify_strict_inclusion(...)` derives every left/right fold from `leaf_index` + `tree_size`; caller-supplied side metadata is not trusted.
5. uint64 domain and exact index bounds are enforced; bool/string numeric coercion is rejected.
6. leaf/root/proof nodes must be exactly 32 bytes (or valid 32-byte hex strings).
7. padded and truncated proofs are rejected before root comparison.
8. deterministic reason codes expose type, geometry and root failures.
9. `verify_transparency_evidence(...)` composes strict inclusion with the existing v0.7 compact-consistency + signed-witness gate.
10. inputs are read-only; malformed combined evidence fails closed rather than escaping the boundary.

## Comparative finding
Evaluator Fabric v0.6 checks that `leaf_index` is in range but its side-labelled inclusion fold does not use that index to determine orientation. In a seven-leaf probe, an otherwise valid proof was accepted under every false in-range claimed index: **42/42 false relabels accepted**. v0.8 rejected **42/42** of those false relabels by binding the proof fold to the declared index and tree size.

This finding does not change v0.6's historical package; v0.6 remains an explicit rollback/comparison artifact.

## TDD / research evidence
- RED observed before implementation: `ModuleNotFoundError: No module named 'evaluator_fabric_v0_8'`.
- Exact first-party Deep Research was searched for but not exposed/callable: `DEEP RESEARCH ACTUALLY INVOKED = NO` for cycle 019.
- Exa research used three targeted standards/implementation workstreams, 24 returned results total.
- Primary normative authority: RFC 9162 §2.1.1 and §2.1.3.2 from RFC Editor/IETF.
- RFC seven-leaf example proof lengths tested: d0=3, d3=3, d4=3, d6=2.

## Fresh exact-package verification
The final ZIP was frozen before these checks and was not mutated afterward.

Exact clean extraction results:
- Focused Evaluator Fabric v0.8 suite: **19/19 PASS**, 0 failures, 0 errors.
- Combined v0.6 + v0.7 + v0.8 regression suite: **46/46 PASS**, 0 failures, 0 errors.
- Valid-inclusion property matrix: **8,256/8,256 PASS** for every leaf of every tree size 1..128.
- Maximum observed proof length for sizes 1..128: 7 nodes.
- Mutated proof-node attacks: **1,500/1,500 rejected**.
- Padded/truncated proof-geometry attacks: **1,000/1,000 rejected**.
- Leaf/root/index binding attacks: **1,000/1,000 rejected**.
- Proof-order attacks: **500/500 rejected**.
- Wrong proof-node-length attacks: **500/500 rejected**.
- Malformed top-level input calls: **500/500 failed closed**, no escaped exception.
- v0.6 false-index relabel probe: **42/42 accepted** (comparative weakness).
- v0.8 false-index relabel probe: **42/42 rejected**.
- Python compilation of shipped v0.6/v0.7/v0.8 modules: PASS.
- Final ZIP contains no `__pycache__` or `.pyc` entries.

## Artifact
- Local artifact: `/mnt/data/ASCENSION_Evaluator_Fabric_v0.8.zip`
- SHA-256: `d8f4a0dedf27def0f1bde05bc52faa6dd637068c95594b3c6090642b08573cae`
- Size: 28,504 bytes
- Local external capsule: `/mnt/data/ASCENSION_STATE_CAPSULE_v019.md`
- No repository commit ID exists; no live repository was mutated.

## Versioned interfaces
- `merkle_leaf_hash(data)`
- `expected_inclusion_path_length(leaf_index, tree_size)`
- `verify_strict_inclusion(leaf_hash, leaf_index, tree_size, root_hash, inclusion_path)`
- `verify_transparency_evidence(...)`

## Dependencies / assumptions
- SHA-256 CT-style domain separation is fixed in this reference.
- Compact consistency and signed witness observations remain Evaluator Fabric v0.7 responsibilities.
- Trust/witness key bootstrap remains external governance.
- Inclusion proves membership of a hash at a position in an advertised root; it does not prove semantic truth of the leaf contents.
- Distinct witness IDs do not prove organizational independence.
- Adapter v0.3 remains unchanged; there is no silent backend upgrade.

## Hard-gate status
- Evidence: PARTIAL — strong local/RFC-aligned evidence; real sibling evidence missing.
- Reproduction: PASS_LOCAL — exact final ZIP clean-extraction verification passed.
- Boundary: PASS_LOCAL — read-only; no sibling writes.
- Non-Interference: PASS_LOCAL — malformed evidence fails closed inside ASCENSION; no sibling mutation/execution stop.
- Rollback: PASS_LOCAL — v0.7/v0.6 retained; Adapter v0.3 unchanged.
- Observability: PASS_LOCAL — deterministic reasons, expected/actual node counts, computed/expected roots.
- Contract: PASS_LOCAL — strict v0.8 inclusion interfaces versioned and documented.
- Transfer: BLOCKED — no authoritative signed real sibling manifest located.
- Regression: PASS_LOCAL — v0.6/v0.7/v0.8 suites remain green.

Lifecycle remains **CANDIDATE**, not VERIFIED or ADOPTED_EXTERNALLY.
`READY_TO_COMMIT = NO` for ecosystem promotion.

## Tools actually used
- Live capability/tool discovery.
- Superpowers skill guidance: `using-superpowers`, TDD, systematic debugging, verification-before-completion.
- Baton Pass continuity guidance.
- Exa standards/implementation research.
- File Library / Google Drive search and persistence tooling.
- Container/Python execution for TDD, regression, property, hostile, compilation, packaging and clean-extraction verification.
- Codex Coordinator and Akinator were discovered but not invoked because no live repository was modified.

## Next / exact resume instructions
1. Verify this capsule and package hash before any new build.
2. Search first for an authoritative signed sibling manifest.
3. If one exists, do not silently change Adapter v0.3; decide explicitly which pinned backend contract will process it and preserve the original artifact unchanged.
4. If no real manifest exists, the next isolated candidate may be **Manifest Trust -> Collision Adapter v0.4**, explicitly pinning Evaluator Fabric v0.8 strict inclusion while retaining Adapter v0.3 as rollback.
5. Do not mark any capability VERIFIED or ADOPTED_EXTERNALLY until Evidence, Reproduction, Boundary, Non-Interference, Rollback, Observability, Contract, Transfer and Regression gates all pass.
