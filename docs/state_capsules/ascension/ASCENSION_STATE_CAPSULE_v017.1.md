# ASCENSION STATE CAPSULE v017.1

Authoritative corrected checkpoint: ascension-cycle-017 / capsule v017.1.
This capsule supersedes v017 only for artifact-byte identity; it does not overwrite or invalidate the prior checkpoint history.

## Lifecycle
- Evaluator Fabric v0.7: CANDIDATE
- Manifest Trust -> Collision Adapter v0.2: CANDIDATE (unchanged)
- Collision Detector v0.3: CANDIDATE
- Context Distillation Engine v0.3: SHADOW
- Rollback baseline: Collision Detector v0.2.1, SHA-256 e71d28d701b9693ce78173c8d0fa603d3ae7fd5ca1bbfdab4dc659d17b0ec9cc

## Completed
Evaluator Fabric v0.7 adds RFC 9162-style compact Merkle consistency-proof verification and ASCENSION-specific signed witness observations, without modifying sibling systems or silently replacing Adapter v0.2's v0.6 backend contract.

## Exact evidence
- Evaluator v0.7 tests: 16/16 PASS.
- Combined Evaluator v0.6 + v0.7 regression: 27/27 PASS from clean extraction of the current exact ZIP bytes.
- Property suite: 2,016/2,016 valid tree transitions for sizes 2..64 PASS; maximum observed proof length 7 hashes.
- Random compact-proof mutation property campaign: 1,000/1,000 rejected.
- Focused compact-proof mutation campaign: 500/500 rejected.
- Signed-witness payload/signature mutation campaign: 400/400 rejected.
- RFC 9162 example transitions 3->7, 4->7, 6->7: PASS.
- Malformed witness-policy inputs fail closed after a regression bug was found and repaired.

## Artifact identity
- Artifact: ASCENSION_Evaluator_Fabric_v0.7_FINAL.zip
- SHA-256: f010e9986eb366d7b65179e722934acb4fa0d30768da3d575eebaa467e889ca7
- Size: 19552 bytes
- Exact clean-extraction verification: PASS.

## Interfaces
- verify_compact_consistency(first_size, second_size, first_root, second_root, consistency_path)
- verify_signed_witness_observations(observations, witness_keys, minimum_witnesses, expected_log_id, expected_tree_size, expected_root_hash, now_iso, max_age_seconds, future_tolerance_seconds=300)
- verify_transparency_transition(...)

## Dependencies / contracts
- Python 3.11+
- SHA-256 reference implementation for compact Merkle verification
- Ed25519 witness signatures
- Adapter v0.2 remains pinned to Evaluator Fabric v0.6/full-history transparency; v0.7 is NOT silently substituted.
- Witness-key registry/trust bootstrap remains externally governed.

## Blockers / risks / assumptions
- No authoritative authenticated real sibling manifest has been found; Transfer/Evidence gate remains open.
- Signed witness IDs do not prove organizational/network independence.
- Compact consistency proves append-only relation, not semantic truthfulness of logged manifests.
- Algorithm agility beyond SHA-256 is not implemented in v0.7.
- No repo commit ID exists because this cycle did not modify a live repository.

## Tools actually used
- Superpowers: using-superpowers, brainstorming, test-driven-development, verification-before-completion.
- Baton Pass continuity guidance.
- Exa research skill/tools for standards research.
- Official RFC 9162 web verification.
- File Library / Google Drive discovery and persistence.
- Container/Python build, tests, property tests, packaging, hashing.
- Exact first-party Deep Research: NOT available in the current cycle tool inventory; not claimed.
- Codex Coordinator and Akinator were exposed but not invoked because no live repo was changed.

## Durable storage
Persist this capsule and the FINAL ZIP as new files under /Google Drive/Icarus Governance/ASCENSION/. Do not overwrite v017 or earlier good checkpoints.

## Exact resume instructions
1. Load v017.1 and verify the FINAL ZIP hash above before using v0.7.
2. Search first for an authoritative signed sibling manifest; if present, process it through the known-good Adapter v0.2 contract without silently changing backends.
3. If no real manifest is available, build Adapter v0.3 as an explicit versioned backend upgrade that can opt into Evaluator Fabric v0.7.
4. Add downgrade/substitution, provenance-loss, compact-proof, witness-binding, and rollback regression tests.
5. Preserve Adapter v0.2/v0.6 and Collision v0.2.1 rollback artifacts.
6. Do not mark VERIFIED or ADOPTED_EXTERNALLY until authenticated real sibling transfer satisfies all nine ASCENSION promotion gates.
