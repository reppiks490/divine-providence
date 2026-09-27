# ASCENSION STATE CAPSULE v017.1

Authoritative continuity checkpoint for `ascension-cycle-017`, superseding v017 only for persistence metadata. Capability lifecycle is unchanged.

## Capability state
- Collision Detector v0.2.1 — CANDIDATE rollback baseline; SHA-256 `e71d28d701b9693ce78173c8d0fa603d3ae7fd5ca1bbfdab4dc659d17b0ec9cc`.
- Collision Detector v0.3 — CANDIDATE.
- Manifest Trust -> Collision Adapter v0.2 — CANDIDATE, unchanged; SHA-256 `86be5d506dbfea57504871ffcbe16542831151f0826cb4545ee27b4baaf80adf`.
- Evaluator Fabric v0.6 — CANDIDATE rollback transparency backend; SHA-256 `ed5c6ec83d08630a903bd26f73166360c0193d7f6dcb28c36729dac6e018acd9`.
- Evaluator Fabric v0.7 — CANDIDATE; exact local ZIP SHA-256 `f010e9986eb366d7b65179e722934acb4fa0d30768da3d575eebaa467e889ca7`.
- Context Distillation Engine v0.3 — SHADOW.

## Completed in cycle 017
Evaluator Fabric v0.7 adds RFC 9162-style compact consistency verification plus ASCENSION-specific signed Ed25519 witness observations. The witness payload binds witness ID, log ID, tree size, root hash and observation time. Verification enforces unique-witness thresholds, freshness/future tolerance, revocation and exact checkpoint binding. Adapter v0.2 was not modified or silently upgraded.

## Verification evidence
- RED sensitivity reproduced: missing v0.7 module -> `ModuleNotFoundError`; restored module -> GREEN.
- Focused v0.7 suite: 16/16 PASS.
- Combined v0.6 + v0.7 regression: 27/27 PASS.
- Property matrix: 2,016/2,016 valid consistency transitions PASS for sizes 2..64.
- Property corruption campaign: 1,000/1,000 mutated compact proofs rejected.
- Focused failure injection: 500/500 compact-proof mutations rejected; 400/400 witness payload/signature mutations rejected.
- RFC example transitions 3->7, 4->7 and 6->7 PASS.
- Exact final ZIP clean extraction: 27/27 regression PASS; property suite PASS; compile PASS.
- ZIP contains no packaged `__pycache__` or `.pyc` files.

## Artifact locations
Local:
- `/mnt/data/ASCENSION_Evaluator_Fabric_v0.7.zip` — SHA-256 `f010e9986eb366d7b65179e722934acb4fa0d30768da3d575eebaa467e889ca7`, 19,552 bytes.
- `/mnt/data/ASCENSION_STATE_CAPSULE_v017.md` — cycle checkpoint before durable-persistence metadata.
- `/mnt/data/ASCENSION_STATE_CAPSULE_v017_1.md` — this capsule.

Persistent Google Drive copies:
- `/Google Drive/Icarus Governance/ASCENSION/ASCENSION_Evaluator_Fabric_v0.7_f010e998.zip` — 19,552 bytes.
- `/Google Drive/Icarus Governance/ASCENSION/ASCENSION_STATE_CAPSULE_v017_verified.md` — 4,843 bytes, pre-v017.1 persistence capsule.
- Older byte-different interrupted files `ASCENSION_Evaluator_Fabric_v0.7.zip` and `ASCENSION_STATE_CAPSULE_v017.md` were preserved, not overwritten.

Commit ID: none; no live repository was modified.

## Interfaces
- `verify_compact_consistency(...)`
- `verify_signed_witness_observations(...)`
- `verify_transparency_transition(...)`

## Research / standards boundary
RFC 9162 Section 2.1.4 compact consistency verification and its 7-leaf examples were checked against the official RFC. RFC 9162 notes that split-view countermeasures are outside its core protocol; therefore signed witnesses are explicitly an ASCENSION companion primitive rather than an RFC claim. Exact first-party Deep Research was not callable in cycle 017; Exa + official RFC verification were used. Previous-cycle Deep Research was not counted as a new invocation.

## Ownership / assumptions
ASCENSION remains non-authoritative, read-only and fail-open for sibling continuity. v0.7 does not authenticate the initial witness-key registry, prove organizational independence of witnesses, prove semantic truth of manifests, mutate siblings, or claim external adoption.

## Open gates / blockers
No authoritative authenticated real sibling manifest was found in the Library sweep. Evidence and Transfer remain open, so lifecycle stays CANDIDATE and READY_TO_COMMIT remains NO for ecosystem promotion.

## Tools actually used
Capability discovery; Superpowers (`using-superpowers`, brainstorming guidance, TDD, verification-before-completion); Baton Pass continuity guidance; Exa research; official RFC web verification; File Library/Google Drive discovery/search/write; container/Python build, tests, property testing, failure injection and packaging. Codex Coordinator and Akinator were discovered but not invoked because no live repository mutation was in scope.

## Exact resume instructions
1. Verify local/package SHA-256 `f010e9986eb366d7b65179e722934acb4fa0d30768da3d575eebaa467e889ca7` or use the hash-qualified Drive copy.
2. Preserve v0.6, Adapter v0.2 and Collision v0.2.1 rollback checkpoints.
3. Search first for a genuine authoritative signed sibling manifest.
4. If found, validate through existing Adapter v0.2 before changing backend contracts.
5. If still absent, build Adapter v0.3 as an explicit optional v0.7 backend contract with downgrade/substitution rejection; do not silently replace v0.2.
6. Do not mark VERIFIED/ADOPTED_EXTERNALLY until all nine hard gates pass with real authenticated sibling evidence.
