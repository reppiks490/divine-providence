# JANUS ∞ Run 004 — Evidence-Aware Adjudication + Non-Mutating Temporal Normalization

Run 004 continues from Run 003 and does not claim live-repository adoption.

## Built

- Explicit `evidence_precedence` policy. JANUS assigns no intrinsic ordering to confidence labels.
- Equal-authority temporal conflicts may be resolved only when every tied fact has an explicitly ranked evidence class and exactly one evidence rank is highest.
- Missing or tied evidence policy remains quarantined; authority precedence still dominates evidence precedence.
- `temporal_normalization_proposals()` detects a narrow historical-progression pattern: same subject/predicate, same source lineage, same authority, older open interval, later differing value.
- Normalization is proposal-only: it never rewrites `valid_to`; every proposal carries `mutation_applied=false` and `proof_required=true`.
- Evidence policy is included in state digests and handoff export/import.
- Added schemas for evidence policy and temporal-normalization proposals.

## Verification

- Red phase observed: 17-test suite initially produced 3 errors + 1 failure before implementation.
- Green phase: 17/17 tests pass after implementation and compatibility correction.
- Python compilation passes.
- Seeded Run 004 state digest: `422b909ed40bc59d88b733f155dc24b43767e6aff06c96a7f40cd1c180ce9d7d`.
- Fresh handoff import reproduces the same digest.
- Seed remains conservative: 1 temporal conflict, 1 quarantined temporal conflict, 0 normalization proposals because the two NEXUS test-count facts have different source lineage and no explicit authority/evidence policy.

## Safety invariant added

Evidence quality may break an authority tie only under explicit policy. Evidence must never override a uniquely higher authority. Temporal normalization must never mutate historical validity without a separate proof-backed approval operation.

## Next

Add proof-backed normalization approval records and conflict evidence lineage, so a proposal can be accepted only by a separately auditable proof bundle while retaining the original immutable fact history.
