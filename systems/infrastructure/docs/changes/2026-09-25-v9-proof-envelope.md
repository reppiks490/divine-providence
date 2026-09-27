# V9 — Proof Envelope Integrity

V9 adds `proof_envelope.py`, a pure integrity-binding layer for evidence already produced by the supervisor.

## Guarantees

- Required stages: guard → topology → lease → canary → evidence → attribution.
- Detects missing, duplicated, reordered, substituted, tampered, stale, and not-yet-valid envelopes.
- Binds every stage to one action identity.
- Uses canonical SHA-256 binding hashes plus an ordered hash chain and final envelope hash.
- Verifier has no execute/mutate/promote/rollback/lease authority.
- Hashes are integrity checks only; they are not signatures, identity attestations, or authorization credentials.

## Deliberate boundary

V9 does not yet make the main loop emit envelopes automatically. That integration should occur only after the envelope contract is stable, because journal emission must bind the exact runtime guard/topology/lease/canary/evidence/attribution records rather than reconstruct them after the fact.

Central Orchestration remains an external sibling contract. This envelope may later be transported by it, but the supervisor does not take over transport/recovery authority.
