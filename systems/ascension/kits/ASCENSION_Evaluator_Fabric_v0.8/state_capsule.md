# ASCENSION STATE CAPSULE v019 (package-internal)

Cycle: `ascension-cycle-019`.

## Lifecycle
- Evaluator Fabric v0.8 — CANDIDATE (this package).
- Evaluator Fabric v0.7 — CANDIDATE rollback dependency, unchanged.
- Manifest Trust -> Collision Adapter v0.3 — CANDIDATE, unchanged.
- Collision Detector v0.3 — CANDIDATE.
- Collision Detector v0.2.1 — rollback baseline, SHA-256 `e71d28d701b9693ce78173c8d0fa603d3ae7fd5ca1bbfdab4dc659d17b0ec9cc`.
- Context Distillation Engine v0.3 — SHADOW.

## Completed
Strict RFC 9162-style inclusion verifier with index/size-derived orientation, exact proof geometry, uint64/type bounds, 32-byte hash enforcement, domain-separated leaf/node hashing, deterministic reasons and composition with v0.7 consistency+witness evidence. Adapter v0.3 and sibling systems are not modified.

## Evidence before packaging
- RED: ModuleNotFoundError before v0.8 module existed.
- Focused v0.8: 19/19 PASS.
- Combined v0.6+v0.7+v0.8 regression: 46/46 PASS.
- Property: 8,256/8,256 valid inclusions for sizes 1..128.
- Property attacks: 1,500 mutated nodes + 1,000 geometry + 1,000 binding rejected.
- Hostile: 500 order + 500 bad-node-length + 500 malformed-top-level rejected/fail-closed.
- Comparative seven-leaf probe: v0.6 accepted 42/42 false in-range index relabels; v0.8 rejected 42/42.

Exact final ZIP clean-extraction verification and final ZIP SHA-256 are recorded in the external `/mnt/data/ASCENSION_STATE_CAPSULE_v019.md` after packaging. No package mutation is allowed after that verification.

## Blocker
No authoritative authenticated real sibling manifest was located. Transfer/Evidence gates remain incomplete. Lifecycle remains CANDIDATE.

## Resume
Verify the external v019 capsule and final package hash. Search first for a real signed sibling manifest. If absent, consider a versioned Adapter v0.4 contract that explicitly pins v0.8; do not silently mutate Adapter v0.3.
